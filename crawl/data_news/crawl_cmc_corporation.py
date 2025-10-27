import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


# =========================
# Setup Selenium
# =========================
def init_driver():
    chrome_path = os.getenv(
        "CHROMEDRIVER_PATH", "chromedriver"
    )  # lấy path từ biến môi trường
    options = Options()
    options.add_argument("--headless")  # chạy ẩn
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(chrome_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def get_session_cookies(driver, url="https://www.cmc.com.vn/language/vi"):
    driver.get(url)
    time.sleep(2)  # chờ load trang và set ngôn ngữ
    cookies = driver.get_cookies()
    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie["name"], cookie["value"])
    return s


# =========================
# Crawl Article
# =========================
def crawl_article(session, url):
    try:
        r = session.get(url, timeout=20)
        r.encoding = "utf-8"
        if r.status_code != 200:
            print(f"❌ Lỗi HTTP {r.status_code} - {url}")
            return None
    except Exception as e:
        print(f"❌ Request lỗi {url}: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # --- Tiêu đề ---
    title_tag = soup.find("h2", class_="content__article__title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # --- Ngày đăng ---
    time_tag = soup.find("time", class_="content__article__time")
    ngay_dang = time_tag.get_text(strip=True) if time_tag else ""

    # --- Content ---
    parts = []

    # Phần 1: div.short
    short_div = soup.find("div", class_="content__article__short font-weight-bold")
    if short_div:
        parts.append(short_div.get_text(" ", strip=True))

    # Phần 2: toàn bộ text trong div.data
    data_div = soup.find("div", class_="content__article__data")
    if data_div:
        # Lấy tất cả text (bao gồm p, span, h2, h4, ...)
        text = data_div.get_text(" ", strip=True)
        if text:
            parts.append(text)

    content = "\n".join(parts)

    return title, ngay_dang, content


# =========================
# Main process
# =========================
def process_files():
    input_dir = "../../dataset/link/cmc_corporation/"
    output_dir = "../../dataset/data/cmc_corporation/"
    os.makedirs(output_dir, exist_ok=True)

    driver = init_driver()
    session = get_session_cookies(driver)
    driver.quit()

    for file in sorted(os.listdir(input_dir)):
        if not file.endswith(".json"):
            continue

        input_file = os.path.join(input_dir, file)
        with open(input_file, "r", encoding="utf-8") as f:
            try:
                articles = json.load(f)
            except Exception as e:
                print(f"❌ Lỗi đọc {input_file}: {e}")
                continue

        output_data = []
        for art in articles:
            url = art.get("url")
            aid = art.get("id")
            print(f"[{file}] Crawling: {url}")

            result = crawl_article(session, url)
            if result:
                title, ngay_dang, content = result
                output_data.append(
                    {
                        "id": aid,
                        "title": title,
                        "url": url,
                        "content": content,
                        "ngay_dang": ngay_dang,
                        "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            else:
                output_data.append(
                    {
                        "id": aid,
                        "title": "",
                        "url": url,
                        "content": "",
                        "ngay_dang": "",
                        "ngay_crawl": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

        # Xuất file json output
        output_file = os.path.join(output_dir, f"data_{file}")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"✅ Đã lưu {output_file}")


if __name__ == "__main__":
    process_files()
