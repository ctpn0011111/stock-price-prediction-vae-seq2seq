import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Thư mục lưu dữ liệu
output_dir = "../dataset/link/pvd/"
os.makedirs(output_dir, exist_ok=True)

BASE_URL = "https://www.pvdrilling.com.vn/tin-tuc/tin-pv-drilling?pagenumber={}"


def crawl_page(page, start_id):
    url = BASE_URL.format(page)
    print(f"Crawling: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ Không thể truy cập {url}")
        return [], start_id

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # Lấy tất cả div.item
    items = soup.find_all("div", class_="item")
    for item in items:
        a_tag = item.find("a")
        if a_tag and a_tag.get("href") and a_tag.get("title"):
            start_id += 1
            results.append(
                {
                    "id": start_id,
                    "title": a_tag["title"].strip(),
                    "url": a_tag["href"],
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
    main(max_pages=65)  # crawl thử 10 trang
