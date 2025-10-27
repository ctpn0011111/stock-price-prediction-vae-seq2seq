import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Đường dẫn input/output
input_dir = "../../dataset/link/pvd/"
output_dir = "../../dataset/data/pvd/"
os.makedirs(output_dir, exist_ok=True)


def crawl_article(url):
    """Crawl chi tiết bài viết PVD"""
    try:
        r = requests.get(url, timeout=15)
        r.encoding = "utf-8"
        if r.status_code != 200:
            print(f"❌ Lỗi HTTP {r.status_code}: {url}")
            return None
    except Exception as e:
        print(f"❌ Lỗi request {url}: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # --- Tiêu đề ---
    title_div = soup.find("div", class_="pvd-title")
    title = title_div.h1.get_text(strip=True) if title_div and title_div.h1 else ""

    # --- Ngày đăng ---
    date_div = soup.find("div", class_="date")
    ngay_dang = date_div.time.get_text(strip=True) if date_div and date_div.time else ""

    # --- Nội dung ---
    content_parts = []
    content_div = soup.find("div", class_="full-content")
    if content_div:
        for p in content_div.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text:
                content_parts.append(text)

    content = "\n".join(content_parts)

    return title, ngay_dang, content


def process_files():
    for file in sorted(os.listdir(input_dir)):
        if not file.endswith(".json"):
            continue

        input_file = os.path.join(input_dir, file)
        with open(input_file, "r", encoding="utf-8") as f:
            try:
                articles = json.load(f)
            except Exception as e:
                print(f"❌ Lỗi đọc {input_file}: {e}")
                continue

        output_data = []
        for art in articles:
            url = art.get("url")
            aid = art.get("id")
            print(f"[{file}] Crawling: {url}")

            result = crawl_article(url)
            if result:
                title, ngay_dang, content = result
                output_data.append(
                    {
                        "id": aid,
                        "title": title,
                        "url": url,
                        "content": content,
                        "ngay_dang": ngay_dang,
                        "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            else:
                output_data.append(
                    {
                        "id": aid,
                        "title": "",
                        "url": url,
                        "content": "",
                        "ngay_dang": "",
                        "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

        # Xuất file json kết quả
        output_file = os.path.join(output_dir, f"data_{file}")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"✅ Đã lưu {output_file}")


if __name__ == "__main__":
    process_files()
