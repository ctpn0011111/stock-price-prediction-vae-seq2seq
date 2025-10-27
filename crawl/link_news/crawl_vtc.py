import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import os
from datetime import datetime
import time
import logging
import random


class VTCCrawler:
    def __init__(self):
        self.base_url = "https://vtconline.vn/news/394?page="
        self.domain = "https://vtconline.vn"
        self.output_dir = "../dataset/link/vtc"
        self.setup_logging()
        self.driver = None
        self.create_output_directory()
        self.max_retries = 3
        self.restart_interval = 15  # Restart driver every 15 pages

    def setup_logging(self):
        """Thiết lập logging để theo dõi quá trình crawl"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler("vtc_crawler.log"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Thiết lập Selenium WebDriver với cấu hình tối ưu"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        # Thêm prefs để tối ưu hóa
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.media_stream": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        try:
            if self.driver:
                self.driver.quit()

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.logger.info("WebDriver đã được khởi tạo thành công")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khởi tạo WebDriver: {e}")
            return False

    def restart_driver(self):
        """Khởi động lại WebDriver để tránh memory leak"""
        self.logger.info("Đang khởi động lại WebDriver...")
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        return self.setup_driver()

    def create_output_directory(self):
        """Tạo thư mục lưu trữ nếu chưa tồn tại"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Đã tạo thư mục: {self.output_dir}")

    def safe_get_page(self, url, retries=0):
        """Truy cập trang web một cách an toàn với retry logic"""
        if retries >= self.max_retries:
            self.logger.error(
                f"Đã thử {self.max_retries} lần, không thể truy cập {url}"
            )
            return False

        try:
            if not self.driver:
                if not self.setup_driver():
                    return False

            self.driver.get(url)

            # Đợi trang load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Đợi thêm một chút để đảm bảo content được load
            time.sleep(2)
            return True

        except TimeoutException:
            self.logger.warning(
                f"Timeout khi tải trang {url}, thử lại... (lần {retries + 1})"
            )
            time.sleep(random.uniform(3, 7))
            return self.safe_get_page(url, retries + 1)

        except WebDriverException as e:
            self.logger.error(f"Lỗi WebDriver: {e}")
            if "chrome not reachable" in str(e).lower() or "session" in str(e).lower():
                self.logger.info("Khởi động lại WebDriver do lỗi session...")
                if self.restart_driver():
                    return self.safe_get_page(url, retries + 1)
            return False

        except Exception as e:
            self.logger.error(f"Lỗi không xác định: {e}")
            time.sleep(random.uniform(2, 5))
            return self.safe_get_page(url, retries + 1)

    def check_page_exists(self, page_num):
        """Kiểm tra xem trang có tồn tại và có dữ liệu hay không"""
        url = f"{self.base_url}{page_num}"

        if not self.safe_get_page(url):
            return False

        try:
            # Kiểm tra xem có các link bài viết không
            # Tìm các thẻ <a> có href bắt đầu bằng "/news/394/"
            links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href^="/news/394/"]')

            if links and len(links) > 0:
                self.logger.info(f"Trang {page_num} có {len(links)} bài viết")
                return True
            else:
                self.logger.warning(
                    f"Trang {page_num} không có bài viết hoặc đã hết dữ liệu"
                )
                return False

        except Exception as e:
            self.logger.error(f"Lỗi khi kiểm tra trang {page_num}: {e}")
            return False

    def extract_data_from_page(self, page_num):
        """Trích xuất dữ liệu từ một trang"""
        url = f"{self.base_url}{page_num}"
        articles = []

        if not self.safe_get_page(url):
            return articles

        try:
            # Đợi các elements load
            time.sleep(3)

            # Lấy HTML source và parse bằng BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Tìm tất cả thẻ <a> có href bắt đầu bằng "/news/394/"
            article_links = soup.find_all(
                "a", href=lambda href: href and href.startswith("/news/394/")
            )

            self.logger.info(
                f"Tìm thấy {len(article_links)} link bài viết trên trang {page_num}"
            )

            processed_urls = set()  # Để tránh trùng lặp

            for link in article_links:
                try:
                    href = link.get("href", "")
                    if not href:
                        continue

                    # Tạo URL hoàn chỉnh
                    if href.startswith("/"):
                        full_url = f"{self.domain}{href}"
                    else:
                        full_url = href

                    # Tránh trùng lặp URL
                    if full_url in processed_urls:
                        continue
                    processed_urls.add(full_url)

                    # Tìm title trong div có class 'h-[70px] line-clamp-2'
                    title = ""

                    # Tìm div cha chứa link này
                    parent_div = link.find_parent()
                    while parent_div:
                        title_div = parent_div.find(
                            "div", class_="h-[70px] line-clamp-2"
                        )
                        if title_div:
                            # Tìm thẻ p với class 'uppercase text-[20px] font-bold py-3'
                            title_p = title_div.find(
                                "p", class_="uppercase text-[20px] font-bold py-3"
                            )
                            if title_p:
                                title = title_p.get_text(strip=True)
                                break
                        parent_div = parent_div.find_parent()

                    # Nếu không tìm thấy title từ cách trên, thử tìm theo cách khác
                    if not title:
                        # Tìm trong toàn bộ trang các div có class 'h-[70px] line-clamp-2'
                        title_divs = soup.find_all(
                            "div", class_="h-[70px] line-clamp-2"
                        )
                        for title_div in title_divs:
                            title_p = title_div.find(
                                "p", class_="uppercase text-[20px] font-bold py-3"
                            )
                            if title_p:
                                # Kiểm tra xem div này có liên quan đến link không (cách đơn giản)
                                title_text = title_p.get_text(strip=True)
                                if title_text and len(title_text) > 10:  # Title hợp lệ
                                    title = title_text
                                    break

                    # Nếu vẫn không có title, dùng text của chính link đó
                    if not title:
                        title = link.get_text(strip=True)

                    # Bỏ qua nếu không có title hoặc title quá ngắn
                    if not title or len(title) < 5:
                        continue

                    article = {"title": title, "url": full_url}
                    articles.append(article)

                except Exception as e:
                    self.logger.warning(
                        f"Lỗi khi xử lý một bài viết trên trang {page_num}: {e}"
                    )
                    continue

            # Loại bỏ các bài viết trùng lặp dựa trên URL
            unique_articles = []
            seen_urls = set()
            for article in articles:
                if article["url"] not in seen_urls:
                    unique_articles.append(article)
                    seen_urls.add(article["url"])

            self.logger.info(
                f"Đã trích xuất {len(unique_articles)} bài viết unique từ trang {page_num}"
            )
            return unique_articles

        except Exception as e:
            self.logger.error(f"Lỗi khi trích xuất dữ liệu từ trang {page_num}: {e}")
            return []

    def save_page_data(self, articles, page_num):
        """Lưu dữ liệu của một trang vào file JSON"""
        if not articles:
            self.logger.warning(f"Không có dữ liệu để lưu cho trang {page_num}")
            return

        filename = f"vtc_page_{page_num}.json"
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

        filename = "vtc_all_articles.json"
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

        # Khởi tạo driver
        if not self.setup_driver():
            self.logger.error("Không thể khởi tạo WebDriver")
            return

        for page_num in range(start_page, end_page + 1):
            self.logger.info(f"Đang crawl trang {page_num}...")

            # Khởi động lại driver định kỳ
            if (
                page_num - start_page
            ) % self.restart_interval == 0 and page_num != start_page:
                self.logger.info(
                    f"Khởi động lại driver sau {self.restart_interval} trang..."
                )
                if not self.restart_driver():
                    self.logger.error("Không thể khởi động lại driver")
                    break

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

            # Random delay để tránh bị block
            time.sleep(random.uniform(3, 6))

        # Lưu file tổng hợp
        if all_articles:
            self.save_all_data(all_articles)
            self.logger.info(
                f"Hoàn thành crawl! Tổng cộng {len(all_articles)} bài viết từ {end_page - start_page + 1} trang"
            )
        else:
            self.logger.warning("Không có dữ liệu nào được crawl")

    def crawl_all_pages(self):
        """Crawl tất cả các trang từ đầu đến cuối"""
        page_num = 1
        all_articles = []
        consecutive_failures = 0
        max_consecutive_failures = 5

        self.logger.info("Bắt đầu crawl dữ liệu từ VTC Online")

        # Khởi tạo driver
        if not self.setup_driver():
            self.logger.error("Không thể khởi tạo WebDriver")
            return

        while True:
            self.logger.info(f"Đang crawl trang {page_num}...")

            # Khởi động lại driver mỗi X trang để tránh memory leak
            if page_num % self.restart_interval == 0:
                self.logger.info(
                    f"Khởi động lại driver sau {self.restart_interval} trang..."
                )
                if not self.restart_driver():
                    self.logger.error("Không thể khởi động lại driver")
                    break

            # Kiểm tra xem trang có tồn tại không
            if not self.check_page_exists(page_num):
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    self.logger.info(
                        f"Đã crawl xong. {consecutive_failures} trang liên tiếp không có dữ liệu."
                    )
                    break
                else:
                    self.logger.warning(
                        f"Trang {page_num} không có dữ liệu, thử trang tiếp theo..."
                    )
                    page_num += 1
                    continue

            # Reset counter khi tìm thấy trang có dữ liệu
            consecutive_failures = 0

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

            # Tăng số trang
            page_num += 1

            # Random delay để tránh bị block
            time.sleep(random.uniform(3, 6))

        # Lưu file tổng hợp
        if all_articles:
            self.save_all_data(all_articles)
            self.logger.info(
                f"Hoàn thành crawl! Tổng cộng {len(all_articles)} bài viết từ {page_num-1} trang"
            )
        else:
            self.logger.warning("Không có dữ liệu nào được crawl")

    def close(self):
        """Đóng WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Đã đóng WebDriver")
            except:
                pass


def get_user_input():
    """Lấy input từ người dùng để chọn chế độ crawl"""
    print("=== VTC Online Web Crawler ===")
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
    crawler = VTCCrawler()

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
