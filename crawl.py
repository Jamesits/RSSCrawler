import requests
import logging
import os
from bs4 import BeautifulSoup

tasksDef = "./tasks.txt"
resultDir = "./result"

class RssCrawler:
    def __init__(self) -> None:
        self.logger = logging.getLogger("Crawler")
        loggerHandler = logging.StreamHandler()
        loggerHandler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
        self.logger.addHandler(loggerHandler)
        self.logger.setLevel(logging.DEBUG)

    def crawl(self, url: str) -> None:
        self.logger.info("Start crawling %s", url)

if __name__ == "__main__":
    # check if destination directory exists
    if not os.path.exists(directory):
        os.makedirs(directory)

    crawler = RssCrawler()
    
    with open(tasksDef, "r") as tasks:
        for originUrl in tasks.readlines():
            normalizedUrl = originUrl.strip()
            if not normalizedUrl.startswith("#"):  # exclude comment
                crawler.crawl(normalizedUrl)