"""WG-Gesucht.de — Kategorie 2 = Wohnungen (2+ Zimmer), Stadt-ID Göttingen = 49.

Kein eigener 3-Zimmer-Filter in der URL; die Zimmerzahl steht im Kartentitel
("3-Zimmer-Wohnung | Göttingen ...") und wird hier geparst — der globale
Filter erledigt den Rest. Achtung: WG-Gesucht ratelimitet bei hohem Volumen.
"""

from bs4 import BeautifulSoup

from ..models import Listing
from .base import BaseScraper, clean, parse_rooms

BASE = "https://www.wg-gesucht.de"
URL = f"{BASE}/wohnungen-in-Goettingen.49.2.1.0.html"


class WgGesucht(BaseScraper):
    name = "wg_gesucht"

    def fetch(self, browser=None) -> list[Listing]:
        soup = BeautifulSoup(self.get(URL).text, "lxml")
        out = []
        for card in soup.select("div.wgg_card.offer_list_item"):
            if "panel-deactivated" in " ".join(card.get("class", [])):
                continue
            ad_id = card.get("data-id")
            link = card.select_one("h2.truncate_title a")
            if not ad_id or not link or not link.get("href"):
                continue
            href = link["href"]
            info_el = card.select_one("div.col-xs-11 > span")
            info = clean(info_el.get_text()) if info_el else ""
            parts = [p.strip() for p in info.split("|")]  # "3-Zimmer-Wohnung | Göttingen Geismar | Straße"
            rooms = parse_rooms(parts[0]) if parts and "Zimmer" in parts[0] else None
            address = ", ".join(parts[1:]) if len(parts) > 1 else ""

            price_el = card.select_one("div.row.noprint.middle div.col-xs-3 b")
            size_el = card.select_one("div.row.noprint.middle div.col-xs-3.text-right b")
            out.append(Listing(
                platform=self.name,
                listing_id=ad_id,
                url=href if href.startswith("http") else BASE + "/" + href.lstrip("/"),
                title=clean(link.get_text()),
                price=clean(price_el.get_text()) if price_el else "",
                rooms=rooms,
                size=clean(size_el.get_text()) if size_el else "",
                address=address,
            ))
        return out
