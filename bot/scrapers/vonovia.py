"""Vonovia — offene JSON-API, kein Bot-Schutz. Der einfachste Scraper."""

from ..models import Listing
from .base import BaseScraper

API = ("https://www.vonovia.de/api/real-estate/list"
       "?rentType=miete&city=G%C3%B6ttingen&immoType=wohnung&offset=0&limit=50")


class Vonovia(BaseScraper):
    name = "vonovia"

    def fetch(self, browser=None) -> list[Listing]:
        data = self.get(API).json()
        out = []
        for r in data.get("results", []):
            if not r.get("wrk_id"):
                continue
            price = r.get("preis")
            size = r.get("groesse")
            out.append(Listing(
                platform=self.name,
                listing_id=str(r["wrk_id"]),
                url=f"https://www.vonovia.de/zuhause-finden/immobilien/{r.get('slug', '')}",
                title=r.get("titel") or "Vonovia-Wohnung",
                price=f"{price} €" if price else "",
                rooms=float(r["anzahl_zimmer"]) if r.get("anzahl_zimmer") else None,
                size=f"{size} m²" if size else "",
                address=", ".join(filter(None, [r.get("strasse"),
                                                f"{r.get('plz', '')} {r.get('ort', '')}".strip()])),
            ))
        return out
