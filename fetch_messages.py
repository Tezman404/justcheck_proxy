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
    # ... (این تابع مثل قبل بدون تغییر است) ...
    channel_str = channel_str.strip()
    match = re.search(r"(?:https?://)?(?:t\.me/)?@?([a-zA-Z][a-zA-Z0-9_]{4,})", channel_str)
    return match.group(1) if match else None

async def get_messages_with_playwright(username):
    url = f"https://t.me/s/{username}"
    messages = []
    
    # راه‌اندازی مرورگر بدون رابط کاربری
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # رفتن به صفحه کانال
            await page.goto(url, wait_until='networkidle')
            
            # اینجا می‌تونیم صبر کنیم تا محتوای صفحه کامل بارگذاری بشه
            # صبر برای ظاهر شدن اولین پیام
            await page.wait_for_selector('.tgme_widget_message', timeout=30000)
            
            # گرفتن HTML نهایی صفحه
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # پیدا کردن لیست پیام‌ها
            message_blocks = soup.find_all("div", class_="tgme_widget_message")
            
            # پردازش پیام‌ها (مشابه روش قبل)
            for block in message_blocks[:NUM_MESSAGES]:
                # ... (کد پردازش پیام‌ها مثل قبل) ...
                # (متن پیام، زمان، عکس و ...)
                pass
                
        except Exception as e:
            print(f"خطا در دریافت از کانال {username}: {e}")
            messages.append(f"❌ خطا در دریافت محتوا: {str(e)}")
        finally:
            await browser.close()
    
    return messages

async def main():
    # ... (کد خواندن فایل کانال‌ها مثل قبل) ...
    # حلقه اصلی که برای هر کانال تابع بالا رو صدا می‌زنه
    for username in channels:
        print(f"\n🔄 در حال پردازش کانال: {username}")
        msgs = await get_messages_with_playwright(username)
        # ... (کد ذخیره در فایل و ساخت ZIP مثل قبل) ...

if __name__ == "__main__":
    asyncio.run(main())
