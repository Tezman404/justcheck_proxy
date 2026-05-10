import os
import logging
from telegram import Bot
from telegram.error import TelegramError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_last_message_id(filename="last_message_id.txt"):
    """آخرین شناسه پیام ذخیره شده را از فایل می‌خواند."""
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try: return int(f.read().strip())
            except: return None
    return None

def save_last_message_id(message_id, filename="last_message_id.txt"):
    """آخرین شناسه پیام را در فایل ذخیره می‌کند."""
    with open(filename, "w") as f:
        f.write(str(message_id))

def fetch_new_messages():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    if not TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    bot = Bot(token=TOKEN)
    last_id = get_last_message_id()
    logging.info(f"Last processed message ID: {last_id}")

    try:
        # دریافت ۲۰ پیام اخیر از کانال
        updates = bot.get_updates(offset=last_id, limit=20, timeout=10)
        if not updates:
            logging.info("No new messages.")
            return

        # پردازش پیام‌های جدید
        new_messages = []
        for update in updates:
            if update.message and update.message.chat_id == int(CHAT_ID):
                msg = update.message
                new_messages.append(f"ID: {msg.message_id}\nText: {msg.text or '[Media or Non-Text Message]'}")
                # به‌روزرسانی last_message_id
                if last_id is None or msg.message_id > last_id:
                    last_id = msg.message_id

        # نمایش ۱۰ پیام آخر (جدیدترین پیام‌ها)
        n_messages = 10
        latest_messages_to_show = new_messages[-n_messages:] if new_messages else []
        
        print("\n" + "="*50)
        print(f"Latest {len(latest_messages_to_show)} Message(s):")
        print("="*50 + "\n")
        
        if not latest_messages_to_show:
            print("No messages to display.\n")
        else:
            for msg in latest_messages_to_show:
                print(f"{msg}\n{'-'*30}")

        # ذخیره آخرین شناسه برای اجرای بعدی
        if last_id is not None:
            save_last_message_id(last_id)

    except TelegramError as e:
        logging.error(f"Telegram API error: {e}")

if __name__ == "__main__":
    fetch_new_messages()
