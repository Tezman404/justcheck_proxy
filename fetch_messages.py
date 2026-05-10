import os
import re
import zipfile
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ----------------- تنظیمات -----------------
INPUT_FILE = "channels.txt"      # فایل ورودی حاوی لینک کانال‌ها
OUTPUT_DIR = "outputs"           # پوشه موقت برای ذخیره فایل‌های متنی
ZIP_NAME = "messages.zip"        # نام فایل فشرده نهایی
NUM_MESSAGES = 10                # تعداد پیام آخر مورد نظر
# ------------------------------------------

def extract_username(channel_str):
    """تبدیل لینک یا @username به نام کاربری خالص"""
    channel_str = channel_str.strip()
    # حذف https://t.me/ , t.me/ , @
    match = re.search(r"(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{4,})", channel_str)
    if match:
        return match.group(1)
    return None

def get_messages(username):
    """دریافت ۱۰ پیام آخر از t.me/s/username به همراه زمان"""
    url = f"https://t.me/s/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return [f"❌ خطا: وضعیت HTTP {resp.status_code}"]
        soup = BeautifulSoup(resp.text, "html.parser")
        # هر پیام در یک div با کلاس tgme_widget_message قرار دارد
        messages_divs = soup.find_all("div", class_="tgme_widget_message")
        results = []
        for msg_div in messages_divs[:NUM_MESSAGES]:
            # استخراج متن
            text_div = msg_div.find("div", class_="tgme_widget_message_text")
            text = text_div.get_text(strip=True) if text_div else "[بدون متن]"
            # استخراج زمان
            time_tag = msg_div.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                # فرمت ISO: 2026-05-11T18:30:00+00:00
                dt_str = time_tag["datetime"]
                # تبدیل به قالب خوانا
                try:
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_str = time_tag.get_text(strip=True) or "زمان نامشخص"
            else:
                time_str = "زمان نامشخص"
            results.append(f"[{time_str}] {text}")
        if not results:
            return ["⚠️ هیچ پیامی یافت نشد (ممکن است کانال خصوصی یا نامعتبر باشد)."]
        return results
    except Exception as e:
        return [f"❌ خطا در دریافت کانال: {str(e)}"]

def save_channel_messages(username, messages):
    """ذخیره پیام‌های یک کانال در فایل متنی"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", username)
    file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"📢 کانال: {username}\n")
        f.write(f"📅 آخرین {len(messages)} پیام:\n")
        f.write("="*50 + "\n\n")
        for i, msg in enumerate(messages, 1):
            f.write(f"{i}. {msg}\n\n")
    print(f"✅ ذخیره شد: {file_path}")

def create_zip():
    """ایجاد فایل zip از تمام فایل‌های داخل پوشه outputs"""
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=os.path.dirname(OUTPUT_DIR))
                zipf.write(file_path, arcname)
    print(f"📦 فایل ZIP ساخته شد: {ZIP_NAME}")

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ فایل {INPUT_FILE} یافت نشد!")
        return
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    channels = []
    for line in lines:
        username = extract_username(line)
        if username:
            channels.append(username)
        else:
            print(f"⚠️ خط نامعتبر نادیده گرفته شد: {line.strip()}")
    if not channels:
        print("❌ هیچ کانال معتبری یافت نشد.")
        return
    print(f"🔍 {len(channels)} کانال پیدا شد:")
    for ch in channels:
        print(f"   - {ch}")
    # پاک کردن پوشه قبلی (اختیاری)
    if os.path.exists(OUTPUT_DIR):
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    for username in channels:
        print(f"\n🔄 در حال پردازش کانال: {username}")
        msgs = get_messages(username)
        save_channel_messages(username, msgs)
    create_zip()
    print("\n✅ کار انجام شد. فایل messages.zip آماده دانلود است.")

if __name__ == "__main__":
    main()
