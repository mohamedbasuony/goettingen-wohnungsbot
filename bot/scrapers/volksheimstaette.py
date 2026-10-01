"""Volksheimstätte eG Göttingen — TYPO3-Seite, server-rendered, kein Schutz.

Wenige Angebote, aber first-come-first-served: genau hier zählt Schnelligkeit.
Stellplätze/Fahrradboxen (objectTyp != 1) werden übersprungen.
"""

import re

from bs4 import BeautifulSoup

from ..models import Listing
from .base import BaseScraper, clean, parse_rooms

BASE = "https://www.volksheimstaette.de"
URL = f"{BASE}/de/wohnen/wohnungsangebote"


class Volksheimstaette(BaseScraper):
    name = "volksheimstaette"

    def fetch(self, browser=None) -> list[Listing]:
        soup = BeautifulSoup(self.get(URL).text, "lxml")
        out = []
        for card in soup.select("div.immolist div.card"):
            link = card.select_one("a[href*='objectUid']") or card.find("a", href=True)
            if not link:
                continue
            href = link["href"]
            # href ist URL-encodiert: ...immoliste%5BobjectUid%5D=29...
            uid_m = re.search(r"objectUid(?:%5D|\])=(\d+)", href)
            if not uid_m:
                continue
            typ_m = re.search(r"objectTyp(?:%5D|\])=(\d+)", href)
            if typ_m and typ_m.group(1) != "1":  # 1 = Wohnung
                continue

            title_el = card.select_one("h3.card-title")
            addr_el = card.select_one("p.immo-address")
            rooms, size = None, ""
            for col in card.select(".card-footer .immo-data .col-auto"):
                value_el, label_el = col.select_one("span.h4"), col.select_one("small")
                if not value_el or not label_el:
                    continue
                label = clean(label_el.get_text())
                if "Zimmer" in label:
                    rooms = parse_rooms(value_el.get_text())
                elif "fläche" in label:
                    size = clean(value_el.get_text())
            out.append(Listing(
                platform=self.name,
                listing_id=uid_m.group(1),
                url=href if href.startswith("http") else BASE + href,
                title=clean(title_el.get_text()) if title_el and clean(title_el.get_text())
                      else "Wohnungsangebot Volksheimstätte",
                rooms=rooms,
                size=size,
                address=clean(addr_el.get_text()) if addr_el else "",
            ))
        return out
