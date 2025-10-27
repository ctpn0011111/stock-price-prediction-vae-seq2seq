import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import uuid


class FPTNewsCrawler:
    def __init__(self):
        self.base_url = "https://fpt.com/vi/tin-tuc/page/"
        self.dataset_path = "../dataset/link/fpt/"
        self.setup_driver()
        self.ensure_directory_exists()

    def setup_driver(self):
        """Thiết lập Chrome driver với các options tối ưu cho Ubuntu"""
        chrome_options = Options()

        # Ubuntu optimized options
        chrome_options.add_argument("--headless")  # Chạy ẩn browser
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Tăng tốc load
        chrome_options.add_argument("--disable-javascript-harmony")
        chrome_options.add_argument("--window-size=1920,1080")

        # Ubuntu Chrome User-Agent
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        # Performance optimization
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(5)  # Implicit wait ngắn

    def ensure_directory_exists(self):
        """Tạo thư mục lưu trữ nếu chưa tồn tại"""
        if not os.path.exists(self.dataset_path):
            os.makedirs(self.dataset_path)

    def wait_for_content_load(self, timeout=15):
        """Đợi nội dung load hoàn toàn với nhiều chiến lược"""
        wait = WebDriverWait(self.driver, timeout)

        try:
            print("Đang đợi nội dung load...")

            # Strategy 1: Đợi elements news-card-meta xuất hiện
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "news-card-meta"))
            )
            print("✓ Tìm thấy elements news-card-meta")

            # Strategy 2: Đợi thêm để đảm bảo tất cả elements đã load
            time.sleep(2)

            # Strategy 3: Kiểm tra số lượng elements có tăng không
            initial_count = len(
                self.driver.find_elements(By.CLASS_NAME, "news-card-meta")
            )
            print(f"Số bài viết ban đầu: {initial_count}")

            # Đợi thêm 5s để xem có load thêm không
            time.sleep(5)
            final_count = len(
                self.driver.find_elements(By.CLASS_NAME, "news-card-meta")
            )
            print(f"Số bài viết sau 5s: {final_count}")

            # Nếu vẫn còn load thì đợi thêm
            if final_count > initial_count:
                print("Vẫn đang load thêm nội dung, đợi thêm 5s...")
                time.sleep(5)

            return True

        except TimeoutException:
            print(
                f"Timeout sau {timeout}s - Có thể trang không có nội dung hoặc load chậm"
            )
            return False

    def crawl_page(self, page_number):
        """Crawl một trang cụ thể với smart waiting"""
        url = f"{self.base_url}{page_number}"
        print(f"\n🔄 Đang crawl trang {page_number}: {url}")

        try:
            # Load trang web
            start_time = time.time()
            self.driver.get(url)

            # Đợi nội dung load với smart strategy
            if not self.wait_for_content_load(timeout=20):
                print(f"❌ Không thể load nội dung trang {page_number}")
                return []

            load_time = time.time() - start_time
            print(f"⏱️ Thời gian load: {load_time:.1f}s")

            # Lấy HTML sau khi đã load xong
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, "html.parser")

            # Tìm các thẻ div có class 'news-card-meta'
            news_cards = soup.find_all("div", class_="news-card-meta")

            if not news_cards:
                print(
                    f"❌ Không tìm thấy elements news-card-meta trên trang {page_number}"
                )
                # Debug: Lưu HTML để kiểm tra
                with open(f"debug_page_{page_number}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"🔍 Đã lưu HTML debug vào debug_page_{page_number}.html")
                return []

            page_data = []
            for i, card in enumerate(news_cards, 1):
                try:
                    # Tìm thẻ a con của div
                    link_tag = card.find("a")
                    if link_tag:
                        # Lấy href
                        href = link_tag.get("href", "")

                        # Lấy thẻ h2 con của a
                        h2_tag = link_tag.find("h2")
                        title = h2_tag.get_text(strip=True) if h2_tag else ""

                        if href and title:
                            # Tạo URL đầy đủ nếu href là relative
                            if href.startswith("/"):
                                full_url = f"https://fpt.com{href}"
                            elif href.startswith("http"):
                                full_url = href
                            else:
                                full_url = f"https://fpt.com/vi/{href}"

                            news_item = {
                                "id": str(uuid.uuid4()),
                                "title": title,
                                "url": full_url,
                                "ngay_crawl": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                            }
                            page_data.append(news_item)
                            print(f"  📰 {i}. {title[:60]}...")

                except Exception as e:
                    print(f"⚠️ Lỗi khi xử lý bài viết {i}: {str(e)}")
                    continue

            print(f"✅ Trang {page_number}: Tìm thấy {len(page_data)} bài viết")
            return page_data

        except Exception as e:
            print(f"❌ Lỗi khi crawl trang {page_number}: {str(e)}")
            return []

    def save_page_data(self, page_number, data):
        """Lưu dữ liệu của một trang vào file JSON"""
        if not data:
            print(f"⚠️ Không có dữ liệu để lưu cho trang {page_number}")
            return

        filename = f"page_{page_number}.json"
        filepath = os.path.join(self.dataset_path, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 Đã lưu dữ liệu trang {page_number} vào {filepath}")
        except Exception as e:
            print(f"❌ Lỗi khi lưu file trang {page_number}: {str(e)}")

    def crawl_multiple_pages(self, start_page, end_page):
        """Crawl nhiều trang từ start_page đến end_page"""
        print(f"🚀 Bắt đầu crawl từ trang {start_page} đến trang {end_page}")
        print(f"📁 Dữ liệu sẽ được lưu vào: {os.path.abspath(self.dataset_path)}")

        all_data = []
        successful_pages = 0

        for page_num in range(start_page, end_page + 1):
            print(f"\n{'='*50}")
            print(f"📄 TRANG {page_num}/{end_page}")
            print(f"{'='*50}")

            page_data = self.crawl_page(page_num)

            if page_data:
                # Lưu dữ liệu trang ngay sau khi crawl xong
                self.save_page_data(page_num, page_data)
                all_data.extend(page_data)
                successful_pages += 1

            # Nghỉ giữa các trang để tránh bị block
            if page_num < end_page:
                print("😴 Nghỉ 3 giây trước khi crawl trang tiếp theo...")
                time.sleep(3)

        # Lưu tổng hợp tất cả dữ liệu
        if all_data:
            summary_file = f"all_pages_{start_page}_to_{end_page}.json"
            summary_path = os.path.join(self.dataset_path, summary_file)

            try:
                with open(summary_path, "w", encoding="utf-8") as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                print(
                    f"\n🎉 Đã lưu tổng hợp {len(all_data)} bài viết vào {summary_path}"
                )
            except Exception as e:
                print(f"❌ Lỗi khi lưu file tổng hợp: {str(e)}")

        print(f"\n{'='*50}")
        print(f"📊 KẾT QUẢ CUỐI CÙNG")
        print(f"{'='*50}")
        print(f"✅ Trang thành công: {successful_pages}/{end_page - start_page + 1}")
        print(f"📰 Tổng bài viết: {len(all_data)}")
        print(f"📁 Thư mục lưu trữ: {os.path.abspath(self.dataset_path)}")

        return all_data

    def test_single_page(self, page_number=1):
        """Test crawl một trang để kiểm tra"""
        print(f"🧪 Test crawl trang {page_number}...")
        data = self.crawl_page(page_number)

        if data:
            print(f"\n📋 Preview {min(3, len(data))} bài viết đầu:")
            for i, item in enumerate(data[:3], 1):
                print(f"  {i}. {item['title']}")
                print(f"     🔗 {item['url']}")
                print(f"     🕐 {item['ngay_crawl']}")
                print()

        return data

    def close(self):
        """Đóng driver"""
        if hasattr(self, "driver"):
            self.driver.quit()
            print("🔒 Đã đóng browser")


def main():
    """Hàm main để chạy crawler"""
    crawler = FPTNewsCrawler()

    try:
        print("🎯 FPT NEWS CRAWLER")
        print("=" * 30)
        print("1. Test crawl trang 1")
        print("2. Crawl nhiều trang")
        choice = input("Chọn (1/2): ").strip()

        if choice == "1":
            result = crawler.test_single_page(1)
            if result:
                save_choice = input("\nLưu kết quả test? (y/n): ").strip().lower()
                if save_choice == "y":
                    crawler.save_page_data(1, result)
        else:
            # Nhập trang bắt đầu và trang kết thúc
            start_page = int(input("Nhập trang bắt đầu: "))
            end_page = int(input("Nhập trang kết thúc: "))

            if start_page > end_page:
                print("❌ Trang bắt đầu phải nhỏ hơn hoặc bằng trang kết thúc!")
                return

            # Xác nhận
            total_pages = end_page - start_page + 1
            estimated_time = total_pages * 15  # ~15s per page
            print(f"\n📊 Sẽ crawl {total_pages} trang")
            print(f"⏱️ Thời gian ước tính: ~{estimated_time//60}p{estimated_time%60}s")

            confirm = input("Tiếp tục? (y/n): ").strip().lower()
            if confirm != "y":
                print("🚫 Đã hủy")
                return

            # Bắt đầu crawl
            start_time = time.time()
            result = crawler.crawl_multiple_pages(start_page, end_page)
            end_time = time.time()

            print(
                f"\n⏱️ Tổng thời gian: {(end_time - start_time)//60:.0f}p{(end_time - start_time)%60:.0f}s"
            )

    except KeyboardInterrupt:
        print("\n🛑 Đã dừng crawl theo yêu cầu người dùng")
    except ValueError:
        print("❌ Vui lòng nhập số hợp lệ!")
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
