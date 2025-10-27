from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime

# Đường dẫn lưu file
SAVE_DIR = "../../dataset/link/vgi/"
os.makedirs(SAVE_DIR, exist_ok=True)

# Khởi tạo Selenium (Chrome headless)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # chạy ngầm
driver = webdriver.Chrome(options=options)

driver.get("https://viettelglobal.com.vn/tin-tuc-vtg")


def crawl_current_page(page_id):
    """Crawl dữ liệu hiện tại và lưu ra file"""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.find_all("h3", class_="dz-title")

    data = []
    for idx, item in enumerate(items, start=1):
        a_tag = item.find("a")
        if a_tag:
            url = a_tag.get("href")
            title = a_tag.get("title")
            data.append(
                {
                    "id": idx,
                    "title": title,
                    "url": url,
                    "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    # Lưu dữ liệu ra file JSON
    filename = os.path.join(SAVE_DIR, f"page_{page_id}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ Đã lưu dữ liệu lần {page_id} → {filename}")


if __name__ == "__main__":
    for i in range(1, 51):  # click 50 lần
        try:
            # Crawl dữ liệu hiện tại
            crawl_current_page(i)

            # Tìm button load_more_
            element = driver.find_element(By.CSS_SELECTOR, "button#load_more_")

            # Cuộn vào giữa màn hình cho chắc
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            time.sleep(1)  # chờ cuộn

            # Click button
            element.click()
            print(f"✅ Đã click 'XEM THÊM' lần {i}")

            # Đợi dữ liệu mới load
            time.sleep(2)

        except Exception as e:
            print(f"❌ Lỗi ở lần click {i}: {e}")
            break

    driver.quit()
