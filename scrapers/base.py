"""
Desert to Cape — Base Scraper
새 소스 추가 시 BaseScraper 상속 후 fetch() 구현만 하면 됩니다.
"""
import time, random, requests
from abc import ABC, abstractmethod
from datetime import datetime, UTC
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

class BaseScraper(ABC):
    SOURCE_NAME: str = "Unknown"
    SOURCE_REGION: str = "Unknown"
    SOURCE_URL: str = ""

    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._fetched_at: str = ""

    def get(self, url: str, **kw) -> requests.Response:
        time.sleep(self.delay + random.uniform(0, 0.5))
        r = self.session.get(url, timeout=20, **kw)
        r.raise_for_status()
        return r

    def soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    def fetch(self) -> list[dict]: ...

    def run(self) -> dict:
        self._fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            data = self.fetch()
            return {"source": self.SOURCE_NAME, "region": self.SOURCE_REGION,
                    "fetched_at": self._fetched_at, "status": "ok",
                    "count": len(data), "data": data, "error": None}
        except Exception as e:
            return {"source": self.SOURCE_NAME, "region": self.SOURCE_REGION,
                    "fetched_at": self._fetched_at, "status": "error",
                    "count": 0, "data": [], "error": str(e)}
