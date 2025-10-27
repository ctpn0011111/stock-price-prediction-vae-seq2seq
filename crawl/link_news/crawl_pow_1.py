import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# Tạo thư mục nếu chưa tồn tại
output_dir = "../dataset/link/pow/"
os.makedirs(output_dir, exist_ok=True)

BASE_URL = "https://pvpower.vn/vi/tag/bao-chi-voi-pv-power-21/page-{}"


def crawl_page(page, start_id):
    url = BASE_URL.format(page)
    print(f"Crawling: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Không thể truy cập {url}")
        return [], start_id

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # Lấy cả div col-sm-12 và col-sm-6
    posts = soup.find_all(
        "div", class_=["col-sm-12 post-item-wrapper", "col-sm-6 post-item-wrapper"]
    )

    for post in posts:
        # Tìm cả h2 và h3 có class "title mt-2"
        title_tag = post.find(["h2", "h3"], class_="title mt-2")
        if title_tag and title_tag.a:
            start_id += 1
            results.append(
                {
                    "id": start_id,
                    "title": title_tag.a.get_text(strip=True),
                    "url": "https://pvpower.vn" + title_tag.a["href"],
                    "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    return results, start_id


def main(max_pages=5):
    current_id = 0
    for page in range(1, max_pages + 1):
        data, current_id = crawl_page(page, current_id)
        if not data:
            break  # nếu hết dữ liệu thì dừng
        output_file = os.path.join(output_dir, f"page-{page}-bao-chi.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu: {output_file}")


if __name__ == "__main__":
    main(max_pages=28)  # crawl thử 10 trang
