import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

# Đường dẫn lưu file
SAVE_DIR = "../../dataset/link/sgt/"
os.makedirs(SAVE_DIR, exist_ok=True)


def crawl_page(start):
    url = f"http://www.saigontel.vn/vi/tin-tuc-2.html?limit=9&start={start}"
    response = requests.get(url)
    response.encoding = "utf-8"

    if response.status_code != 200:
        print(f"❌ Lỗi khi tải trang start={start}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.find_all("h3", class_="catItemTitle")

    data = []
    for idx, item in enumerate(items, start=1):
        a_tag = item.find("a")
        if a_tag:
            link = a_tag.get("href")
            title = a_tag.get_text(strip=True)
            data.append(
                {
                    "id": idx,
                    "title": title,
                    "url": "http://www.saigontel.vn" + link,
                    "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    return data


def save_to_json(data, start):
    filename = os.path.join(SAVE_DIR, f"page_{start}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ Đã lưu dữ liệu trang start={start} vào file {filename}")


if __name__ == "__main__":
    # Vòng lặp từ start=0 đến start=981, bước nhảy 9
    for start in range(0, 982, 9):
        data = crawl_page(start)
        if data:
            save_to_json(data, start)
            data.clear()
        else:
            print(f"⚠️ Không có dữ liệu tại start={start}, dừng crawl.")
            break
