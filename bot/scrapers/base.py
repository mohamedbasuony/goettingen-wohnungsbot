import re

import httpx

from ..models import Listing

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def parse_rooms(text) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"(\d+(?:[.,]\d)?)", str(text))
    return float(m.group(1).replace(",", ".")) if m else None


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text).strip() if text else ""


class BaseScraper:
    name = "base"
    uses_browser = False  # True -> fetch() gets a Playwright Browser

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def fetch(self, browser=None) -> list[Listing]:
        raise NotImplementedError

    def get(self, url: str, **kw) -> httpx.Response:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30, **kw)
        r.raise_for_status()
        return r
