import math
import os
import time

import click
import selenium
from PIL import Image
from selenium import webdriver
from selenium.common import WebDriverException

from src.models.Resolution import Resolution

MOBILE_RESOLUTIONS = [
    Resolution(name='iPhone SE', width=375, height=667),
]

CHUNK_SIZE_PX = 200
DEAD_ZONE_PX = 200


@click.command()
@click.argument('url', type=str, required=True)
@click.option('--skip', default=False, is_flag=True)
@click.option('--pages', default=2, type=int, help="Number of pages to screenshot")
def main(url: str, skip: bool, pages: int):
    """Script to take a screenshot of a URL using Selenium with Chrome."""

    # find the resolution of the device
    resolution = MOBILE_RESOLUTIONS[0]

    # Load the user profile to avoid cookie popups
    # (you need to accept the cookies manually the first time)
    # (you can use config/categories/homepage to find all websites)
    options = webdriver.ChromeOptions()
    options.add_argument('--user-data-dir=.google-chrome')
    options.add_argument('--profile-directory=.google-profile')
    options.add_experimental_option('mobileEmulation', {'deviceName': resolution['name']})  # Emulate a mobile device

    # Set Chrome as headless to avoid resolution issues
    # options.add_argument('--headless')  # Run Chrome in headless mode (without a graphical interface)

    # Initialize the Chrome driver
    print("Initializing Chrome driver...")
    driver = webdriver.Chrome(options=options)

    # read each file in the folder dataset/categories
    # for each file, take a screenshot of the urls in the file
    # save the screenshot in the folder dataset/{category_name}/
    try:
        take_screenshot(driver, url, skip, pages)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the browser
        driver.quit()


def resize_screenshot(input_file: str, resolution: Resolution):
    im = Image.open(input_file)
    im = im.resize((resolution['width'], resolution['height']), Image.ADAPTIVE)
    im.save(input_file)


def take_screenshot(driver: webdriver.Chrome,
                    url: str,
                    skip: bool,
                    pages: int = 2):
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

    # Create the output folder if it does not exist
    output_folder = f"var/{url_slug}"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Take the full size screenshot
    print(f"Taking screenshot ...")

    # get width and height of the browser window
    width = driver.execute_script("return window.innerWidth;")
    height = driver.execute_script("return window.innerHeight;")

    # let user close every popup manually
    if not skip:
        input("Press Enter to continue...")

    # Take first page screenshot
    if pages == 1:
        output = f"{output_folder}/screenshot.png"
        driver.save_screenshot(output)
        return 0
    else:
        driver.save_screenshot(f"{output_folder}/page_0.png")

    nb_chunks_by_page = math.ceil(height / CHUNK_SIZE_PX)
    nb_screenshots = nb_chunks_by_page * pages
    pixel_ratio = get_pixel_ratio(driver)

    screenshot_parts = []

    scroll = DEAD_ZONE_PX * pixel_ratio

    # Take a screenshot of each chunk of the page
    for i in range(nb_screenshots):
        print(f"Taking screenshot {i + 1} of {nb_screenshots} ...")
        driver.execute_script(f"window.scrollTo(0, {scroll});")

        scroll += CHUNK_SIZE_PX
        time.sleep(1)

        output = f"{output_folder}/part_{i}.png"
        driver.save_screenshot(output)

        if not os.path.exists(output):
            print(f"Screenshot {output} was not taken!")
            raise Exception(f"Screenshot {output} not taken!")
        else:
            print(f"Screenshot successfully saved to {output}")

    # Chunking screenshot
    print(f"Chunking screenshot ...")

    for i in range(nb_screenshots):
        output = f"{output_folder}/part_{i}_chunk.png"
        crop_chunk(
            f"{output_folder}/part_{i}.png",
            output,
            CHUNK_SIZE_PX * pixel_ratio,
            DEAD_ZONE_PX * pixel_ratio
        )
        screenshot_parts.append(output)

    # Gluing screenshot
    print(f"Gluing screenshot ...")

    screenshot_size = (
        width * pixel_ratio,
        height * pixel_ratio * (pages + 1)
    )

    screenshot = Image.new('RGB', screenshot_size)

    for i in range(-1, nb_screenshots):
        if i == -1:
            screenshot.paste(
                Image.open(f"{output_folder}/page_0.png"),
                (0, 0)
            )
        else:
            page_height = height * pixel_ratio
            chunk_height = CHUNK_SIZE_PX * pixel_ratio

            screenshot.paste(
                Image.open(screenshot_parts[i]),
                (0, page_height + (i * chunk_height))
            )

    output = f"{output_folder}/screenshot.png"

    screenshot.save(output)
    print(f"Screenshot successfully saved to {output}")


def crop_chunk(image_path: str,
               output_path: str,
               chunk_size_px: int,
               dead_zone_px: int):
    # Open the image
    original_image = Image.open(image_path)

    # Get the dimensions of the original image
    width, height = original_image.size

    # Set the crop box to keep the bottom 100 pixels
    crop_box = (
        0,
        height - (chunk_size_px + dead_zone_px),
        width,
        height - dead_zone_px
    )

    # Crop the image
    cropped_image = original_image.crop(crop_box)

    # Save the cropped image
    cropped_image.save(output_path)


def get_pixel_ratio(driver):
    pixel_ratio_script = "return window.devicePixelRatio || 1;"
    pixel_ratio = driver.execute_script(pixel_ratio_script)
    return pixel_ratio


if __name__ == '__main__':
    main()
