import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime


class PVGasCrawler:
    def __init__(self, start_page=1, end_page=1, output_dir="./pvgas_data"):
        self.base_url = "https://www.pvgas.com.vn/tin-tuc/pgrid/588/pageid/"
        self.start_page = start_page
        self.end_page = end_page
        self.output_dir = output_dir
        self.create_output_directory()

    def create_output_directory(self):
        """Tạo thư mục lưu dữ liệu nếu chưa tồn tại"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def crawl_page(self, page_num):
        """Crawl dữ liệu từ một trang"""
        url = f"{self.base_url}{page_num}"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ Lỗi khi tải trang {page_num}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        crawl_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        h3_tags = soup.find_all("h3", class_="edn_articleTitle")

        for idx, h3 in enumerate(h3_tags, 1):
            a_tag = h3.find("a")
            if a_tag:
                title = a_tag.get_text(strip=True)
                href = a_tag.get("href")

                article = {
                    "id": f"page_{page_num}_{idx}",
                    "title": title,
                    "url": href,
                    "crawl_date": crawl_date,
                }
                articles.append(article)

        print(f"✅ Trang {page_num}: tìm thấy {len(articles)} bài viết")
        return articles

    def save_page_data(self, articles, page_num):
        """Lưu dữ liệu mỗi trang ra file JSON"""
        if not articles:
            return

        filename = f"pvgas_page_{page_num}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        print(f"💾 Đã lưu {len(articles)} bài viết vào {filepath}")

    def crawl(self):
        """Crawl từ start_page đến end_page"""
        for page in range(self.start_page, self.end_page + 1):
            articles = self.crawl_page(page)
            self.save_page_data(articles, page)


def main():
    # Bạn có thể chỉnh start_page và end_page ở đây
    start_page = 51
    end_page = 100

    crawler = PVGasCrawler(start_page=start_page, end_page=end_page)
    crawler.crawl()


if __name__ == "__main__":
    main()
