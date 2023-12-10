import os
import time

import selenium
from selenium import webdriver
from selenium.common import WebDriverException

from src.models.Resolution import Resolution


def take_screenshots(driver: webdriver.Chrome,
                    url: str,
                    output_folder: str,
                    resolution: list[Resolution],
                    fullscreen: bool = False):
    """Take a screenshot of the specified URL using the specified driver."""

    # Create a slug from the URL to use as a filename
    url_slug = (url
                .replace("https://", "")
                .replace("http://", "")
                .replace("/", "_"))

    # Load the specified URL
    try:
        print(f"Loading URL {url}...")
        driver.set_page_load_timeout(20)
        driver.get(url)
    except selenium.common.exceptions.TimeoutException:
        print(f"TimeoutException for URL {url}...")
        return

    # Wait for the page to load
    time.sleep(3)

    for resolution in resolution:
        # Take the full size screenshot
        print(f"Taking screenshot {resolution['width']}x{resolution['height']}...")

        if fullscreen:
            height = driver.execute_script('return document.documentElement.scrollHeight')
            width = driver.execute_script('return document.documentElement.scrollWidth')
            driver.set_window_size(width, height * 2)  # the trick
        else:
            driver.set_window_size(resolution['width'], resolution['height'])

        time.sleep(3)
        output = f"{output_folder}/{url_slug}-{resolution['width']}x{resolution['height']}-{resolution['name']}.png"

        # check if folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # remove the file if it already exists
        if os.path.exists(output):
            os.remove(output)

        driver.save_screenshot(output)
        print(f"Screenshot successfully saved to {output}")

        # check if file exists
        if not os.path.exists(output):
            print(f"Screenshot {output} does not exist!")
            raise Exception(f"Screenshot {output} does not exist!")
