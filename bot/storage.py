import sqlite3
import time

from .config import DATA_DIR
from .models import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    platform       TEXT NOT NULL,
    listing_id     TEXT NOT NULL,
    url            TEXT,
    title          TEXT,
    price          TEXT,
    rooms          REAL,
    size           TEXT,
    address        TEXT,
    first_seen     INTEGER,
    contacted      INTEGER DEFAULT 0,
    contact_status TEXT,
    PRIMARY KEY (platform, listing_id)
);
CREATE TABLE IF NOT EXISTS contact_log (
    ts INTEGER NOT NULL
);
"""


class Store:
    def __init__(self, path=None):
        DATA_DIR.mkdir(exist_ok=True)
        self.db = sqlite3.connect(path or DATA_DIR / "listings.db")
        self.db.executescript(SCHEMA)

    def is_known(self, platform: str, listing_id: str) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM listings WHERE platform=? AND listing_id=?",
            (platform, listing_id),
        ).fetchone()
        return row is not None

    def count(self, platform: str) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM listings WHERE platform=?", (platform,)
        ).fetchone()[0]

    def add(self, l: Listing):
        self.db.execute(
            "INSERT OR IGNORE INTO listings "
            "(platform, listing_id, url, title, price, rooms, size, address, first_seen) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (l.platform, l.listing_id, l.url, l.title, l.price, l.rooms,
             l.size, l.address, int(time.time())),
        )
        self.db.commit()

    def mark_contacted(self, platform: str, listing_id: str, status: str):
        self.db.execute(
            "UPDATE listings SET contacted=1, contact_status=? "
            "WHERE platform=? AND listing_id=?",
            (status, platform, listing_id),
        )
        self.db.execute("INSERT INTO contact_log (ts) VALUES (?)", (int(time.time()),))
        self.db.commit()

    def contacts_last_hour(self) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM contact_log WHERE ts > ?", (int(time.time()) - 3600,)
        ).fetchone()[0]
