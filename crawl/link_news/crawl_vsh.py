import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Thư mục lưu file JSON
output_dir = "../dataset/link/vsh/"
os.makedirs(output_dir, exist_ok=True)

BASE_URL = "https://vshpc.evn.com.vn/c3/vi-VN/news-lf/Tin-tuc-1-734?page={}"


def crawl_page(page, start_id):
    url = BASE_URL.format(page)
    print(f"Crawling: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ Không thể truy cập {url}")
        return [], start_id

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # tìm tất cả article có class "g-pos-rel"
    articles = soup.find_all("article", class_="g-pos-rel")

    for article in articles:
        a_tag = article.find("a")
        if a_tag and a_tag.get("href") and a_tag.get("title"):
            start_id += 1
            results.append(
                {
                    "id": start_id,
                    "title": a_tag["title"].strip(),
                    "url": "https://vshpc.evn.com.vn" + a_tag["href"],
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
    main(max_pages=6)  # crawl thử 10 trang
