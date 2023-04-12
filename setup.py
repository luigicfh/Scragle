import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='scragler',
    version='1.0.0',
    license='MIT',
    description='SCRAGLER is a CLI utility for scraping Google search image results and store them in your local machine or GCS.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Luis Moreno',
    author_email='luis.cfh.90@gmail.com',
    url='https://github.com/luigicfh/google_images_scraper',
    project_urls={
        "Bug Tracker": "https://github.com/luigicfh/google_images_scraper/issues"
    },
    install_requires=['google-cloud-storage',
                      'selenium', 'pillow', 'webdriver-manager'],
    packages=setuptools.find_packages(),
    keywords=["pypi", "handler_module", "cloud_functions"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "scragle = scragle:main",
        ]
    }
)
