import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import urllib3

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.pvtrans.com"

# 📂 Đường dẫn thư mục lưu dữ liệu
SAVE_DIR = "../../dataset/data/bsr"
os.makedirs(SAVE_DIR, exist_ok=True)
SAVE_PATH = os.path.join(SAVE_DIR, "output.json")

# 📂 Đường dẫn file JSON chứa URL
INPUT_PATH = "../../dataset/link/bsr/pvtrans_data.json"

# 📄 Đọc file JSON đầu vào
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

output = []

for idx, item in enumerate(data, start=1):
    full_url = BASE_URL + item["url"]

    resp = requests.get(full_url, verify=False, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    # ---- Lấy tiêu đề ----
    title_tag = soup.select_one("div.container h4#blog_post_name")
    title = title_tag.get_text(strip=True) if title_tag else item.get("title", "")

    # ---- Lấy ngày đăng ----
    date_tag = soup.select_one("div.entry-meta time.entry-date")
    ngay_dang = date_tag.get_text(strip=True) if date_tag else ""

    # ---- Lấy nội dung ----
    content_parts = []

    # Phần 1: nội dung trong h5.entry-title > p
    h5_tag = soup.select_one("h5.entry-title p")
    if h5_tag:
        content_parts.append(h5_tag.get_text(" ", strip=True))

    # Phần 2: nội dung các span trong div.blog_content div.col-md-12.mb16.mt16
    spans = soup.select("div.blog_content div.col-md-12.mb16.mt16 span")
    for sp in spans:
        text = sp.get_text(" ", strip=True)
        if text:
            content_parts.append(text)

    content = "\n".join(content_parts)

    # ---- Ngày crawl ----
    ngay_crawl = datetime.now().strftime("%Y-%m-%d")

    # ---- Ghi dữ liệu ----
    output.append(
        {
            "id": idx,
            "title": title,
            "url": full_url,
            "content": content,
            "ngay_dang": ngay_dang,
            "ngay_crawl": ngay_crawl,
        }
    )

# 💾 Lưu ra file JSON
with open(SAVE_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"✅ Đã crawl xong, lưu tại: {SAVE_PATH}")
