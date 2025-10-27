import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Thư mục lưu dữ liệu
output_dir = "../dataset/link/oil/"
os.makedirs(output_dir, exist_ok=True)

BASE_URL = "https://www.pvoil.com.vn/tin-lien-quan?page={}"


def crawl_page(page, start_id):
    url = BASE_URL.format(page)
    print(f"Crawling: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ Không thể truy cập {url}")
        return [], start_id

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # Tìm tất cả item
    items = soup.find_all("div", class_="news-other-item item-hover")

    for item in items:
        img_container = item.find("div", class_="image img-contain")
        if not img_container:
            continue
        a_tag = img_container.find("a")
        img_tag = a_tag.find("img") if a_tag else None

        if a_tag and img_tag:
            start_id += 1
            results.append(
                {
                    "id": start_id,
                    "title": img_tag.get("alt", "").strip(),
                    "url": "https://www.pvoil.com.vn" + a_tag.get("href"),
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
        output_file = os.path.join(output_dir, f"page-{page}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu: {output_file}")


if __name__ == "__main__":
    main(max_pages=270)  # crawl thử 10 trang
