"""ImmobilienScout24 — hinter AWS-WAF-Bot-Schutz, deshalb via echtem Browser.

Der persistente Chromium (data/browser-profile) besteht die JS-Challenge in
der Regel automatisch; eingeloggt zu sein (python -m bot.login) hilft
zusätzlich. Geparst wird absichtlich locker über /expose/-Links + Kartentext,
weil IS24 seine CSS-Klassen häufig ändert.
"""

import re

from ..models import Listing
from .base import BaseScraper, parse_rooms


class ImmoScout24(BaseScraper):
    name = "immoscout24"
    uses_browser = True

    def search_url(self) -> str:
        f = self.cfg["filters"]
        return ("https://www.immobilienscout24.de/Suche/de/niedersachsen/goettingen-kreis/"
                f"goettingen/wohnung-mieten?numberofrooms={f['min_rooms']:.1f}-{f['max_rooms']:.1f}")

    def fetch(self, browser=None) -> list[Listing]:
        if browser is None:
            raise RuntimeError("ImmoScout24 needs the browser (AWS WAF protection). "
                               "Check the headless/auto_contact configuration.")
        page = browser.page()
        try:
            page.goto(self.search_url(), wait_until="domcontentloaded")
            try:
                page.wait_for_selector('a[href*="/expose/"]', timeout=30000)
            except Exception:
                shot = browser.screenshot_failure(page, "immoscout24-search")
                raise RuntimeError(
                    "Search results did not load — most likely bot protection/captcha. "
                    f"Screenshot: {shot}. Tip: run `python -m bot.login` once and sign in "
                    "at ImmoScout24 (solve the captcha by hand there)."
                )
            found: dict[str, Listing] = {}
            for a in page.query_selector_all('a[href*="/expose/"]'):
                href = a.get_attribute("href") or ""
                m = re.search(r"/expose/(\d+)", href)
                if not m:
                    continue
                lid = m.group(1)
                text = a.evaluate("el => (el.closest('article, li') || el).innerText") or ""
                text = re.sub(r"\s+", " ", text)
                if lid in found and len(text) <= len(found[lid].raw.get("text", "")):
                    continue
                price_m = re.search(r"(\d[\d.,]*\s*€)", text)
                rooms_m = re.search(r"(\d+(?:[.,]\d)?)\s*Zi", text)
                size_m = re.search(r"(\d+(?:[.,]\d+)?\s*m²)", text)
                title = (a.get_attribute("title") or "").strip() or text[:90]
                found[lid] = Listing(
                    platform=self.name,
                    listing_id=lid,
                    url=f"https://www.immobilienscout24.de/expose/{lid}",
                    title=title.strip() or "ImmoScout24-Wohnung",
                    price=price_m.group(1) if price_m else "",
                    rooms=parse_rooms(rooms_m.group(1)) if rooms_m else None,
                    size=size_m.group(1) if size_m else "",
                    raw={"text": text},
                )
            return list(found.values())
        finally:
            page.close()
