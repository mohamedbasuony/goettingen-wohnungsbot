"""Kleinanzeigen.de — Mietwohnungen Göttingen (Ortscode l3130).

Server-rendered, kein Bot-Schutz. Zimmerfilter direkt in der URL
(Format zimmer_d:MIN%2C = offen nach oben).
"""

from bs4 import BeautifulSoup

from ..models import Listing
from .base import BaseScraper, clean, parse_rooms

BASE = "https://www.kleinanzeigen.de"


class Kleinanzeigen(BaseScraper):
    name = "kleinanzeigen"

    def search_url(self) -> str:
        min_rooms = self.cfg["filters"]["min_rooms"]
        return (f"{BASE}/s-wohnung-mieten/goettingen/"
                f"c203l3130+wohnung_mieten.zimmer_d:{min_rooms:g}%2C")

    def fetch(self, browser=None) -> list[Listing]:
        soup = BeautifulSoup(self.get(self.search_url()).text, "lxml")
        out = []
        for card in soup.select("article.aditem"):
            adid = card.get("data-adid")
            href = card.get("data-href", "")
            if not adid or not href:
                continue
            # "TOP"-Anzeigen sind bezahlte Platzierungen, die den Filter ignorieren
            if card.select_one(".aditem-image--badges--badge-topad"):
                continue
            title = clean(card.select_one("h2 a") and card.select_one("h2 a").get_text())
            price_el = card.select_one("p.aditem-main--middle--price-shipping--price")
            tags = clean((card.select_one("p.aditem-main--middle--tags") or {}).get_text()
                         if card.select_one("p.aditem-main--middle--tags") else "")
            rooms, size = None, ""
            for part in tags.split("·"):
                part = part.strip()
                if "Zi" in part:
                    rooms = parse_rooms(part)
                elif "m²" in part:
                    size = part
            addr_el = card.select_one("div.aditem-main--top--left")
            out.append(Listing(
                platform=self.name,
                listing_id=adid,
                url=BASE + href,
                title=title,
                price=clean(price_el.get_text()) if price_el else "",
                rooms=rooms,
                size=size,
                address=clean(addr_el.get_text()) if addr_el else "",
            ))
        return out
