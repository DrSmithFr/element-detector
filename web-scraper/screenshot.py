import math
import os
import shutil
import time

import click
import selenium
from PIL import Image
from selenium import webdriver
from selenium.common import WebDriverException

from src.models.Resolution import Resolution

MOBILE_RESOLUTIONS = [
    Resolution(name='iPhone SE', width=375, height=667, pixel_ratio=2, is_touch=True),
    Resolution(name='iPhone 12 Pro', width=390, height=844, pixel_ratio=3, is_touch=True),
    Resolution(name='iPhone 12 Pro Max', width=430, height=932, pixel_ratio=3, is_touch=True),

    Resolution(name='iPad Mini - Vertical', width=768, height=1024, pixel_ratio=3, is_touch=True),
    Resolution(name='iPad Mini - Horizontal', width=1024, height=768, pixel_ratio=3, is_touch=True),

    Resolution(name='720p', width=1280, height=720, pixel_ratio=1),
    Resolution(name='1080p', width=1920, height=1080, pixel_ratio=1),
    Resolution(name='1440p', width=2560, height=1440, pixel_ratio=1),

    Resolution(name='4K', width=3840, height=2160, pixel_ratio=1),
    Resolution(name='5K', width=5120, height=2880, pixel_ratio=1),
    Resolution(name='8K', width=7680, height=4320, pixel_ratio=1),
]

CHUNK_SIZE_PX = 300
DEAD_ZONE_PX = 100


@click.command()
@click.argument('url', type=str, required=True)
@click.option('--skip', default=False, is_flag=True)
@click.option('--parallax', default=False, is_flag=True)
def main(url: str, skip: bool, parallax: bool):
    """Script to take a screenshot of a URL using Selenium with Chrome."""

    # find the resolution of the device
    resolution = MOBILE_RESOLUTIONS[4]

    # Ask the to choose a resolution
    print(" > Select a resolution:")
    for i, res in enumerate(MOBILE_RESOLUTIONS):
        print(f"{i + 1}. {res['name']}")

    choice = input("Enter your choice: ")
    if choice.isdigit():
        choice = int(choice)
        if 0 < choice <= len(MOBILE_RESOLUTIONS):
            resolution = MOBILE_RESOLUTIONS[choice - 1]
            print(f" > You chose {resolution['name']}")
        else:
            raise Exception("Invalid choice, using default resolution.")

    # Load the user profile to avoid cookie popups
    # (you need to accept the cookies manually the first time)
    # (you can use config/categories/homepage to find all websites)
    options = webdriver.ChromeOptions()
    options.add_argument('--user-data-dir=.google-chrome')
    options.add_argument('--profile-directory=.google-profile')
    options.add_argument(f"--window-size={resolution['width']},{resolution['height']}")

    if 'is_touch' in resolution and resolution['is_touch']:
        options.add_experimental_option(
            "mobileEmulation",
            {
                "deviceMetrics": {
                    "width": resolution['width'],
                    "height": resolution['height'],
                    "pixelRatio": resolution['pixel_ratio']
                },
            }
        )

    # Set Chrome as headless to avoid resolution issues
    # options.add_argument('--headless')  # Run Chrome in headless mode (without a graphical interface)

    # Initialize the Chrome driver
    print("Initializing Chrome driver...")
    driver = webdriver.Chrome(options=options)

    # read each file in the folder dataset/categories
    # for each file, take a screenshot of the urls in the file
    # save the screenshot in the folder dataset/{category_name}/
    try:
        take_screenshot(driver, resolution, url, skip, parallax)
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
                    resolution: Resolution,
                    url: str,
                    skip: bool,
                    parallax: bool):
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
    if parallax:
        time.sleep(3)
    else:
        time.sleep(1)

    # Create the output folder if it does not exist
    cache_folder = f"var/{url_slug}"
    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)

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
        remove_cache_folder(cache_folder)
        filename = get_screenshot_filename(resolution)
        driver.save_screenshot(filename)
        print(f"Screenshot successfully saved to {filename}")
        return 0
    else:
        driver.save_screenshot(f"{cache_folder}/page_0.png")

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

        if parallax:
            time.sleep(1)

        if scroll_diff != 0:
            print(f" > Scroll diff: {scroll_diff}")

        output = f"{cache_folder}/part_{i}.png"
        driver.save_screenshot(output)

        if not os.path.exists(output):
            print(f"Screenshot {output} was not taken!")
            raise Exception(f"Screenshot {output} not taken!")

    # Chunking screenshot
    print(f"Chunking screenshot ...")

    for i in range(partial['nb_screenshots']):
        output = f"{cache_folder}/part_{i}_chunk.png"

        if i != (partial['nb_screenshots'] - 1):
            crop_chunk(
                f"{cache_folder}/part_{i}.png",
                output,
                partial['chunk_size'],
                partial['dead_zone'],
                screen['pixel_ratio']
            )
        else:
            crop_queue(
                f"{cache_folder}/part_{i}.png",
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
    total_height = 0

    for i in range(-1, partial['nb_screenshots']):
        page_height = screen['height']
        chunk_height = partial['chunk_size']

        if i == -1:
            image = Image.open(f"{cache_folder}/page_0.png")

            # resize image to aspect ratio 1:1
            image = image.resize(
                (
                    int(screen['width']),
                    int(screen['height'])
                ),
                Image.ADAPTIVE
            )

            total_height += screen['height']
            screenshot.paste(image, (0, 0))
        else:
            image = Image.open(screenshot_parts[i])

            # get image original size
            image_width, image_height = image.size
            height = int(image_height / screen['pixel_ratio'])

            # resize image to aspect ratio 1:1
            image = image.resize(
                (
                    int(screen['width']),
                    int(height)
                ),
                Image.ADAPTIVE
            )

            total_height += height
            screenshot.paste(image, (0, page_height + (i * chunk_height)))

    # Final crop to ensure height is correct even on parallax websites
    screenshot = screenshot.crop((0, 0, screen['width'], total_height))

    remove_cache_folder(cache_folder)
    filename = get_screenshot_filename(resolution)

    screenshot.save(filename)
    print(f"Screenshot successfully saved to {filename}")


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


def remove_cache_folder(cache_folder: str):
    try:
        shutil.rmtree(cache_folder)
        print(f"Cache '{cache_folder}' and its contents have been successfully removed.")
    except OSError as e:
        print(f"Error: {e}")


def get_screenshot_filename(resolution: Resolution):
    return f"screenshots/screenshot-{resolution['width']}x{resolution['height']}-{os.urandom(8).hex()}.png"


if __name__ == '__main__':
    main()
