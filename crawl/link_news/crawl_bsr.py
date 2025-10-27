import time
import json
import os
import requests
from bs4 import BeautifulSoup

# === URL gốc với page số 1 ===
base_url = "https://www.pvtrans.com/blog/tin-hoat-ong-pvtrans-11/page/{}"

# === Thư mục lưu file JSON ===
output_dir = "../../dataset/link/bsr/"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "pvtrans_data.json")


def extract_data(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    data = []

    # --- Nguồn 1: article.entry-attachment > a.button-md.primary-button ---
    articles = soup.find_all("article", class_="entry-attachment")
    for art in articles:
        a_tag = art.find("a", class_="button-md primary-button")
        if a_tag:
            data.append({"url": a_tag.get("href"), "title": a_tag.get_text(strip=True)})

    # --- Nguồn 2: div.entry-body > a.button-md.primary-button ---
    entries = soup.find_all("div", class_="entry-body")
    for entry in entries:
        a_tag = entry.find("a", class_="button-md primary-button")
        if a_tag:
            data.append({"url": a_tag.get("href"), "title": a_tag.get_text(strip=True)})

    return data


all_data = []
max_pages = 30  # Giới hạn an toàn, tránh vòng lặp vô tận

for page in range(1, max_pages + 1):
    url = base_url.format(page)
    print(f"🔎 Đang crawl trang {page}: {url}")

    resp = requests.get(url, timeout=10, verify=False)

    if resp.status_code != 200:
        print(
            f"❌ Trang {page} không tồn tại hoặc lỗi ({resp.status_code}) -> Dừng crawl."
        )
        break

    page_data = extract_data(resp.text)

    if not page_data:  # Không còn dữ liệu
        print(f"❌ Trang {page} không có dữ liệu -> Dừng crawl.")
        break

    all_data.extend(page_data)

    # Ghi file JSON (ghi đè mỗi vòng, không cộng dồn file cũ)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã lấy {len(page_data)} bài từ trang {page}. Tổng cộng: {len(all_data)}")

    time.sleep(1)  # nghỉ 1s tránh bị chặn

print(f"\n🎯 Hoàn tất crawl. Tổng số bài viết lấy được: {len(all_data)}")
print(f"📂 Dữ liệu lưu tại: {output_path}")
