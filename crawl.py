import requests
import logging
import os
import re
import datetime
import json
import socket
import platform
import shutil
from bs4 import BeautifulSoup

defaultEncoding = "utf-8"
tasksDef = "./tasks.txt"
resultDir = "./result"
connectionRetryTimes = 3
proxies = { 
    "http": "http://localhost:1080", 
    "https": "http://localhost:1080",
}

class RssCrawler:
    def __init__(self, url, alias, basedir, proxies=None, forceRedownload=False) -> None:
        self.url = url
        self.alias = alias
        self.basedir = basedir
        self.forceRedownload = forceRedownload
        self.proxies = proxies or {}

        self.downloadedFileCache = set()

        self.logger = logging.getLogger("Crawler@{}".format(alias))
        loggerHandler = logging.StreamHandler()
        loggerHandler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
        self.logger.addHandler(loggerHandler)
        self.logger.setLevel(logging.DEBUG)

    def _retry(self, func, retryTimes: int):
        triedTimes = 0
        while triedTimes <= retryTimes:
            triedTimes += 1
            self.logger.debug("Trying %d times, max %d times...", triedTimes, retryTimes)
            try:
                return func()
            except e:
                self.logger.error(e)

    def _saveToFile(self, s: str, filename: str) -> None:
        with open(filename, 'w', encoding=defaultEncoding) as f:
            f.write(str(s))

    def _toLegalFilename(self, s: str) -> str:
        return re.sub('[^\w\-_\. ]', '_', s)

    def _createDirectory(self, path: str) -> None:
        os.makedirs(os.path.normcase(os.path.normpath(path)), exist_ok=True)

    def _downloadFile(self, url, force=None):
        if force == None:
            force = self.forceRedownload
        localFileName = os.path.join(self.basedir, "media", os.path.normcase(os.path.normpath("/".join(map(self._toLegalFilename, filter(len, url.split("/")))))))
        self._createDirectory(os.path.dirname(localFileName))

        if url in self.downloadedFileCache:
            self.logger.warn("Duplicate file in this session %s", url)
            return

        if os.path.isfile(localFileName):
            if not force:
                self.logger.warn("File exists for %s", url)
                return
            else:
                self.logger.warn("Re-downloading file %s", url)

        self.logger.debug("Downloading %s", url)
        self.downloadedFileCache.add(url)
        with self._retry(lambda:requests.get(url, stream=True, proxies=self.proxies), connectionRetryTimes) as r:
            r.raw.decode_content = True
            with open(localFileName, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

    def crawl(self) -> None:
        self.logger.info("Start crawling %s", self.url)
        self._createDirectory(self.basedir)
        self._saveToFile(json.dumps({
            "url": self.url,
            "crawlTime": datetime.datetime.now(),
            "crawlHost": socket.gethostname(),
            "OS": "{} {} {} {}".format(platform.system(), platform.release(), platform.version(), platform.machine()),
            "Python": "{} {} {}".format( platform.python_implementation(), platform.python_version(), platform.python_compiler()),
        }, default=str, indent=4), os.path.join(self.basedir, "config.json"))
        
        self.logger.debug("Downloading RSS description...")
        r = self._retry(lambda:requests.get(self.url, proxies=self.proxies), connectionRetryTimes)
        self.logger.debug("Status=%d, Type='%s', Encoding=%s", r.status_code, r.headers['content-type'] or "None", r.encoding)

        self.logger.debug("Saving RSS description...")
        self._saveToFile(r.text, os.path.join(self.basedir, "metadata.xml"))

        self.logger.debug("Processing RSS description...")
        soup = BeautifulSoup(r.text, 'xml')
        for channel in soup:
            self.logger.info("Entering channel %s", channel.title.string)
            channelPath = os.path.join(self.basedir, self._toLegalFilename(channel.title.string))
            self._createDirectory(channelPath)

            # crawl media contents
            for image in channel.find_all("itunes:image", recursive=False):
                self._downloadFile(image["href"])

            for article in channel.find_all('item'):
                self.logger.info("Archiving article %s", article.title.string)
                itemPath = os.path.join(channelPath, self._toLegalFilename("{}_{}".format(article.title.string, article.guid.string)))
                self._createDirectory(itemPath)

                # save item metadata
                self._saveToFile(article, os.path.join(itemPath, "metadata.part.xml"))

                # crawl media contents
                for image in article.find_all("itunes:image"):
                    self._downloadFile(image["href"])
                for img in article.find_all("img"):
                    self._downloadFile(image["href"])
                for audio in article.find_all("enclosure"):
                    self._downloadFile(audio["url"])

        r.close()

if __name__ == "__main__":
    os.makedirs(resultDir, exist_ok=True)
    
    with open(tasksDef, "r", encoding=defaultEncoding) as tasks:
        for line in tasks.readlines():
            normalizedLine = line.strip()
            if len(normalizedLine) > 0 and not normalizedLine.startswith("#"):  # exclude comment
                url, alias = normalizedLine.split(" ", maxsplit=1)
                datastore = os.path.join(resultDir, alias)

                crawler = RssCrawler(url, alias, datastore, forceRedownload=True)
                crawler.crawl()