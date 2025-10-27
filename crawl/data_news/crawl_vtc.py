import json
import os
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import logging
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("crawler.log"), logging.StreamHandler()],
)


class VTCCrawler:
    def __init__(self, input_dir, output_dir, delay=1):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.delay = delay
        self.session = requests.Session()

        # Set headers to mimic a real browser
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def load_json_files(self):
        """Load all JSON files from input directory"""
        json_files = []
        for filename in os.listdir(self.input_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.input_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Handle both single object and array of objects
                        if isinstance(data, list):
                            json_files.extend(data)
                        else:
                            json_files.append(data)
                except Exception as e:
                    logging.error(f"Error loading {filename}: {str(e)}")
        return json_files

    def extract_content(self, soup):
        """Extract content from HTML using specified selectors"""
        result = {"title": "", "publish_date": "", "content": ""}

        try:
            # Extract title from div with class 'detailNews__left--title subTitle-l'
            title_div = soup.find("div", class_="detailNews__left--title subTitle-l")
            if title_div:
                result["title"] = title_div.get_text(strip=True)

            # Extract publish date from div with class 'flex items-center' -> p with class 'ml-2'
            flex_div = soup.find("div", class_="flex items-center")
            if flex_div:
                date_p = flex_div.find("p", class_="ml-2")
                if date_p:
                    result["publish_date"] = date_p.get_text(strip=True)

            # Extract content from div with class 'contentDiv mt-4' -> all child p tags
            content_div = soup.find("div", class_="contentDiv mt-4")
            if content_div:
                # Get all direct child p tags
                p_tags = content_div.find_all("p", recursive=False)
                if p_tags:
                    content_parts = []
                    for p in p_tags:
                        text = p.get_text(strip=True)
                        if text and text != "&nbsp;":  # Skip empty paragraphs
                            content_parts.append(text)
                    result["content"] = "\n\n".join(content_parts)
                else:
                    # If no direct child p tags, get all p tags within the div
                    all_p_tags = content_div.find_all("p")
                    content_parts = []
                    for p in all_p_tags:
                        text = p.get_text(strip=True)
                        if text and text != "&nbsp;":
                            content_parts.append(text)
                    result["content"] = "\n\n".join(content_parts)

        except Exception as e:
            logging.error(f"Error extracting content: {str(e)}")

        return result

    def crawl_url(self, url, max_retries=3):
        """Crawl a single URL with retry mechanism"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, "html.parser")
                return self.extract_content(soup)

            except requests.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(self.delay * (attempt + 1))  # Exponential backoff
                else:
                    logging.error(f"Failed to crawl {url} after {max_retries} attempts")
                    return None
            except Exception as e:
                logging.error(f"Unexpected error crawling {url}: {str(e)}")
                return None

    def process_data(self):
        """Process all JSON files and crawl URLs"""
        # Load all JSON data
        json_data = self.load_json_files()
        logging.info(f"Loaded {len(json_data)} items to crawl")

        crawled_data = []
        successful_crawls = 0
        failed_crawls = 0

        for i, item in enumerate(json_data, 1):
            logging.info(
                f"Processing item {i}/{len(json_data)}: {item.get('url', 'No URL')}"
            )

            # Get current timestamp
            crawl_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Crawl the URL
            # Enable debug for first URL to analyze structure
            debug_mode = i == 1
            content_data = self.crawl_url(item["url"], debug=debug_mode)

            if content_data:
                # Create result object
                result = {
                    "id": item["id"],
                    "title": content_data["title"]
                    or item.get("title", ""),  # Fallback to original title
                    "url": item["url"],
                    "content": content_data["content"],
                    "publish_date": content_data["publish_date"],
                    "crawl_date": crawl_date,
                }
                crawled_data.append(result)
                successful_crawls += 1
                logging.info(f"Successfully crawled: {item['url']}")
            else:
                # Add failed item with empty content
                result = {
                    "id": item["id"],
                    "title": item.get("title", ""),
                    "url": item["url"],
                    "content": "",
                    "publish_date": "",
                    "crawl_date": crawl_date,
                }
                crawled_data.append(result)
                failed_crawls += 1
                logging.error(f"Failed to crawl: {item['url']}")

            # Add delay between requests
            if i < len(json_data):
                time.sleep(self.delay)

        logging.info(
            f"Crawling completed. Success: {successful_crawls}, Failed: {failed_crawls}"
        )
        return crawled_data

    def save_results(self, data, filename="crawled_data.json"):
        """Save crawled data to JSON file"""
        output_path = os.path.join(self.output_dir, filename)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"Results saved to: {output_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving results: {str(e)}")
            return False


def main():
    # Configuration
    input_dir = "../../dataset/link/vtc/"
    output_dir = "../../dataset/data/vtc/"

    # Initialize crawler
    crawler = VTCCrawler(input_dir, output_dir, delay=1)

    try:
        # Process all data
        crawled_data = crawler.process_data()

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vtc_crawled_data_{timestamp}.json"

        if crawler.save_results(crawled_data, filename):
            logging.info(f"Crawling process completed successfully!")
            logging.info(f"Total items processed: {len(crawled_data)}")
        else:
            logging.error("Failed to save results")

    except KeyboardInterrupt:
        logging.info("Crawling process interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
