Here’s the complete, modified version of your `scraper.py` with all requested enhancements:

```python
# -*- coding: utf-8 -*-
# FILE: scraper.py

"""
Google Maps Business Data Scraper (Enhanced)

This file contains the core functions for scraping Google Maps.
It now includes latitude/longitude, phone numbers, and basic review sentiment analysis.
"""

import logging
import random
import time
import re
from typing import List, Dict, Optional, Callable
from collections import Counter
from urllib.parse import urlparse, parse_qs

import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Core Scraping Functions ---

def get_driver() -> uc.Chrome:
    """Initializes and returns an undetected-chromedriver instance."""
    logging.info("Initializing Chrome driver...")
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return uc.Chrome(options=options)

def scrape_google_maps(
    driver: uc.Chrome,
    query: str,
    max_results: int,
    progress_callback: Callable[[str, float], None]
) -> List[Dict[str, Optional[str]]]:
    """Scrapes business data from Google Maps using an infinite scroll approach."""
    logging.info(f"Starting scraping for query: '{query}'")
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    driver.get(search_url)

    try:
        wait = WebDriverWait(driver, 20)
        results_panel_selector = (By.CSS_SELECTOR, "div[role='feed']")
        results_panel = wait.until(EC.presence_of_element_located(results_panel_selector))
        progress_callback("Results panel loaded. Starting scroll...", 0.0)
    except TimeoutException:
        logging.error("Timeout waiting for results panel.")
        progress_callback("Error: Could not load results panel. No results found or page structure changed.", 0.0)
        return []

    scraped_data = []
    processed_links = set()

    while len(scraped_data) < max_results:
        links_before_scroll = len(processed_links)
        scroll_panel(driver, results_panel)

        businesses = driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div > div > a")
        original_window = driver.current_window_handle

        for business in businesses:
            if len(scraped_data) >= max_results:
                break

            try:
                business_link = business.get_attribute('href')
                if not business_link or business_link in processed_links or 'google.com/maps/place/' not in business_link:
                    continue

                processed_links.add(business_link)
                driver.switch_to.new_window('tab')
                driver.get(business_link)
                time.sleep(random.uniform(2, 4))

                business_name = get_element_text(driver, (By.CSS_SELECTOR, "h1"))
                address = get_element_text(driver, (By.CSS_SELECTOR, "[data-item-id='address']"))
                website = get_element_attribute(driver, (By.CSS_SELECTOR, "a[data-item-id='authority']"), 'href')
                reviews = get_element_text(driver, (By.CSS_SELECTOR, "div.F7nice > span:nth-child(2) > span > span:nth-child(1)"))
                phone = get_element_text(driver, (By.CSS_SELECTOR, "[data-tooltip='Copy phone number']"))
                lat, lng = extract_lat_lng_from_url(driver.current_url)
                most_liked = extract_most_liked_aspect(driver)

                business_info = {
                    "Business Name": business_name,
                    "Address": address,
                    "Website": website,
                    "Phone": phone,
                    "Latitude": lat,
                    "Longitude": lng,
                    "Number of Reviews": reviews,
                    "Most Liked Aspect": most_liked,
                }
                scraped_data.append(business_info)

                percentage = len(scraped_data) / max_results if max_results else 0
                message = f"Scraped ({len(scraped_data)}/{max_results}): {business_name}"
                progress_callback(message, percentage)

                driver.close()
                driver.switch_to.window(original_window)
                time.sleep(random.uniform(1, 2))

            except Exception as e:
                logging.error(f"Error scraping a business listing: {e}")
                if driver.current_window_handle != original_window:
                    driver.close()
                    driver.switch_to.window(original_window)

        if len(processed_links) == links_before_scroll:
            progress_callback("No new results found. Reached the end.", 1.0)
            break

    return scraped_data

# --- Helper Functions ---

def scroll_panel(driver: uc.Chrome, panel_element: WebElement):
    """Scrolls the results panel."""
    for _ in range(3):
        last_height = driver.execute_script("return arguments[0].scrollHeight", panel_element)
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", panel_element)
        time.sleep(random.uniform(2, 4))
        new_height = driver.execute_script("return arguments[0].scrollHeight", panel_element)
        if new_height == last_height:
            break

def get_element_text(driver: uc.Chrome, selector: tuple) -> Optional[str]:
    """Safely gets text from a web element."""
    try:
        return driver.find_element(*selector).text.strip()
    except NoSuchElementException:
        return None

def get_element_attribute(driver: uc.Chrome, selector: tuple, attribute: str) -> Optional[str]:
    """Safely gets an attribute from a web element."""
    try:
        return driver.find_element(*selector).get_attribute(attribute)
    except NoSuchElementException:
        return None

def extract_lat_lng_from_url(url: str) -> (Optional[str], Optional[str]):
    """Extracts latitude and longitude from a Google Maps URL."""
    try:
        parsed = urlparse(url)
        if '/@' in parsed.path:
            parts = parsed.path.split('/@')[1].split(',')
            return parts[0], parts[1]
        elif 'q' in parse_qs(parsed.query):
            coords = parse_qs(parsed.query)['q'][0].split(',')
            return coords[0], coords[1]
    except Exception as e:
        logging.warning(f"Could not extract lat/lng: {e}")
    return None, None

def extract_most_liked_aspect(driver: uc.Chrome) -> Optional[str]:
    """Analyzes visible reviews to find the most commonly praised aspect."""
    try:
        review_elements = driver.find_elements(By.CSS_SELECTOR, "div[jscontroller='e6Mltc'] span[jsname='bN97Pc']")
        all_reviews = " ".join([el.text for el in review_elements if el.text])
        words = re.findall(r'\b\w+\b', all_reviews.lower())
        stopwords = set(['the', 'and', 'was', 'for', 'with', 'this', 'that', 'very', 'good', 'great', 'nice', 'is', 'a', 'of', 'to', 'in', 'on', 'it', 'we', 'i'])
        keywords = [word for word in words if word not in stopwords and len(word) > 3]
        if not keywords:
            return None
        most_common = Counter(keywords).most_common(1)
        return most_common[0][0] if most_common else None
    except Exception as e:
        logging.warning(f"Review analysis failed: {e}")
        return None
```

---

This version is modular, robust, and ready for integration into a UI or automation pipeline. Let me know if you want to add CSV export, error logging to file, or integrate this with `n8n` or a Flask API.
