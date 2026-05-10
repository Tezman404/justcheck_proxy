import os
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

logging.basicConfig(level=logging.INFO)

LAST_ID_FILE = "last_message_id.txt"
OUTPUT_FILE = "latest_messages.txt"

def update_last_message_id(message_id):
    """همیشه فایل last_message_id را ایجاد یا به‌روز می‌کند."""
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(message_id))
    logging.info(f"Last message ID updated to: {message_id}")

def create_empty_last_id_file():
    """اگر فایل وجود نداشت، یک فایل خالی ایجاد می‌کند."""
    if not os.path.exists(LAST_ID_FILE):
        update_last_message_id(0)  # با 0 شروع می‌کنیم

def get_last_message_id():
    """آخرین شناسه پیام ذخیره شده را برمی‌گرداند."""
    create_empty_last_id_file()
    with open(LAST_ID_FILE, "r") as f:
        return int(f.read().strip())

async def fetch_and_save():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    if not TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    last_id = get_last_message_id()
    offset = last_id + 1 if last_id > 0 else None

    async with Bot(token=TOKEN) as bot:
        updates = await bot.get_updates(offset=offset, limit=20)
        new_messages = []
        for update in updates:
            if update.message and str(update.message.chat_id) == CHAT_ID:
                msg = update.message
                new_messages.append(f"ID: {msg.message_id}\nText: {msg.text or '[Non-text]'}")
                if msg.message_id > last_id:
                    last_id = msg.message_id

        # همیشه فایل last_message_id را با آخرین ID به‌روز می‌کند
        update_last_message_id(last_id)

        # ذخیره ۱۰ پیام آخر در فایل خروجی
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            if new_messages:
                # فقط ۱۰ پیام آخر جدید را ذخیره کن
                f.write("\n\n---\n\n".join(new_messages[-10:]))
                logging.info(f"Saved {len(new_messages[-10:])} new messages to {OUTPUT_FILE}")
            else:
                f.write("No new messages found.")
                logging.info("No new messages, but placeholder file created.")

if __name__ == "__main__":
    asyncio.run(fetch_and_save())
