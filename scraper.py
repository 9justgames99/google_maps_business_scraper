# -*- coding: utf-8 -*-
# FILE: scraper.py

"""
Google Maps Business Data Scraper (Backend Logic)

This file contains the core functions for scraping Google Maps.
It's designed to be imported and used by a user interface, like app.py.
"""
import logging
import random
import time
from typing import List, Dict, Optional, Callable

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
    options.add_argument('--headless') # Run in headless mode for server/UI use
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
    """
    Scrapes business data from Google Maps using an infinite scroll approach.

    Args:
        driver: An instance of undetected-chromedriver.
        query: The search query.
        max_results: The maximum number of results to scrape.
        progress_callback: A function to call with progress updates (message, percentage).
    """
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

                business_info = {
                    "Business Name": business_name,
                    "Address": address,
                    "Website": website,
                    "Number of Reviews": reviews,
                }
                scraped_data.append(business_info)
                
                # *** Report progress back to the UI ***
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


def scroll_panel(driver: uc.Chrome, panel_element: WebElement):
    """Scrolls the results panel."""
    for _ in range(3): # Scroll a few times to ensure content loads
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