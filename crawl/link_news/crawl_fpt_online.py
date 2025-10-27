import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
from datetime import datetime
import time
import logging


class FPTOnlineCrawler:
    def __init__(self):
        self.base_url = "https://fptonline.net/tin-tuc/page/"
        self.output_dir = "../dataset/link/fpt_online"
        self.setup_logging()
        self.setup_driver()
        self.create_output_directory()

    def setup_logging(self):
        """Thiết lập logging để theo dõi quá trình crawl"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("fpt_online_crawler.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Thiết lập Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Chạy ở chế độ headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("WebDriver đã được khởi tạo thành công")
        except Exception as e:
            self.logger.error(f"Lỗi khởi tạo WebDriver: {e}")
            raise

    def create_output_directory(self):
        """Tạo thư mục lưu trữ nếu chưa tồn tại"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Đã tạo thư mục: {self.output_dir}")

    def check_page_exists(self, page_num):
        """Kiểm tra xem trang có tồn tại hay không"""
        url = f"{self.base_url}{page_num}.html"
        try:
            self.driver.get(url)
            # Đợi trang load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Kiểm tra xem có phần tử h3 với class item-title không
            h3_titles = self.driver.find_elements(By.CSS_SELECTOR, "h3.item-title")

            if h3_titles:
                return True
            else:
                self.logger.warning(
                    f"Trang {page_num} không có nội dung hoặc đã hết dữ liệu"
                )
                return False

        except Exception as e:
            self.logger.error(f"Lỗi khi kiểm tra trang {page_num}: {e}")
            return False

    def extract_data_from_page(self, page_num):
        """Trích xuất dữ liệu từ một trang"""
        url = f"{self.base_url}{page_num}.html"
        articles = []

        try:
            self.driver.get(url)
            # Đợi trang load hoàn toàn
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h3.item-title"))
            )

            # Lấy HTML source và parse bằng BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Tìm tất cả h3 với class 'item-title'
            h3_titles = soup.find_all("h3", class_="item-title")

            for h3 in h3_titles:
                try:
                    # Tìm thẻ a với class 'item-title-a' trong h3
                    a_tag = h3.find("a", class_="item-title-a")

                    if a_tag:
                        title = a_tag.get_text(strip=True)
                        href = a_tag.get("href", "")

                        # Xử lý URL tương đối nếu cần
                        if href.startswith("/"):
                            full_url = f"https://fptonline.net{href}"
                        elif href.startswith("../"):
                            full_url = f"https://fptonline.net/{href[3:]}"
                        elif not href.startswith("http"):
                            full_url = f"https://fptonline.net/{href}"
                        else:
                            full_url = href

                        article = {"title": title, "url": full_url}
                        articles.append(article)

                except Exception as e:
                    self.logger.warning(
                        f"Lỗi khi xử lý một bài viết trên trang {page_num}: {e}"
                    )
                    continue

            self.logger.info(
                f"Đã trích xuất {len(articles)} bài viết từ trang {page_num}"
            )
            return articles

        except Exception as e:
            self.logger.error(f"Lỗi khi trích xuất dữ liệu từ trang {page_num}: {e}")
            return []

    def save_page_data(self, articles, page_num):
        """Lưu dữ liệu của một trang vào file JSON"""
        if not articles:
            return

        filename = f"fpt_online_page_{page_num}.json"
        filepath = os.path.join(self.output_dir, filename)

        # Thêm ID tự động tăng và ngày crawl
        crawl_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted_articles = []
        for idx, article in enumerate(articles, 1):
            formatted_article = {
                "id": f"page_{page_num}_{idx}",
                "title": article["title"],
                "url": article["url"],
                "crawl_date": crawl_date,
            }
            formatted_articles.append(formatted_article)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(formatted_articles, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Đã lưu {len(formatted_articles)} bài viết vào {filepath}"
            )

        except Exception as e:
            self.logger.error(f"Lỗi khi lưu file {filepath}: {e}")

    def save_all_data(self, all_articles):
        """Lưu tất cả dữ liệu vào một file tổng hợp"""
        if not all_articles:
            return

        filename = "fpt_online_all_articles.json"
        filepath = os.path.join(self.output_dir, filename)

        # Thêm ID tự động tăng và ngày crawl
        crawl_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted_articles = []
        for idx, article in enumerate(all_articles, 1):
            formatted_article = {
                "id": idx,
                "title": article["title"],
                "url": article["url"],
                "crawl_date": crawl_date,
            }
            formatted_articles.append(formatted_article)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(formatted_articles, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Đã lưu tổng cộng {len(formatted_articles)} bài viết vào {filepath}"
            )

        except Exception as e:
            self.logger.error(f"Lỗi khi lưu file tổng hợp {filepath}: {e}")

    def crawl_all_pages(self):
        """Crawl tất cả các trang từ đầu đến cuối"""
        page_num = 1
        all_articles = []

        self.logger.info("Bắt đầu crawl dữ liệu từ FPT Online")

        while True:
            self.logger.info(f"Đang crawl trang {page_num}...")

            # Kiểm tra xem trang có tồn tại không
            if not self.check_page_exists(page_num):
                self.logger.info(
                    f"Đã crawl xong. Trang {page_num} không tồn tại hoặc không có dữ liệu."
                )
                break

            # Trích xuất dữ liệu từ trang
            articles = self.extract_data_from_page(page_num)

            if articles:
                # Lưu dữ liệu trang hiện tại
                self.save_page_data(articles, page_num)

                # Thêm vào danh sách tổng
                all_articles.extend(articles)

                self.logger.info(
                    f"Đã hoàn thành trang {page_num} với {len(articles)} bài viết"
                )
            else:
                self.logger.warning(f"Trang {page_num} không có dữ liệu, dừng crawl")
                break

            # Tăng số trang
            page_num += 1

            # Delay để tránh bị block
            time.sleep(2)

        # Lưu file tổng hợp
        if all_articles:
            self.save_all_data(all_articles)
            self.logger.info(
                f"Hoàn thành crawl! Tổng cộng {len(all_articles)} bài viết từ {page_num-1} trang"
            )
        else:
            self.logger.warning("Không có dữ liệu nào được crawl")

    def crawl_pages_range(self, start_page, end_page):
        """Crawl các trang trong khoảng từ start_page đến end_page"""
        all_articles = []

        # Kiểm tra input hợp lệ
        if start_page < 1 or end_page < start_page:
            self.logger.error(
                "Số trang không hợp lệ. start_page phải >= 1 và end_page >= start_page"
            )
            return

        self.logger.info(
            f"Bắt đầu crawl dữ liệu từ trang {start_page} đến trang {end_page}"
        )

        for page_num in range(start_page, end_page + 1):
            self.logger.info(f"Đang crawl trang {page_num}...")

            # Kiểm tra xem trang có tồn tại không
            if not self.check_page_exists(page_num):
                self.logger.warning(
                    f"Trang {page_num} không tồn tại hoặc không có dữ liệu, bỏ qua"
                )
                continue

            # Trích xuất dữ liệu từ trang
            articles = self.extract_data_from_page(page_num)

            if articles:
                # Lưu dữ liệu trang hiện tại
                self.save_page_data(articles, page_num)

                # Thêm vào danh sách tổng
                all_articles.extend(articles)

                self.logger.info(
                    f"Đã hoàn thành trang {page_num} với {len(articles)} bài viết"
                )
            else:
                self.logger.warning(f"Trang {page_num} không có dữ liệu")

            # Delay để tránh bị block
            time.sleep(2)

        # Lưu file tổng hợp
        if all_articles:
            self.save_all_data(all_articles)
            self.logger.info(
                f"Hoàn thành crawl! Tổng cộng {len(all_articles)} bài viết từ {end_page - start_page + 1} trang"
            )
        else:
            self.logger.warning("Không có dữ liệu nào được crawl")

    def close(self):
        """Đóng WebDriver"""
        if hasattr(self, "driver"):
            self.driver.quit()
            self.logger.info("Đã đóng WebDriver")


def get_user_input():
    """Lấy input từ người dùng để chọn chế độ crawl"""
    print("=== FPT Online Web Crawler ===")
    print("Chọn chế độ crawl:")
    print("1. Crawl tất cả trang (từ đầu đến cuối)")
    print("2. Crawl theo khoảng trang (chọn trang bắt đầu và kết thúc)")

    while True:
        try:
            choice = int(input("\nNhập lựa chọn (1 hoặc 2): "))
            if choice in [1, 2]:
                return choice
            else:
                print("Vui lòng nhập 1 hoặc 2")
        except ValueError:
            print("Vui lòng nhập số hợp lệ")


def get_page_range():
    """Lấy khoảng trang từ người dùng"""
    while True:
        try:
            start_page = int(input("Nhập trang bắt đầu: "))
            if start_page < 1:
                print("Trang bắt đầu phải >= 1")
                continue

            end_page = int(input("Nhập trang kết thúc: "))
            if end_page < start_page:
                print("Trang kết thúc phải >= trang bắt đầu")
                continue

            return start_page, end_page
        except ValueError:
            print("Vui lòng nhập số hợp lệ")


def main():
    crawler = FPTOnlineCrawler()

    try:
        choice = get_user_input()

        if choice == 1:
            print("\n🚀 Bắt đầu crawl tất cả trang...")
            crawler.crawl_all_pages()
        else:
            start_page, end_page = get_page_range()
            print(f"\n🚀 Bắt đầu crawl từ trang {start_page} đến trang {end_page}...")
            crawler.crawl_pages_range(start_page, end_page)

    except KeyboardInterrupt:
        crawler.logger.info("Crawl bị dừng bởi người dùng")
    except Exception as e:
        crawler.logger.error(f"Lỗi không mong đợi: {e}")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
