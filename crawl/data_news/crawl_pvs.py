import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

input_dir = "../../dataset/link/pvs/"
output_dir = "../../dataset/data/pvs/"
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
    title_tag = soup.select_one(
        "div.heading h1.detail-title.fz-44.text-main.fw-600.lh-12"
    )
    title = title_tag.get_text(strip=True) if title_tag else ""

    # --- Lấy ngày đăng ---
    pub_date_tag = soup.select_one(
        "div.sub-title.flex.align-center time.fz-16.fw-400.text-99"
    )
    pub_date = pub_date_tag.get_text(strip=True) if pub_date_tag else ""

    # --- Lấy content ---
    content_parts = []
    full_content = soup.select_one("div.full-content")
    if full_content:
        # lấy tất cả p
        for p in full_content.find_all("p", recursive=True):
            if "text-align: center" in (p.get("style") or ""):
                continue
            text = p.get_text(" ", strip=True)
            if text:
                content_parts.append(text)

        # lấy div span và div strong
        for div in full_content.find_all("div", recursive=True):
            if "text-align: center" in (div.get("style") or ""):
                continue
            for tag in div.find_all(["span", "strong"], recursive=True):
                text = tag.get_text(" ", strip=True)
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
