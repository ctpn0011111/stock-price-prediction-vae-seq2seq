import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
import glob

# Đường dẫn input và output
INPUT_DIR = "../../dataset/link/elc/"
OUTPUT_DIR = "../../dataset/data/elc/"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(text):
    """Loại bỏ khoảng trắng thừa"""
    return " ".join(text.split())


def crawl_article(url):
    response = requests.get(url)
    response.encoding = "utf-8"
    if response.status_code != 200:
        print(f"❌ Không truy cập được {url}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Lấy tiêu đề
    title_tag = soup.find("h2", class_="news-title-sub")
    title = clean_text(title_tag.get_text()) if title_tag else ""

    # Lấy ngày đăng
    date_tag = soup.find("h4", class_="news-time")
    ngay_dang = clean_text(date_tag.get_text()) if date_tag else ""

    # Lấy nội dung
    content_div = soup.find("div", id="content")
    content = ""
    if content_div:
        # Lấy toàn bộ text trong thẻ div#content
        content = clean_text(content_div.get_text(separator=" "))

    return title, ngay_dang, content


def process_json_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        articles = json.load(f)

    results = []
    for item in articles:
        article_id = item["id"]
        url = item["url"]

        print(f"🔍 Đang crawl {url}")
        data = crawl_article(url)
        if data:
            title, ngay_dang, content = data
            results.append(
                {
                    "id": article_id,
                    "title": title,
                    "url": url,
                    "content": content,
                    "ngay_dang": ngay_dang,
                    "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    return results


def save_to_json(data, filename):
    out_path = os.path.join(OUTPUT_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ Đã lưu file {out_path}")


if __name__ == "__main__":
    # Lấy tất cả file JSON trong thư mục input
    json_files = glob.glob(os.path.join(INPUT_DIR, "*.json"))

    for filepath in json_files:
        filename = os.path.basename(filepath)
        print(f"📂 Đang xử lý file: {filename}")

        data = process_json_file(filepath)
        if data:
            save_to_json(data, filename)
