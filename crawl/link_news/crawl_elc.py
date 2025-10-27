import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

# Đường dẫn lưu file
SAVE_DIR = "../../dataset/link/elc/"

# Tạo thư mục nếu chưa tồn tại
os.makedirs(SAVE_DIR, exist_ok=True)


def crawl_page(page):
    url = f"https://www.elcom.com.vn/tin-tuc-su-kien/ban-tin-elcom?page={page}"
    response = requests.get(url)
    response.encoding = "utf-8"  # xử lý tiếng Việt

    if response.status_code != 200:
        print(f"Lỗi khi tải trang {page}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.find_all("div", class_="elc-news-item")

    data = []
    for idx, item in enumerate(items, start=1):
        a_tag = item.find("a")
        if a_tag:
            link = a_tag.get("href")
            title = a_tag.get("title")
            data.append(
                {
                    "id": idx,
                    "title": title,
                    "url": link,
                    "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    return data


def save_to_json(data, page):
    filename = os.path.join(SAVE_DIR, f"page_{page}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ Đã lưu dữ liệu trang {page} vào file {filename}")


if __name__ == "__main__":
    # Crawl thử 3 trang (bạn có thể thay đổi số trang tuỳ ý)
    for page in range(1, 16):
        data = crawl_page(page)
        if data:
            save_to_json(data, page)
            # Xóa dữ liệu sau khi ghi file
            data.clear()
