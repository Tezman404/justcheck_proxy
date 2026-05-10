import os
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LAST_ID_FILE = "last_message_id.txt"
OUTPUT_FILE = "latest_messages.txt"

async def check_channel_access(bot, chat_id):
    """بررسی می‌کند آیا ربات به کانال دسترسی دارد و عضو است یا خیر."""
    try:
        chat = await bot.get_chat(chat_id)
        # بررسی نوع چت و وضعیت عضویت (برای کانال‌های عمومی معمولاً不需要)
        logging.info(f"✅ دسترسی به کانال موفق: {chat.title} (ID: {chat.id})")
        return True
    except TelegramError as e:
        logging.error(f"❌ خطای دسترسی به کانال: {e.message}")
        return False

def update_last_message_id(message_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(message_id))
    logging.info(f"Last message ID updated to: {message_id}")

def ensure_last_id_file():
    if not os.path.exists(LAST_ID_FILE):
        update_last_message_id(0)

def get_last_message_id():
    ensure_last_id_file()
    with open(LAST_ID_FILE, "r") as f:
        return int(f.read().strip())

async def fetch_and_save():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    if not TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    async with Bot(token=TOKEN) as bot:
        # گام 1: بررسی دسترسی به کانال
        access_ok = await check_channel_access(bot, CHAT_ID)
        if not access_ok:
            # ذخیره فایل placeholder با پیام خطا
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write("❌ خطا: ربات به کانال دسترسی ندارد.\n"
                        "لطفاً بررسی کنید:\n"
                        "1. ربات به عنوان عضو به کانال اضافه شده باشد.\n"
                        "2. آیدی کانال صحیح باشد (با پیشوند 100-).\n"
                        "3. ربات توسط ادمین کانال تایید شده باشد.")
            update_last_message_id(0)
            return

        # گام 2: دریافت پیام‌های جدید
        last_id = get_last_message_id()
        offset = last_id + 1 if last_id > 0 else None

        updates = await bot.get_updates(offset=offset, limit=20)
        new_messages = []
        for update in updates:
            if update.message and str(update.message.chat_id) == CHAT_ID:
                msg = update.message
                new_messages.append(f"ID: {msg.message_id}\nText: {msg.text or '[Non-text]'}")
                if msg.message_id > last_id:
                    last_id = msg.message_id

        # به‌روزرسانی آخرین ID
        update_last_message_id(last_id)

        # ذخیره خروجی
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            if new_messages:
                f.write("\n\n---\n\n".join(new_messages[-10:]))
                logging.info(f"✅ {len(new_messages[-10:])} پیام جدید ذخیره شد.")
            else:
                f.write("ℹ️ پیام جدیدی یافت نشد.\n"
                        "توجه: اگر کانال پیام دارد اما اینجا خالی است، ممکن است ربات دسترسی به پیام‌های قدیمی‌تر از زمان عضویت نداشته باشد.")
                logging.info("ℹ️ پیام جدیدی یافت نشد (اما دسترسی به کانال تأیید شده است).")

if __name__ == "__main__":
    asyncio.run(fetch_and_save())
