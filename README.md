# Scragle

Scragle is a CLI tool for scraping Google search image results.

## Installation

To install Scragle, simply run:

```
git clone https://github.com/luigicfh/google_images_scraper.git
```

```python
cd google_images_scraper
```

```python
pip install .
```

## Usage

To use Scragle, execute the command scragle followed by the required argument —count which specifies how many images you want to download from Google.

```bash
scragle --count=10

```

You will be prompted to paste the following items:

- The full url of your search in Google Images
- The element class name for the small thumbnails in the search results page
- If image quality is set to standard (sd) you will be asked to paste the class name for the image in the modal opened when clicking a thumbnail

Once Scragle runs it will create a new folder called images and store the results there.

By default Scragle will just obtain images from the small thumbnails in the search result page, it will resize it and attempt to remove pixelation, this is the fastest way to get results but the quality of the images is poor.

```python
def resize_image(image_path):
    standard_quality_images = os.environ.get("IMG_QUALITY") == 'sd'
    if standard_quality_images:
        return
    print("Resizing...")
    image = Image.open(image_path).convert('RGB')
    output_size = (image.width * 3, image.height * 3)
    resized_image = image.resize(output_size, resample=Image.LANCZOS)
    resized_image.save(image_path)
```

If you wish to get a better quality you can pass the —imagequality tag with the value sd (standard), then Scragle will attempt to obtain the higher quality image but the process will take a bit longer to finish.

```bash
scragle --count=10 --imagequality=sd
```

You can also save your images to Google Cloud Storage, by passing the —out argument as gcs and specifying the —credentials (path to service account credentials) and —bucket (bucket name).

```bash
scragle --count=10 --imagequality=sd --out=gcs --credentials=<path_to_credentials> --bucket=<bucket_name>
```

## License

Scragle is licensed under the [MIT License](https://www.notion.so/LICENSE).
