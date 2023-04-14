#!/usr/bin/env python3

import argparse
import os
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
from PIL import Image
import re
import urllib.request
import requests
from google.cloud import storage
import traceback

"""
SCRAGLE\n
This program is a scraping utility for Google search image results.
"""

google_search_base_url = "https://www.google.com/search?q={}&tbm=isch&sxsrf=APwXEdfeyuso-v9A58LJMGlpV-H5WMDh-g%3A1681104750982&source=hp&biw=1440&bih=745&ei=bp8zZI30OZidwbkP7KaEkAo&iflsig=AOEireoAAAAAZDOtfg9ww-3nh_9s_X-hlc7L7O9PlIoK&ved=0ahUKEwiN44qcy57-AhWYTjABHWwTAaIQ4dUDCAc&uact=5&oq=test&gs_lcp=CgNpbWcQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQ6BAgjECdQAFitAmDnBGgAcAB4AIABWIgB3AKSAQE0mAEAoAEBqgELZ3dzLXdpei1pbWc&sclient=img"
images_folder = os.path.join(os.getcwd(), 'images')
if not os.path.exists(images_folder):
    os.mkdir(images_folder)
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
    scroll_script = "window.scrollTo(0, document.body.scrollHeight);"
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
    image = Image.open(image_path).convert('RGB')
    output_size = (image.width * 3, image.height * 3)
    resized_image = image.resize(output_size, resample=Image.LANCZOS)
    resized_image.save(image_path)


def get_image_from_url(url, filename, save_to_local):
    response = requests.get(url)
    content_type = response.headers.get('Content-Type')
    print(
        f"Content-Type: {content_type}, status code: {response.status_code}")
    file_extension = content_type.split('/')[-1]
    filename = f'{filename}.{file_extension}'
    urllib.request.urlretrieve(url, filename)
    resize_image(filename)
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


def write_images(images, count, credentials=None, bucket=None):
    save_to_local = credentials is None
    image_track = 0
    if not save_to_local:
        os.environ['CREDENTIALS'] = credentials
        os.environ['BUCKET'] = bucket
    for image in images:
        print(
            f"""{bcolors.OKGREEN}Image count: {image_track}, {round(image_track/count*100)}% completed"""
        )
        if image_track == count:
            break
        image_src = image.get_attribute('src')
        if image_src is None:
            print("Empty src attribute, skipping.")
            continue
        if 'base64' not in image_src:
            print(f"{bcolors.OKBLUE}Downloading: {image.get_attribute('alt')}")
            cleaned_name = re.sub(r'\W+', '', image.get_attribute('alt'))
            filename = os.path.join(
                images_folder, cleaned_name)
            get_image_from_url(image_src, filename, save_to_local)
            image_track += 1
            continue
        image_b64 = get_base64_string(image_src, image)
        if image is None:
            continue
        file_extension = 'jpeg' if 'jpeg' in image_src else 'png'
        cleaned_name = re.sub(r'\W+', '', image.get_attribute('alt'))
        filename = os.path.join(
            images_folder, f'{cleaned_name}.{file_extension}')
        print(f"{bcolors.OKCYAN}Saving from base 64: {image.get_attribute('alt')}")
        write_from_base64(filename, image_b64[1], save_to_local)
        image_track += 1


def scragle(query, count, params, out='folder'):
    try:
        full_url = google_search_base_url.format(query)
        driver.get(full_url)
        driver.maximize_window()
        time.sleep(3)
        scroll(count)
        images = driver.find_elements(by=By.CLASS_NAME, value='rg_i')
        if len(images) == 0:
            print("No results found.")
            return
        print(f"Starting process with {len(images)} images.")
        if out == 'folder':
            return write_images(images, count)
        elif out == 'gcs':
            return write_images(
                images, count,
                params.credentials,
                params.bucket
            )
    except Exception:
        raise Exception(traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--out", type=str, default='folder',
                        choices=['folder', 'gcs'])
    parser.add_argument("--credentials", type=str, default=None,
                        help="name of service account credentials file")
    parser.add_argument("--bucket", type=str, default=None)
    args = parser.parse_args()
    if args.out == 'folder':
        scragle(args.query, args.count, args, args.out)
    elif args.out == 'gcs':
        if args.credentials is None and args.bucket is None:
            raise Exception(
                """
                Credentials and bucket must be specified
                when using GCS as out parameter.
                """
            )
        scragle(args.query, args.count, args, args.out)


if __name__ == "__main__":
    main()
