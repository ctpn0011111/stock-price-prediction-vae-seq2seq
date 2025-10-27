import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Thư mục lưu dữ liệu
output_dir = "../dataset/link/oil/"
os.makedirs(output_dir, exist_ok=True)

BASE_URL = "https://www.pvoil.com.vn/tin-pvoil?page={}"


def crawl_page(page, start_id):
    url = BASE_URL.format(page)
    print(f"Crawling: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ Không thể truy cập {url}")
        return [], start_id

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # Tìm tất cả caption > h3.title > a.line-clamp-2
    captions = soup.find_all("div", class_="caption")
    for cap in captions:
        h3 = cap.find("h3", class_="title")
        if not h3:
            continue
        a_tag = h3.find("a")
        if a_tag and a_tag.get("href"):
            start_id += 1
            results.append(
                {
                    "id": start_id,
                    "title": a_tag.get_text(strip=True),
                    "url": "https://www.pvoil.com.vn" + a_tag["href"],
                    "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    return results, start_id


def main(max_pages=5):
    current_id = 0
    for page in range(1, max_pages + 1):
        data, current_id = crawl_page(page, current_id)
        if not data:
            break  # hết dữ liệu thì dừng
        output_file = os.path.join(output_dir, f"page-{page}-tin-oil.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu: {output_file}")


if __name__ == "__main__":
    main(max_pages=33)
