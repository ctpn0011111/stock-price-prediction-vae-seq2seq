import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime


class PetrolimexPressCrawler:
    def __init__(self, start_page=1, end_page=1, output_dir="../dataset/link/plx"):
        self.base_url = "https://www.petrolimex.com.vn/ndi/thong-cao-bao-chi/"
        self.start_page = start_page
        self.end_page = end_page
        self.output_dir = output_dir
        self.create_output_directory()

    def create_output_directory(self):
        """Tạo thư mục lưu dữ liệu nếu chưa có"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def crawl_page(self, page_num):
        """Crawl dữ liệu từ một trang"""
        url = f"{self.base_url}{page_num}.html"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ Không tải được trang {page_num} (status {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        crawl_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Tìm tất cả div chứa nội dung
        bodies = soup.find_all("div", class_="post-default__body")

        for idx, body in enumerate(bodies, 1):
            h3 = body.find("h3", class_="post-default__title")
            if not h3:
                continue

            a_tag = h3.find("a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")

            # Xử lý URL tuyệt đối
            if href.startswith("/"):
                href = "https://www.petrolimex.com.vn" + href

            article = {
                "id": f"page_{page_num}_{idx}",
                "title": title,
                "url": href,
                "crawl_date": crawl_date,
            }
            articles.append(article)

        print(f"✅ Trang {page_num}: lấy được {len(articles)} bài viết")
        return articles

    def save_page_data(self, articles, page_num):
        """Lưu dữ liệu mỗi trang thành file JSON"""
        if not articles:
            return

        filename = f"plx_press_page_{page_num}.json"
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
    # ✅ Chọn số trang cần crawl
    start_page = 1
    end_page = 25

    crawler = PetrolimexPressCrawler(start_page=start_page, end_page=end_page)
    crawler.crawl()


if __name__ == "__main__":
    main()
