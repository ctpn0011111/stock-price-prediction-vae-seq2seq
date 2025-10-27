import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

input_dir = "../../dataset/link/pvg/"
output_dir = "../../dataset/data/pvg/"
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, "articles.json")


def crawl_page(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Lỗi khi crawl {url}: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # --- Lấy title ---
    title_tag = soup.select_one("div.dnw-title a h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # --- Lấy ngày đăng ---
    pub_date_tag = soup.select_one("div.dnw-time a span")
    pub_date = pub_date_tag.get_text(strip=True) if pub_date_tag else ""

    # --- Lấy content ---
    content_parts = []

    # Lấy h3.desc
    desc_tag = soup.select_one("div.dnw-center h3.desc")
    if desc_tag:
        content_parts.append(desc_tag.get_text(strip=True))

    # Lấy tất cả p con trực tiếp của div.dnw-center
    for p in soup.select("div.dnw-center > p"):
        content_parts.append(p.get_text(" ", strip=True))

    # Lấy text trong table td (kể cả td > p)
    for td in soup.select("div.dnw-center table td"):
        text = td.get_text(" ", strip=True)
        if text:
            content_parts.append(text)

    content = "\n".join(content_parts).strip()

    return title, pub_date, content


def main():
    results = []

    # Duyệt qua tất cả file JSON trong thư mục input_dir
    for file_name in os.listdir(input_dir):
        if not file_name.endswith(".json"):
            continue
        input_file = os.path.join(input_dir, file_name)
        print(f"📂 Đang xử lý file: {input_file}")

        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            url = item.get("url")
            print(f"🔎 Crawling {url} ...")
            crawled = crawl_page(url)
            if not crawled:
                continue

            title, pub_date, content = crawled
            results.append(
                {
                    "id": item.get("id"),
                    "title": title,
                    "url": url,
                    "content": content,
                    "pub_date": pub_date,
                    "crawl_date": item.get(
                        "crawl_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ),
                }
            )

    # Xuất toàn bộ kết quả ra một file duy nhất
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã lưu {len(results)} bài viết vào {output_file}")


if __name__ == "__main__":
    main()
