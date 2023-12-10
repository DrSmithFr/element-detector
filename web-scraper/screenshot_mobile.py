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

CHUNK_SIZE_PX = 300
DEAD_ZONE_PX = 100


@click.command()
@click.argument('url', type=str, required=True)
@click.option('--skip', default=False, is_flag=True)
def main(url: str, skip: bool):
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
        take_screenshot(driver, url, skip)
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
                    skip: bool):
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
    time.sleep(1)

    # Create the output folder if it does not exist
    output_folder = f"var/{url_slug}"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Take the full size screenshot
    print(f"Taking screenshot ...")

    # get width and height of the browser window
    screen = {
        "width": driver.execute_script("return screen.width;"),
        "height": driver.execute_script("return screen.height;"),
        "pixel_ratio": get_pixel_ratio(driver)
    }
    print(" > Screen:", screen)

    # let user close every popup manually
    if not skip:
        input("Press Enter to continue...")

    # check if body height is bigger than the window height
    body: dict = {
        "width": driver.execute_script("return document.body.clientWidth;"),
        "height": driver.execute_script("return document.body.clientHeight;"),
        "scroll_max": driver.execute_script("return document.body.scrollHeight;"),
    }

    body['nb_page'] = math.ceil(body['height'] / screen['height'])
    print(" > Body:", body)

    # Take first page screenshot
    if body['nb_page'] == 1:
        output = f"{output_folder}/screenshot.png"
        driver.save_screenshot(output)
        return 0
    else:
        driver.save_screenshot(f"{output_folder}/page_0.png")

    # Take the full size screenshot
    print(f"Taking partial screenshots ...")

    partial = {
        "dead_zone": DEAD_ZONE_PX,
        "chunk_size": CHUNK_SIZE_PX,
        "nb_screenshots": math.ceil((body['height'] - screen['height'] - DEAD_ZONE_PX) / CHUNK_SIZE_PX),
    }

    print(" > Partial:", partial)

    print(f"Number of screenshots needed: {partial['nb_screenshots']}")

    screenshot_parts = []

    scroll_diff = 0

    # Take a screenshot of each chunk of the page
    for i in range(partial['nb_screenshots']):
        scroll_offset = screen['height'] + (i * partial['chunk_size']) - partial['dead_zone']

        print(f" > Scroll offset: {scroll_offset}")
        print(f" > Display from: {scroll_offset} to {scroll_offset + screen['height']}")

        if scroll_offset + screen['height'] > body['scroll_max']:
            scroll_diff = body['scroll_max'] - (screen['height'] + scroll_offset)
            scroll_offset = body['scroll_max']

        print(f"Taking screenshot {i + 1} of {partial['nb_screenshots']} ...")
        driver.execute_script(f"window.scrollTo(0, {scroll_offset});")

        if scroll_diff != 0:
            print(f" > Scroll diff: {scroll_diff}")

        output = f"{output_folder}/part_{i}.png"
        driver.save_screenshot(output)

        if not os.path.exists(output):
            print(f"Screenshot {output} was not taken!")
            raise Exception(f"Screenshot {output} not taken!")

    # Chunking screenshot
    print(f"Chunking screenshot ...")

    for i in range(partial['nb_screenshots']):
        output = f"{output_folder}/part_{i}_chunk.png"

        if i != (partial['nb_screenshots'] - 1):
            crop_chunk(
                f"{output_folder}/part_{i}.png",
                output,
                partial['chunk_size'],
                partial['dead_zone'],
                screen['pixel_ratio']
            )
        else:
            crop_queue(
                f"{output_folder}/part_{i}.png",
                output,
                -scroll_diff,
                partial['dead_zone'],
                screen['pixel_ratio']
            )

        screenshot_parts.append(output)

    # Gluing screenshot
    print(f"Gluing screenshot ...")

    screenshot_size = (
        screen['width'],
        body['scroll_max']
    )

    screenshot = Image.new('RGB', screenshot_size)

    for i in range(-1, partial['nb_screenshots']):
        page_height = screen['height']
        chunk_height = partial['chunk_size']

        if i == -1:
            image = Image.open(f"{output_folder}/page_0.png")

            # resize image to aspect ratio 1:1
            image = image.resize(
                (
                    int(screen['width']),
                    int(screen['height'])
                ),
                Image.ADAPTIVE
            )

            screenshot.paste(image, (0, 0))
        else:
            image = Image.open(screenshot_parts[i])

            # get image original size
            image_width, image_height = image.size

            # resize image to aspect ratio 1:1
            image = image.resize(
                (
                    int(screen['width']),
                    int(image_height / screen['pixel_ratio'])
                ),
                Image.ADAPTIVE
            )

            screenshot.paste(image, (0, page_height + (i * chunk_height)))

    output = f"{output_folder}/screenshot.png"

    screenshot.save(output)
    print(f"Screenshot successfully saved to {output}")


def crop_chunk(image_path: str,
               output_path: str,
               chunk_size_px: int,
               dead_zone_px: int,
               pixel_ratio: int):
    # Open the image
    original_image = Image.open(image_path)

    # Get the dimensions of the original image
    width, height = original_image.size

    dead_zone_screen = dead_zone_px * pixel_ratio
    chunk_size_screen = chunk_size_px * pixel_ratio

    # Set the crop box to keep the top 100 pixels
    crop_box = (
        0,
        dead_zone_screen,
        width,
        dead_zone_screen + chunk_size_screen
    )

    # Crop the image
    cropped_image = original_image.crop(crop_box)

    # Save the cropped image
    cropped_image.save(output_path)


def crop_queue(image_path: str,
               output_path: str,
               scroll_diff: int,
               dead_zone_px: int,
               pixel_ratio: int):
    # Open the image
    original_image = Image.open(image_path)

    # Get the dimensions of the original image
    width, height = original_image.size

    print(f" > Scroll diff: {scroll_diff}")

    # Set the crop box to keep the bottom 100 pixels
    if scroll_diff == 0:
        crop_box = (
            0,
            scroll_diff + dead_zone_px,
            width,
            height
        )
    else:
        crop_box = (
            0,
            height - scroll_diff,
            width,
            height
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
