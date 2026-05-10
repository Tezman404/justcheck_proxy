import os
import re
import zipfile
import shutil
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

INPUT_FILE = "channels.txt"
OUTPUT_DIR = "outputs"
ZIP_NAME = "messages.zip"
NUM_MESSAGES = 10

def extract_username(channel_str):
    channel_str = channel_str.strip()
    # پشتیبانی از: https://t.me/username , @username , t.me/username , فقط username
    match = re.search(r"(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{4,})", channel_str)
    return match.group(1) if match else None

async def get_messages_with_playwright(username):
    """دریافت آخرین پیام‌ها با استفاده از مرورگر واقعی (بدون کش)"""
    url = f"https://t.me/s/{username}"
    results = []
    async with async_playwright() as p:
        # راه‌اندازی مرورگر Chromium در حالت بدون رابط (headless)
        browser = await p.chromium.launch(headless=True)
        # ایجاد یک صفحه جدید با viewport استاندارد
        page = await browser.new_page()
        try:
            # رفتن به آدرس و منتظر ماندن تا شبکه کاملاً آرام شود
            await page.goto(url, wait_until="networkidle", timeout=30000)
            # منتظر بمان تا اولین پیام ظاهر شود (حداکثر ۱۰ ثانیه)
            await page.wait_for_selector(".tgme_widget_message", timeout=10000)
            # گرفتن محتوای HTML کامل پس از بارگذاری داینامیک
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            message_blocks = soup.find_all("div", class_="tgme_widget_message")

            for block in message_blocks[:NUM_MESSAGES]:
                # ---- استخراج زمان ----
                time_tag = block.find("time")
                if time_tag and time_tag.has_attr("datetime"):
                    try:
                        # تبدیل ISO 8601 به فرمت خوانا
                        dt_str = time_tag["datetime"].replace('Z', '+00:00')
                        from datetime import datetime
                        dt = datetime.fromisoformat(dt_str)
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        time_str = time_tag.get_text(strip=True) or "زمان نامشخص"
                else:
                    time_str = "زمان نامشخص"

                # ---- استخراج متن یا شناسایی رسانه ----
                text_div = block.find("div", class_="tgme_widget_message_text")
                if text_div:
                    text = text_div.get_text(strip=True)
                else:
                    # بررسی وجود رسانه (عکس، ویدیو، فایل)
                    media_photo = block.find("a", class_="tgme_widget_message_photo_wrap")
                    media_video = block.find("div", class_="tgme_widget_message_video")
                    media_doc = block.find("div", class_="tgme_widget_message_document")
                    if media_photo or media_video or media_doc:
                        text = "[📷 رسانه: عکس/ویدیو/فایل]"
                    else:
                        text = "[⚠️ بدون متن قابل نمایش]"
                results.append(f"[{time_str}] {text}")

            if not results:
                results.append("⚠️ هیچ پیامی یافت نشد (کانال خصوصی یا نامعتبر؟)")

        except Exception as e:
            results.append(f"❌ خطا در بارگذاری صفحه: {str(e)}")
        finally:
            await browser.close()
    return results

def save_channel_messages(username, messages):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", username)
    file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"📢 کانال: {username}\n")
        f.write(f"📅 آخرین {len(messages)} پیام (جدیدترین در بالا):\n")
        f.write("="*50 + "\n\n")
        for i, msg in enumerate(messages, 1):
            f.write(f"{i}. {msg}\n\n")
    print(f"✅ ذخیره شد: {file_path}")

def create_zip():
    """ایجاد فایل ZIP از تمام فایل‌های داخل outputs"""
    if not os.path.exists(OUTPUT_DIR) or not os.listdir(OUTPUT_DIR):
        print("⚠️ پوشه خالی است، ZIP ساخته نمی‌شود.")
        return
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=os.path.dirname(OUTPUT_DIR))
                zipf.write(full_path, arcname)
    print(f"📦 فایل ZIP ساخته شد: {ZIP_NAME} (حجم: {os.path.getsize(ZIP_NAME)} بایت)")

async def main():
    # بررسی وجود فایل کانال‌ها
    if not os.path.exists(INPUT_FILE):
        print(f"❌ فایل {INPUT_FILE} یافت نشد")
        return

    # خواندن خطوط
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # استخراج نام کاربری معتبر
    channels = []
    for line in lines:
        uname = extract_username(line)
        if uname:
            channels.append(uname)
        else:
            print(f"⚠️ خط نادیده گرفته شد: {line.strip()}")

    if not channels:
        print("❌ هیچ کانال معتبری یافت نشد")
        return

    print(f"🔍 تعداد کانال‌ها: {len(channels)} -> {', '.join(channels)}")

    # پاک کردن پوشه قبلی (برای شروع تمیز)
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # پردازش هر کانال
    for username in channels:
        print(f"\n🔄 در حال دریافت پیام‌های کانال: {username}")
        msgs = await get_messages_with_playwright(username)
        save_channel_messages(username, msgs)

    create_zip()
    print("\n✅ عملیات با موفقیت پایان یافت. فایل messages.zip را از بخش Artifacts دانلود کنید.")

if __name__ == "__main__":
    asyncio.run(main())
