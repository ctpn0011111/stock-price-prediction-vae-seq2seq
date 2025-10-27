import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import os
from datetime import datetime
import time
import logging


class HPTCrawler:
    def __init__(self):
        self.base_url = "https://hpt.vn/newscate/27"
        self.output_dir = "../dataset/link/hpt"
        self.setup_logging()
        self.setup_driver()
        self.create_output_directory()

    def setup_logging(self):
        """Thiết lập logging để theo dõi quá trình crawl"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler("hpt_crawler.log"), logging.StreamHandler()],
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

    def extract_data_from_current_page(self, page_num):
        """Trích xuất dữ liệu từ trang hiện tại"""
        articles = []

        try:
            # Đợi trang load hoàn toàn
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.content"))
            )

            # Lấy HTML source và parse bằng BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Tìm tất cả div với class 'content'
            content_divs = soup.find_all("div", class_="content")

            for content_div in content_divs:
                try:
                    # Tìm thẻ a trong content div
                    a_tag = content_div.find("a")

                    if a_tag:
                        href = a_tag.get("href", "")

                        # Tìm thẻ h1 trong thẻ a
                        h1_tag = a_tag.find("h1")

                        if h1_tag:
                            title = h1_tag.get_text(strip=True)

                            # Xử lý URL tương đối
                            if href.startswith("/"):
                                full_url = f"https://hpt.vn{href}"
                            elif not href.startswith("http"):
                                full_url = f"https://hpt.vn/{href}"
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

        filename = f"hpt_page_{page_num}.json"
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

        filename = "hpt_all_articles.json"
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

    def click_next_page(self):
        """Click vào nút next để chuyển trang"""
        try:
            # Tìm thẻ a có class 'next fa fa-caret-right'
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "a.next.fa.fa-caret-right")
                )
            )

            # Click vào nút next
            self.driver.execute_script("arguments[0].click();", next_button)
            self.logger.info("Đã click vào nút Next để chuyển trang")

            # Đợi trang load
            time.sleep(3)
            return True

        except TimeoutException:
            self.logger.info("Không tìm thấy nút Next - có thể đã đến trang cuối")
            return False
        except Exception as e:
            self.logger.error(f"Lỗi khi click nút Next: {e}")
            return False

    def crawl_all_pages(self):
        """Crawl tất cả các trang bằng cách click Next"""
        page_num = 1
        all_articles = []

        self.logger.info("Bắt đầu crawl dữ liệu từ HPT")

        try:
            # Truy cập trang đầu tiên
            self.driver.get(self.base_url)
            self.logger.info(f"Đã truy cập trang đầu tiên: {self.base_url}")

            while True:
                self.logger.info(f"Đang crawl trang {page_num}...")

                # Trích xuất dữ liệu từ trang hiện tại
                articles = self.extract_data_from_current_page(page_num)

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

                # Thử click Next để chuyển sang trang tiếp theo
                if not self.click_next_page():
                    self.logger.info("Đã crawl hết tất cả các trang")
                    break

                # Tăng số trang
                page_num += 1

                # Delay để tránh bị block
                time.sleep(2)

            # Lưu file tổng hợp
            if all_articles:
                self.save_all_data(all_articles)
                self.logger.info(
                    f"Hoàn thành crawl! Tổng cộng {len(all_articles)} bài viết từ {page_num} trang"
                )
            else:
                self.logger.warning("Không có dữ liệu nào được crawl")

        except Exception as e:
            self.logger.error(f"Lỗi trong quá trình crawl: {e}")

    def crawl_pages_range(self, max_pages):
        """Crawl một số trang giới hạn"""
        page_num = 1
        all_articles = []

        self.logger.info(f"Bắt đầu crawl tối đa {max_pages} trang từ HPT")

        try:
            # Truy cập trang đầu tiên
            self.driver.get(self.base_url)
            self.logger.info(f"Đã truy cập trang đầu tiên: {self.base_url}")

            while page_num <= max_pages:
                self.logger.info(f"Đang crawl trang {page_num}/{max_pages}...")

                # Trích xuất dữ liệu từ trang hiện tại
                articles = self.extract_data_from_current_page(page_num)

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

                # Nếu chưa đến trang cuối cùng, thử click Next
                if page_num < max_pages:
                    if not self.click_next_page():
                        self.logger.info(
                            f"Không thể chuyển sang trang tiếp theo - dừng ở trang {page_num}"
                        )
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

        except Exception as e:
            self.logger.error(f"Lỗi trong quá trình crawl: {e}")

    def close(self):
        """Đóng WebDriver"""
        if hasattr(self, "driver"):
            self.driver.quit()
            self.logger.info("Đã đóng WebDriver")


def get_user_input():
    """Lấy input từ người dùng để chọn chế độ crawl"""
    print("=== HPT Web Crawler ===")
    print("Chọn chế độ crawl:")
    print("1. Crawl tất cả trang (click Next đến hết)")
    print("2. Crawl số trang giới hạn")

    while True:
        try:
            choice = int(input("\nNhập lựa chọn (1 hoặc 2): "))
            if choice in [1, 2]:
                return choice
            else:
                print("Vui lòng nhập 1 hoặc 2")
        except ValueError:
            print("Vui lòng nhập số hợp lệ")


def get_max_pages():
    """Lấy số trang tối đa từ người dùng"""
    while True:
        try:
            max_pages = int(input("Nhập số trang tối đa muốn crawl: "))
            if max_pages > 0:
                return max_pages
            else:
                print("Số trang phải > 0")
        except ValueError:
            print("Vui lòng nhập số hợp lệ")


def main():
    crawler = HPTCrawler()

    try:
        choice = get_user_input()

        if choice == 1:
            print("\n🚀 Bắt đầu crawl tất cả trang...")
            crawler.crawl_all_pages()
        else:
            max_pages = get_max_pages()
            print(f"\n🚀 Bắt đầu crawl tối đa {max_pages} trang...")
            crawler.crawl_pages_range(max_pages)

    except KeyboardInterrupt:
        crawler.logger.info("Crawl bị dừng bởi người dùng")
    except Exception as e:
        crawler.logger.error(f"Lỗi không mong đợi: {e}")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
