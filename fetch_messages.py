import os
import requests
from bs4 import BeautifulSoup

# --- تنظیمات ---
CHANNEL_USERNAME = "PinkProxy"
BASE_URL = f"https://t.me/s/{CHANNEL_USERNAME}"
OUTPUT_FILE = "latest_messages.txt"
NUM_MESSAGES = 10

def get_latest_messages():
    print(f"🔄 در حال دریافت آخرین {NUM_MESSAGES} پیام از کانال @{CHANNEL_USERNAME}...")
    response = requests.get(BASE_URL)
    
    if response.status_code != 200:
        print(f"❌ خطا در دریافت صفحه! وضعیت: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    # پیدا کردن همهٔ پیام‌های متنی با استفاده از کلاس مخصوص آنها
    message_divs = soup.find_all("div", class_="tgme_widget_message_text")
    
    messages = []
    for div in message_divs[:NUM_MESSAGES]:
        text = div.get_text(strip=True)
        if text:
            messages.append(text)
    
    print(f"✅ {len(messages)} پیام جدید پیدا شد.\n"+ "="*30)
    return messages

def save_messages(messages):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        if not messages:
            f.write("⚠️ پیامی در کانال یافت نشد.")
            return
        for i, msg in enumerate(messages, 1):
            f.write(f"📨 پیام {i}:\n{msg}\n\n{'-'*30}\n")
    print(f"📁 پیام‌ها در فایل '{OUTPUT_FILE}' ذخیره شدند.")

if __name__ == "__main__":
    latest_msgs = get_latest_messages()
    save_messages(latest_msgs)
