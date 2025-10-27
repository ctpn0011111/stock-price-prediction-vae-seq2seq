import os
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
)

# Tạo thư mục lưu file
output_dir = "../dataset/link/pvg/"
os.makedirs(output_dir, exist_ok=True)

URL = "https://www.genco3.com/tin-tuc/tin-nganh-dien.html"


def crawl_genco3(max_clicks=50):
    # Lấy chromedriver path từ biến môi trường
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if not chromedriver_path:
        raise EnvironmentError(
            "⚠️ Biến môi trường CHROMEDRIVER_PATH chưa được thiết lập"
        )

    # Cấu hình Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # bỏ nếu muốn nhìn trình duyệt
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(URL)
    wait = WebDriverWait(driver, 10)

    current_id = 0
    all_data = []
    seen_urls = set()

    for click_num in range(1, max_clicks + 1):
        try:
            # Chờ nút "Xem thêm" hiển thị
            btn = wait.until(EC.element_to_be_clickable((By.ID, "btnLoadMore")))
            driver.execute_script("arguments[0].click();", btn)  # click bằng JS
            time.sleep(2)  # chờ load
        except (
            TimeoutException,
            ElementClickInterceptedException,
            NoSuchElementException,
        ):
            print("⚠️ Không tìm thấy hoặc không click được nút Xem thêm.")
            break

        # Parse HTML sau khi click
        soup = BeautifulSoup(driver.page_source, "html.parser")
        posts = soup.find_all("div", class_="nw-card-item")

        for post in posts:
            card_content = post.find("div", class_="card-content")
            if card_content:
                p_tag = card_content.find("p")
                a_tag = p_tag.find("a") if p_tag else None
                if a_tag and a_tag.get("href"):
                    url = "https://www.genco3.com" + a_tag["href"]
                    if url not in seen_urls:  # tránh trùng lặp
                        seen_urls.add(url)
                        current_id += 1
                        all_data.append(
                            {
                                "id": current_id,
                                "title": a_tag.get_text(strip=True),
                                "url": url,
                                "ngay_crawl": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                            }
                        )

        print(f"👉 Đã crawl xong lần click {click_num}, tổng {len(all_data)} bài viết.")

    driver.quit()

    # Sau khi crawl xong mới lưu 1 file duy nhất
    output_file = os.path.join(output_dir, "genco3_data.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã lưu toàn bộ dữ liệu vào: {output_file}")


if __name__ == "__main__":
    crawl_genco3(max_clicks=100)
