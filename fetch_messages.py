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
    match = re.search(r"(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{4,})", channel_str)
    return match.group(1) if match else None

async def scrape_telegram_channel(username, target_message_count):
    url = f"https://t.me/s/{username}"
    messages_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"   ↳ باز کردن صفحه: {url}")
            await page.goto(url, wait_until="networkidle")

            # اسکرول خودکار برای بارگذاری همه پیام‌ها
            previous_height = None
            scroll_attempts = 0
            while scroll_attempts < 50:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == previous_height:
                    break
                previous_height = current_height
                scroll_attempts += 1

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            message_blocks = soup.find_all("div", class_="tgme_widget_message")
            total = len(message_blocks)
            print(f"   ↳ مجموع پیام‌های یافت شده: {total}")

            # آخرین N پیام (جدیدترین‌ها در انتهای لیست هستند)
            latest_blocks = message_blocks[-target_message_count:] if total >= target_message_count else message_blocks

            for block in latest_blocks:
                # ---- استخراج لینک پست ----
                link_tag = block.find("a", class_="tgme_widget_message_date")
                post_link = None
                if link_tag and link_tag.has_attr("href"):
                    post_link = link_tag["href"]  # مثلاً https://t.me/hamvex/123
                else:
                    post_link = f"https://t.me/{username}/پیام_فاقد_لینک"
                # -------------------------

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

                # ---- استخراج متن یا نوع رسانه ----
                text_div = block.find("div", class_="tgme_widget_message_text")
                if text_div:
                    text = text_div.get_text(strip=True)
                else:
                    # تشخیص دقیق‌تر نوع رسانه
                    if block.find("a", class_="tgme_widget_message_photo_wrap"):
                        text = "[Image]"
                    elif block.find("div", class_="tgme_widget_message_video"):
                        text = "[Video]"
                    elif block.find("div", class_="tgme_widget_message_document"):
                        text = "[File]"
                    else:
                        text = "[Media]"
                # ---------------------------------

                messages_data.append({
                    "time": time_str,
                    "text": text,
                    "link": post_link
                })

        except Exception as e:
            print(f"   ❌ خطا در کانال {username}: {e}")
            messages_data = []
        finally:
            await browser.close()

    # معکوس کردن ترتیب (جدیدترین در ابتدا)
    messages_data.reverse()
    return messages_data

def save_channel_messages(username, messages_list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", username)
    file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"📢 کانال: {username}\n")
        f.write(f"📅 آخرین {len(messages_list)} پیام (جدیدترین در بالا):\n")
        f.write("="*50 + "\n\n")
        for i, msg in enumerate(messages_list, 1):
            f.write(f"{i}. زمان: {msg['time']}\n")
            f.write(f"   متن: {msg['text']}\n")
            f.write(f"   لینک: {msg['link']}\n\n")
    print(f"   ✅ ذخیره شد: {file_path}")

def create_zip():
    if not os.path.exists(OUTPUT_DIR) or not os.listdir(OUTPUT_DIR):
        print("⚠️ پوشه خالی است، ZIP ساخته نمی‌شود.")
        return
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=os.path.dirname(OUTPUT_DIR))
                zipf.write(full_path, arcname)
    print(f"📦 فایل ZIP نهایی: {ZIP_NAME}")

async def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ فایل {INPUT_FILE} یافت نشد")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    channels = []
    for line in lines:
        uname = extract_username(line)
        if uname:
            channels.append(uname)
        else:
            print(f"⚠️ خط نادیده گرفته: {line.strip()}")

    if not channels:
        print("❌ هیچ کانال معتبری یافت نشد")
        return

    print(f"🔍 {len(channels)} کانال: {', '.join(channels)}")

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for username in channels:
        print(f"\n🔄 پردازش کانال: {username}")
        msgs = await scrape_telegram_channel(username, NUM_MESSAGES)
        if msgs:
            save_channel_messages(username, msgs)
        else:
            print(f"   ⚠️ هیچ پیامی دریافت نشد")

    create_zip()
    print("\n✅ مرحله ۱ تمام شد. فایل messages.zip آماده است.")

if __name__ == "__main__":
    asyncio.run(main())
