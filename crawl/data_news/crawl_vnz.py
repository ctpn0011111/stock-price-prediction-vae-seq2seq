import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Thư mục chứa file link json
input_dir = "../../dataset/link/vnz/"
# Thư mục lưu kết quả crawl chi tiết
output_dir = "../../dataset/data/vnz/"
os.makedirs(output_dir, exist_ok=True)


def crawl_article(url):
    """Crawl chi tiết bài viết từ URL"""
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
    title_tag = soup.select_one("div.post-description h1.post-title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # --- Ngày đăng ---
    date_tag = soup.select_one("div.flex.post-info p")
    ngay_dang = date_tag.get_text(strip=True) if date_tag else ""

    # --- Nội dung ---
    spans = soup.select("div.post-content span")
    if spans:
        parts = [s.get_text(" ", strip=True) for s in spans if s.get_text(strip=True)]
        content = "\n".join(parts)
    else:
        # fallback: lấy toàn bộ text trong post-content
        content_div = soup.select_one("div.post-content")
        content = content_div.get_text(" ", strip=True) if content_div else ""

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

        # Xuất file json mới
        output_file = os.path.join(output_dir, f"data_{file}")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"✅ Đã lưu {output_file}")


if __name__ == "__main__":
    process_files()
