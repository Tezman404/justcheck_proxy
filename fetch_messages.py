import os
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError, RetryAfter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_last_message_id(filename="last_message_id.txt"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return int(f.read().strip())
            except:
                return None
    return None

def save_last_message_id(message_id, filename="last_message_id.txt"):
    with open(filename, "w") as f:
        f.write(str(message_id))

async def fetch_new_messages():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    if not TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    last_id = get_last_message_id()
    logging.info(f"Last processed message ID: {last_id}")
    
    # offset باید برابر last_id + 1 باشد تا پیام تکراری دریافت نشود
    offset = last_id + 1 if last_id is not None else None

    try:
        # استفاده از async with برای مدیریت خودکار بستن اتصال بدون خطای flood
        async with Bot(token=TOKEN) as bot:
            updates = await bot.get_updates(offset=offset, limit=20, timeout=10)
            
            if not updates:
                logging.info("No new messages.")
                return

            new_messages = []
            for update in updates:
                if update.message and str(update.message.chat_id) == str(CHAT_ID):
                    msg = update.message
                    new_messages.append(f"ID: {msg.message_id}\nText: {msg.text or '[Media or Non-Text Message]'}")
                    if last_id is None or msg.message_id > last_id:
                        last_id = msg.message_id

            # نمایش ۱۰ پیام آخر جدید
            n_messages = 10
            latest_to_show = new_messages[-n_messages:] if new_messages else []
            
            print("\n" + "="*50)
            print(f"Latest {len(latest_to_show)} Message(s):")
            print("="*50 + "\n")
            
            if not latest_to_show:
                print("No new messages to display.\n")
            else:
                for msg in latest_to_show:
                    print(f"{msg}\n{'-'*30}")

            if last_id is not None:
                save_last_message_id(last_id)

    except TelegramError as e:
        logging.error(f"Telegram API error: {e}")
        # اگر خطای RetryAfter باشد، فقط لاگ می‌کنیم و ادامه می‌دهیم
        if isinstance(e, RetryAfter):
            logging.warning(f"Flood control: retry after {e.retry_after} seconds")

if __name__ == "__main__":
    asyncio.run(fetch_new_messages())
