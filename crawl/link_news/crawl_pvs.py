import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Tạo thư mục lưu file
output_dir = "../dataset/link/pvs/"
os.makedirs(output_dir, exist_ok=True)

BASE_URL = "https://www.ptsc.com.vn/tin-tuc/tin-dau-khi-1?pagenumber={}"


def crawl_page(page, start_id):
    url = BASE_URL.format(page)
    print(f"Crawling: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ Không thể truy cập {url}")
        return [], start_id

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # tìm div có class caption
    captions = soup.find_all("div", class_="caption")

    for caption in captions:
        # Tìm h2.title hoặc h3.title
        title_tag = caption.find(["h2", "h3"], class_="title")
        if title_tag and title_tag.a:
            start_id += 1
            results.append(
                {
                    "id": start_id,
                    "title": title_tag.a.get_text(strip=True),
                    "url": title_tag.a["href"],
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
    main(max_pages=15)  # crawl thử 10 trang
