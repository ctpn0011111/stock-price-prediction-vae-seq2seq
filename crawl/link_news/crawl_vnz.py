import time
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Setup Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")  # chạy ẩn
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=chrome_options
)
driver.get("https://vng.com.vn/news/list.1.html")
time.sleep(3)

# Thư mục lưu file
output_dir = "../../dataset/link/vnz"
os.makedirs(output_dir, exist_ok=True)

crawl_times = 150
for crawl_round in range(1, crawl_times + 1):
    try:
        # Scroll xuống và click "Xem thêm"
        see_more = driver.find_element(By.CSS_SELECTOR, "a.btn-bordergray.seemore")
        ActionChains(driver).move_to_element(see_more).perform()
        time.sleep(1)
        see_more.click()
        time.sleep(3)  # chờ load nội dung mới
    except Exception as e:
        print("Không tìm thấy nút 'Xem thêm' nữa!", e)
        break

    # Sau khi click thì lấy dữ liệu mới load thêm
    soup = BeautifulSoup(driver.page_source, "html.parser")
    news_items = soup.find_all("a", class_="news-item")

    # Chỉ lấy phần tin mới xuất hiện ở lần này:
    # Giả sử mỗi lần click sẽ load thêm 10 tin (tuỳ site),
    # nên ta lấy "phần cuối" của news_items tương ứng
    new_items = news_items[-10:]  # điều chỉnh nếu số lượng mỗi lần khác

    data = []
    for idx, item in enumerate(new_items, start=1):
        url = item.get("href")
        title_tag = item.find("div", class_="news-des").find("h5", class_="bold")
        title = title_tag.get_text(strip=True) if title_tag else None

        data.append(
            {
                "id": idx,
                "title": title,
                "url": "https://vng.com.vn/news/" + url,
                "date_crawled": datetime.now().strftime("%Y-%m-%d"),
            }
        )

    # Xuất file json riêng cho vòng này
    output_file = os.path.join(output_dir, f"vnz_links_round_{crawl_round}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Đã lưu file: {output_file}")

driver.quit()
