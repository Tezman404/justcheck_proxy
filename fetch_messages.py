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
NUM_MESSAGES = 10  # تعداد پیام مورد نظر برای هر کانال

def extract_username(channel_str):
    """استخراج نام کاربری از لینک‌های مختلف"""
    channel_str = channel_str.strip()
    match = re.search(r"(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{4,})", channel_str)
    return match.group(1) if match else None

async def scrape_telegram_channel(username, target_message_count):
    """
    اسکرپ کردن یک کانال تلگرام با اسکرول خودکار
    """
    url = f"https://t.me/s/{username}"
    messages_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"   ↳ در حال باز کردن صفحه: {url}")
            await page.goto(url, wait_until="networkidle")

            # --- بخش جدید: اسکرول خودکار برای بارگذاری همه پیام‌ها ---
            print(f"   ↳ اسکرول خودکار برای یافتن آخرین {target_message_count} پیام آغاز شد...")
            previous_height = None
            scroll_attempts = 0
            max_scrolls = 50  # یک محدودیت ایمنی برای جلوگیری از حلقه بی‌نهایت

            while scroll_attempts < max_scrolls:
                # اسکرول به پایین‌ترین نقطه صفحه
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                # منتظر بارگذاری محتوای جدید
                await page.wait_for_timeout(2000)  # 2 ثانیه صبر کنید (برای شبکه‌های کند می‌توانید بیشتر کنید)

                # بررسی کنید که آیا محتوای جدیدی بارگذاری شده است
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == previous_height:
                    # اگر ارتفاع صفحه تغییر نکرد، به انتها رسیده‌ایم
                    break
                previous_height = current_height
                scroll_attempts += 1
            # --------------------------------------------------------

            # پس از پایان اسکرول، محتوای صفحه را بگیرید
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # پیدا کردن همه بلوک‌های پیام
            message_blocks = soup.find_all("div", class_="tgme_widget_message")
            total_messages_found = len(message_blocks)
            print(f"   ↳ مجموع پیام‌های یافت شده در صفحه: {total_messages_found}")

            # استخراج تعداد مورد نظر از آخرین پیام‌ها
            # توجه: اولین المان در این لیست، قدیمی‌ترین پیام است و آخرین آن جدیدترین.
            # بنابراین ما به سراغ آخرین 'target_message_count' المان می‌رویم.
            latest_blocks = message_blocks[-target_message_count:] if total_messages_found >= target_message_count else message_blocks

            for block in latest_blocks:
                # ---- استخراج زمان ----
                time_tag = block.find("time")
                time_str = "زمان نامشخص"
                if time_tag and time_tag.has_attr("datetime"):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(time_tag["datetime"].replace('Z', '+00:00'))
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        time_str = time_tag.get_text(strip=True) or "زمان نامشخص"
                # ---------------------

                # ---- استخراج متن پیام یا تشخیص رسانه ----
                text_div = block.find("div", class_="tgme_widget_message_text")
                if text_div:
                    text = text_div.get_text(strip=True)
                else:
                    # تشخیص رسانه (عکس، ویدیو، فایل و ...)
                    media = (block.find("a", class_="tgme_widget_message_photo_wrap") or
                             block.find("div", class_="tgme_widget_message_video") or
                             block.find("div", class_="tgme_widget_message_document"))
                    if media:
                        text = "[📷 این یک پیام حاوی عکس، ویدیو یا فایل است]"
                    else:
                        text = "[⚠️ پیام بدون متن قابل نمایش]"
                # -------------------------------------

                messages_data.append(f"[{time_str}] {text}")

        except Exception as e:
            print(f"   ❌ خطا در پردازش کانال {username}: {e}")
            messages_data = [f"❌ خطا در بارگذاری صفحه: {str(e)}"]
        finally:
            await browser.close()

    # پیام‌ها را برعکس می‌کنیم تا جدیدترین در ابتدا قرار گیرد
    messages_data.reverse()
    return messages_data

def save_channel_messages(username, messages):
    """ذخیره پیام‌های یک کانال در یک فایل متنی"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", username)
    file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"📢 کانال: {username}\n")
        f.write(f"📅 آخرین {len(messages)} پیام (جدیدترین در بالا):\n")
        f.write("="*50 + "\n\n")
        for i, msg in enumerate(messages, 1):
            f.write(f"{i}. {msg}\n\n")
    print(f"   ✅ فایل ذخیره شد: {file_path}")

def create_zip():
    """ایجاد فایل ZIP از تمام فایل‌های متنی"""
    if not os.path.exists(OUTPUT_DIR) or not os.listdir(OUTPUT_DIR):
        print("⚠️ پوشه خالی است، فایل ZIP ساخته نمی‌شود.")
        return
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=os.path.dirname(OUTPUT_DIR))
                zipf.write(full_path, arcname)
    print(f"📦 فایل ZIP نهایی ساخته شد: {ZIP_NAME}")

async def main():
    """تابع اصلی برای اجرای کل فرآیند"""
    if not os.path.exists(INPUT_FILE):
        print(f"❌ فایل {INPUT_FILE} یافت نشد. لطفاً آن را ایجاد کنید.")
        return

    # خواندن کانال‌ها از فایل
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        channels_raw = f.readlines()

    channel_usernames = []
    for raw_line in channels_raw:
        username = extract_username(raw_line)
        if username:
            channel_usernames.append(username)
        else:
            print(f"⚠️ خط نادیده گرفته شد (فرمت نامعتبر): {raw_line.strip()}")

    if not channel_usernames:
        print("❌ هیچ کانال معتبری یافت نشد.")
        return

    print(f"🔍 {len(channel_usernames)} کانال برای پردازش پیدا شد: {', '.join(channel_usernames)}")

    # پاک کردن پوشه خروجی قبلی برای یک شروع تمیز
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # پردازش هر کانال
    for username in channel_usernames:
        print(f"\n🔄 در حال پردازش کانال: {username}")
        channel_messages = await scrape_telegram_channel(username, NUM_MESSAGES)
        if channel_messages:
            save_channel_messages(username, channel_messages)
        else:
            print(f"   ⚠️ هیچ پیامی برای کانال {username} یافت نشد.")

    create_zip()
    print("\n✅ همه کارها با موفقیت انجام شد. فایل messages.zip را از بخش Artifacts دانلود کنید.")

if __name__ == "__main__":
    asyncio.run(main())
