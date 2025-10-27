import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

input_dir = "../../dataset/link/st8/"
output_dir = "../../dataset/data/st8/"
os.makedirs(output_dir, exist_ok=True)


def crawl_page(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Lỗi khi crawl {url}: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # --- Lấy title ---
    title_tag = soup.select_one("h1.detail__title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # --- Lấy ngày đăng ---
    pub_date_tag = soup.select_one("div.detail__time")
    pub_date = pub_date_tag.get_text(strip=True) if pub_date_tag else ""

    # --- Lấy content ---
    content_parts = []
    article = soup.select_one("div.i-article")
    if article:
        for p in article.find_all("p", recursive=True):
            # tìm trong p > span > span và p > span > span > strong
            for span in p.select("span > span, span > span > strong"):
                text = span.get_text(" ", strip=True)
                if text:
                    content_parts.append(text)

    content = "\n".join(content_parts).strip()
    return title, pub_date, content


def main():
    for file_name in os.listdir(input_dir):
        if not file_name.endswith(".json"):
            continue

        input_file = os.path.join(input_dir, file_name)
        output_file = os.path.join(output_dir, file_name)

        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []
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

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"✅ Đã lưu {len(results)} bài viết vào {output_file}")


if __name__ == "__main__":
    main()
