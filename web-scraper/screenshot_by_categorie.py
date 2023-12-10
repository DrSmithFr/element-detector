import os
import time

import click
import selenium
from selenium import webdriver
from selenium.common import WebDriverException

from src.models.Resolution import Resolution

DESKTOP_RESOLUTIONS = [
    {
        'name': '720p',
        'height': 720,
        'width': 1280
    },
    {
        'name': '1440p',
        'height': 1440,
        'width': 2560
    },
    {
        'name': '4K',
        'height': 2160,
        'width': 3840
    },
]

MOBILE_RESOLUTIONS = [
    {
        'name': 'iPhone_SE',
        'width': 375,
        'height': 667,
    },
    {
        'name': 'iPhone_12',
        'width': 390,
        'height': 844,
    },
    {
        'name': 'iPhone_14',
        'width': 490,
        'height': 932,
    },
]


@click.command()
@click.option('--output-folder', default='dataset', help='Output folder')
@click.option('--fullscreen', default=False, is_flag=True, help='Take a fullscreen screenshot')
@click.option('--mobile', default=False, is_flag=True, help='Take a screenshot as mobile device')
@click.option('--skip-cookies', default=False, is_flag=True, help='Skip waiting for cookies')
def main(output_folder: str, fullscreen: bool, mobile: bool, skip_cookies: bool):
    """Script to take a screenshot of a URL using Selenium with Chrome."""

    if not skip_cookies:
        accept_cookies()

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # remove last / of output_folder
    if output_folder[-1] == '/':
        output_folder = output_folder[:-1]

    # Load the user profile to avoid cookie popups
    # (you need to accept the cookies manually the first time)
    # (you can use config/categories/homepage to find all websites)
    options = webdriver.ChromeOptions()
    options.add_argument('--user-data-dir=.google-chrome')
    options.add_argument('--profile-directory=Default')

    # Set Chrome as headless to avoid resolution issues
    options.add_argument('--headless')  # Run Chrome in headless mode (without a graphical interface)

    # Set the user agent to a mobile device
    if mobile:
        options.add_argument(
            'Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36'
        )

    # Initialize the Chrome driver
    print("Initializing Chrome driver...")
    driver = webdriver.Chrome(options=options)

    # read each file in the folder dataset/categories
    # for each file, take a screenshot of the urls in the file
    # save the screenshot in the folder dataset/{category_name}/
    try:
        for category in os.listdir('config/categories'):
            with open(os.path.join('config/categories', category), 'r') as f:
                for line in f:
                    url = line.strip()

                    # remove url query parameters
                    if '?' in url:
                        url = url.split('?')[0]

                    if mobile:
                        if not os.path.exists(f"{output_folder}/mobile"):
                            os.makedirs(f"{output_folder}/mobile")

                        take_screenshot(driver, url, f"{output_folder}/mobile/{category}", MOBILE_RESOLUTIONS,
                                        fullscreen)
                    else:
                        if not os.path.exists(f"{output_folder}/desktop"):
                            os.makedirs(f"{output_folder}/desktop")

                        take_screenshot(driver, url, f"{output_folder}/desktop/{category}", DESKTOP_RESOLUTIONS,
                                        fullscreen)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the browser
        driver.quit()


def take_screenshot(driver: webdriver.Chrome,
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
            driver.set_window_size(resolution['width'], resolution['height'] * 2)

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


def accept_cookies():
    # Load the user profile to avoid cookie popups
    # (you need to accept the cookies manually the first time)
    # (you can use config/categories/homepage to find all websites)
    options = webdriver.ChromeOptions()
    options.add_argument('--user-data-dir=.google-chrome')
    options.add_argument('--profile-directory=.google-profile')

    # Initialize the Chrome driver
    print("Initializing Chrome driver...")
    driver = webdriver.Chrome(options=options)

    print("Loading all domains of dataset...")
    domains = dict()
    for filename in os.listdir('config/categories'):
        with open(os.path.join('config/categories', filename), 'r') as f:
            for line in f:
                url = line.strip()
                domain = url.split('/')[2]
                domains[domain] = url

    print(f"Prepare accepting cookies for {len(domains)} domains...")

    for domain, url in domains.items():
        try:
            print(f"Accepting cookies for {domain}...")
            driver.get(url)

            # Wait for browser to be closed manually (cookies accepted)
            while is_browser_alive(driver):
                time.sleep(0.5)
        except selenium.common.exceptions.WebDriverException:
            print("Reloading Chrome driver...")
            driver.quit()
            driver = webdriver.Chrome(options=options)

        print(f"Accepted cookies for {domain}.")

    driver.quit()
    print("\n", "All cookies accepted.", "\n")


def is_browser_alive(driver) -> bool:
    try:
        # Try to interact with an element on the page
        driver.execute_script("return document.readyState")
        _ = driver.window_handles
        return True  # If successful, the browser is still open
    except WebDriverException:
        return False  # WebDriverException is raised if the browser is closed


if __name__ == '__main__':
    main()
