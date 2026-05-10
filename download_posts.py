import os
import re
import asyncio
import zipfile
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

INPUT_FILE = "to_download.txt"
OUTPUT_DIR = "downloads"
ZIP_NAME = "selected_posts.zip"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

async def download_media_from_post(post_url, output_folder):
    """
    دریافت صفحه یک پست خاص و دانلود فایل رسانه (اگر وجود داشته باشد)
    بازگرداند: (متن پیام، مسیر فایل دانلود شده یا None)
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(post_url, wait_until="networkidle")
            await page.wait_for_selector(".tgme_widget_message", timeout=10000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            msg_block = soup.find("div", class_="tgme_widget_message")
            if not msg_block:
                return "❌ پیام یافت نشد", None

            # استخراج متن
            text_div = msg_block.find("div", class_="tgme_widget_message_text")
            text = text_div.get_text(strip=True) if text_div else "[بدون متن]"

            # استخراج لینک دانلود مستقیم (اولویت با عکس، ویدیو، فایل)
            media_link = None
            photo_link = msg_block.find("a", class_="tgme_widget_message_photo_wrap")
            if photo_link and photo_link.has_attr("href"):
                # لینک عکس معمولاً در style یا data-* نیست، ولی خود href به صفحه بزرگ‌تر می‌رود
                # برای دانلود مستقیم تصویر باید از تصویر کوچک استفاده کنیم: یافتن img داخل آن
                img = photo_link.find("img")
                if img and img.has_attr("src"):
                    media_link = img["src"]
            if not media_link:
                video = msg_block.find("video")
                if video and video.has_attr("src"):
                    media_link = video["src"]
            if not media_link:
                doc_link = msg_block.find("a", class_="tgme_widget_message_document")
                if doc_link and doc_link.has_attr("href"):
                    media_link = doc_link["href"]

            downloaded_file = None
            if media_link:
                # دانلود فایل
                try:
                    resp = requests.get(media_link, stream=True, timeout=30)
                    if resp.status_code == 200:
                        # استخراج نام فایل از url یا محتوا
                        content_disposition = resp.headers.get('content-disposition', '')
                        if 'filename=' in content_disposition:
                            filename = content_disposition.split('filename=')[-1].strip('"')
                        else:
                            filename = os.path.basename(media_link.split('?')[0]) or "media_file"
                        if not filename:
                            filename = "download"
                        safe_name = sanitize_filename(filename)
                        filepath = os.path.join(output_folder, safe_name)
                        with open(filepath, 'wb') as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded_file = filepath
                        print(f"   ✅ دانلود شد: {safe_name}")
                    else:
                        print(f"   ⚠️ خطا در دانلود: HTTP {resp.status_code}")
                except Exception as e:
                    print(f"   ❌ خطا در دانلود فایل: {e}")

            return text, downloaded_file
        except Exception as e:
            return f"❌ خطا: {str(e)}", None
        finally:
            await browser.close()

async def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ فایل {INPUT_FILE} یافت نشد. لطفاً آن را با لینک پست‌ها پر کنید.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        print("⚠️ هیچ لینکی در فایل to_download.txt یافت نشد.")
        return

    print(f"🔍 تعداد لینک‌ها: {len(links)}")

    # پاک کردن پوشه قبلی
    if os.path.exists(OUTPUT_DIR):
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    ensure_dir(OUTPUT_DIR)

    report_lines = []
    for idx, link in enumerate(links, 1):
        print(f"\n🔄 پردازش {idx}: {link}")
        text, media_file = await download_media_from_post(link, OUTPUT_DIR)
        report_lines.append(f"لینک: {link}\nمتن: {text}\nفایل: {media_file if media_file else 'بدون فایل'}\n{'-'*40}")

    # ذخیره گزارش
    report_path = os.path.join(OUTPUT_DIR, "report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # ساخت ZIP
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUTPUT_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=os.path.dirname(OUTPUT_DIR))
                zipf.write(full_path, arcname)
    print(f"\n📦 فایل ZIP نهایی: {ZIP_NAME}")

if __name__ == "__main__":
    asyncio.run(main())
