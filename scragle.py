#!/usr/bin/env python3

import argparse
import os
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from PIL import Image
import re
import urllib.request
from urllib.parse import urlparse
import requests
from google.cloud import storage
import traceback
import uuid

"""
SCRAGLE\n
This program is a scraping utility for Google search image results.
"""


images_folder = os.path.join(os.getcwd(), 'images')
if not os.path.exists(images_folder):
    os.mkdir(images_folder)
js_folder = os.path.join(os.getcwd(), 'js')
with open(os.path.join(js_folder, 'scroll.js')) as file:
    scroll_script = file.read()
options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(service=Service(
    ChromeDriverManager().install()), options=options)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def scroll(count):
    print("Scrolling page, please wait...")
    results_per_page = 20
    if count < results_per_page:
        driver.execute_script(scroll_script)
        time.sleep(3)
        return
    scroll_times = count/results_per_page
    if scroll_times.is_integer():
        for i in range(int(scroll_times)):
            driver.execute_script(scroll_script)
            time.sleep(3)
        return
    scroll_times = int(scroll_times) + 1
    for i in range(scroll_times):
        driver.execute_script(scroll_script)
        time.sleep(3)


def resize_image(image_path):
    standard_quality_images = os.environ.get("IMG_QUALITY") == 'sd'
    if standard_quality_images:
        return
    print("Resizing...")
    image = Image.open(image_path).convert('RGB')
    output_size = (image.width * 3, image.height * 3)
    resized_image = image.resize(output_size, resample=Image.LANCZOS)
    resized_image.save(image_path)

def set_request_headers():
    return {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
    }

def get_image_from_url(url, filename, save_to_local):
    headers = set_request_headers()
    standard_quality_images = os.environ.get("IMG_QUALITY") != 'low'
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(
        f"""Skipping due to invalid response from server: {response.status_code}\n
        URL: {url}""")
        return
    content_type = response.headers.get('Content-Type')
    print(
        f"Content-Type: {content_type}, status code: {response.status_code}")
    if 'webp' in content_type:
        file_extension = 'jpeg'
    elif content_type is not None:
        file_extension = content_type.split('/')[-1]
    else:
        file_extension = 'jpeg'
    filename = f'{filename}.{file_extension}'
    if not standard_quality_images:
        urllib.request.urlretrieve(url, filename)
        resize_image(filename)
    else:
        with open(filename, 'wb') as file:
            file.write(response.content)
    if not save_to_local:
        upload_to_gcs(filename)
        os.remove(filename)


def get_base64_string(image_src, image_element):
    if 'jpeg' in image_src:
        return image_element.get_attribute(
            'src').split('data:image/jpeg;base64,')
    elif 'png' in image_src:
        return image_element.get_attribute(
            'src').split('data:image/png;base64,')
    return None


def write_from_base64(filename, base64_string, save_to_local):
    with open(filename, 'wb') as file:
        file.write(base64.b64decode(base64_string))
    resize_image(filename)
    if not save_to_local:
        upload_to_gcs(filename)
        os.remove(filename)


def upload_to_gcs(filename):
    gcs_client = storage.Client().from_service_account_json(
        os.environ.get("CREDENTIALS"))
    bucket = gcs_client.bucket(os.environ.get("BUCKET"))
    blob = bucket.blob(filename.split("/")[-1])
    file_extension = 'jpeg' if 'jpeg' in filename else 'png'
    blob.upload_from_filename(
        filename, content_type=f'image/{file_extension}')

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def get_elements(class_name):
    elements = driver.find_elements(by=By.CLASS_NAME, value=class_name)
    if len(elements) == 0:
        return None
    return elements

def fetch_sd_quality_image(image):
    sd_image_class_name = os.environ.get("SD_IMAGE_CLASS")
    larger_thumbnail = get_elements(sd_image_class_name)
    if larger_thumbnail is None:
        print("This element does not posses a higher quality image.")
        print("Fetching low quality image...")
        return image
    https_image_element = [
    image_element for image_element in larger_thumbnail if is_valid_url(image_element.get_attribute('src'))
    ]
    return https_image_element[0] if len(https_image_element) == 1 else image 

def get_image(image, save_to_local, image_track):
    image_src = image.get_attribute('src')
    if image_src is None:
        print("Empty src attribute, skipping.")
        return image_track
    if 'base64' not in image_src:
        print(f"{bcolors.OKBLUE}Downloading: {image.get_attribute('alt')}")
        cleaned_name = re.sub(r'\W+', '', image.get_attribute('alt')) + str(uuid.uuid4())
        filename = os.path.join(
            images_folder, cleaned_name)
        get_image_from_url(image_src, filename, save_to_local)
        image_track += 1
        return image_track
    image_b64 = get_base64_string(image_src, image)
    file_extension = 'jpeg' if 'jpeg' in image_src else 'png'
    cleaned_name = re.sub(r'\W+', '', image.get_attribute('alt'))
    filename = os.path.join(
        images_folder, f'{cleaned_name + str(uuid.uuid4())}.{file_extension}')
    print(f"{bcolors.OKCYAN}Saving from base 64: {image.get_attribute('alt')}")
    write_from_base64(filename, image_b64[1], save_to_local)
    image_track += 1
    return image_track

def write_images(images, count, credentials=None, bucket=None, quality='low'):
    save_to_local = credentials is None
    image_track = 0
    if not save_to_local:
        os.environ['CREDENTIALS'] = credentials
        os.environ['BUCKET'] = bucket
    os.environ["QUALITY"] = quality
    for image in images:
        print(
            f"""{bcolors.OKGREEN}Image count: {image_track}, {round(image_track/count*100)}% completed"""
        )
        if image_track == count:
            break
        if quality == 'low':
            image_track = get_image(image, save_to_local, image_track)
        else:
            image.click()
            time.sleep(3)
            thumbnail = fetch_sd_quality_image(image)
            image_track = get_image(thumbnail, save_to_local, image_track)

def ready_page(url, count):
    driver.get(url)
    driver.maximize_window()
    time.sleep(3)
    scroll(count)
    print("Page ready...")

def scragle(count, params, out='folder'):
    try:
        full_url = input(
            """Paste the Google Search Images result URL: """
        )
        if not full_url or not is_valid_url(full_url):
            raise ValueError(
                """The value provided is not valid."""
            )
        ready_page(full_url, count)
        small_thumbnail_class = input(
            """Paste the class name for the small thumbnail elements: """
        )
        if not small_thumbnail_class:
            raise ValueError(
                """
                Please provide a valid value.
                """
            )
        images = get_elements(small_thumbnail_class.strip())
        if images is None:
            print(
            f"Elements with class name {small_thumbnail_class} not found.")
            print("Exiting...")
            return
        print(f"Starting process with {len(images)} images.")
        if params.imagequality == 'sd':
            print("Standard quality images will take longer to fetch...")
            sd_quality_images_class = input(
                """Paste the class name for the modal image element: """
            )
            if not sd_quality_images_class:
                raise ValueError(
                    """
                    Please provide a valid value.
                    """
                )
            os.environ["SD_IMAGE_CLASS"] = sd_quality_images_class.strip()
        if out == 'folder':
            return write_images(
                images, 
                count, 
                params.credentials, 
                params.bucket, 
                params.imagequality
            )
        elif out == 'gcs':
            return write_images(
                images, 
                count,
                params.credentials,
                params.bucket,
                params.imagequality
            )
    except Exception:
        raise Exception(traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--imagequality", type=str, default='low', 
                        choices=['low', 'sd'])
    parser.add_argument("--out", type=str, default='folder',
                        choices=['folder', 'gcs'])
    parser.add_argument("--credentials", type=str, default=None,
                        help="name of service account credentials file")
    parser.add_argument("--bucket", type=str, default=None)
    args = parser.parse_args()
    if args.out == 'folder':
        scragle(args.count, args, args.out)
    elif args.out == 'gcs':
        if args.credentials is None and args.bucket is None:
            raise Exception(
                """
                Credentials and bucket must be specified
                when using GCS as out parameter.
                """
            )
        scragle(args.count, args, args.out)


if __name__ == "__main__":
    main()
