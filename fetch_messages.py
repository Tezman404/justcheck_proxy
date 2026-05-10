import os
import re
import zipfile
import requests
from bs4 import BeautifulSoup
from datetime import datetime

INPUT_FILE = "channels.txt"
OUTPUT_DIR = "outputs"
ZIP_NAME = "messages.zip"
NUM_MESSAGES = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache"
}

def extract_username(channel_str):
    channel_str = channel_str.strip()
    match = re.search(r"(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{4,})", channel_str)
    return match.group(1) if match else None

def get_messages(username):
    url = f"https://t.me/s/{username}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return [f"❌ خطا: HTTP {resp.status_code}"]
        soup = BeautifulSoup(resp.text, "html.parser")
        # تمام بلوک‌های پیام
        message_blocks = soup.find_all("div", class_="tgme_widget_message")
        results = []
        for block in message_blocks[:NUM_MESSAGES]:
            # --- استخراج زمان ---
            time_tag = block.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                try:
                    dt = datetime.fromisoformat(time_tag["datetime"].replace('Z', '+00:00'))
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_str = time_tag.get_text(strip=True) or "زمان نامشخص"
            else:
                time_str = "زمان نامشخص"

            # --- استخراج متن (در صورت وجود) ---
            text_div = block.find("div", class_="tgme_widget_message_text")
            if text_div:
                text = text_div.get_text(strip=True)
            else:
                # بررسی وجود رسانه (عکس، ویدیو، صوت، فایل)
                media = block.find("a", class_="tgme_widget_message_photo_wrap") or \
                        block.find("div", class_="tgme_widget_message_video") or \
                        block.find("div", class_="tgme_widget_message_document")
                if media:
                    text = "[📷 Media: عکس یا ویدیو یا فایل]"
                else:
                    text = "[⚠️ پیام بدون محتوای قابل نمایش]"

            results.append(f"[{time_str}] {text}")
        
        if not results:
            return ["⚠️ هیچ پیامی یافت نشد (کانال خصوصی یا نامعتبر؟)"]
        return results
    except Exception as e:
        return [f"❌ خطا: {str(e)}"]

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
    import shutil
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # دوباره فایل‌ها را پیدا کنید (قبلاً در save_channel_messages ساخته شده)
    # اما در اینجا zip می‌سازیم
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=os.path.dirname(OUTPUT_DIR))
                zipf.write(full_path, arcname)
    print(f"📦 فایل ZIP: {ZIP_NAME}")

def main():
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
        print("❌ هیچ کانال معتبری نیست")
        return
    print(f"🔍 {len(channels)} کانال: {', '.join(channels)}")
    # حذف پوشه قبلی
    if os.path.exists(OUTPUT_DIR):
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    for username in channels:
        print(f"\n🔄 در حال گرفتن پیام‌های {username} ...")
        msgs = get_messages(username)
        save_channel_messages(username, msgs)
    create_zip()
    print("\n✅ تمام شد. فایل messages.zip آماده دانلود از بخش Artifacts است.")

if __name__ == "__main__":
    main()
