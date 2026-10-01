import html

import httpx

from .config import env
from .models import Listing

API = "https://api.telegram.org/bot{token}/{method}"


class Telegram:
    def __init__(self):
        self.token = env("TELEGRAM_BOT_TOKEN", required=True)
        self.chat_id = env("TELEGRAM_CHAT_ID", required=True)

    def send(self, text: str, disable_preview: bool = True):
        r = httpx.post(
            API.format(token=self.token, method="sendMessage"),
            data={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            },
            timeout=30,
        )
        r.raise_for_status()

    def send_listing(self, l: Listing, contact_status: str | None = None):
        rooms = f"{l.rooms:g}" if l.rooms is not None else "unknown"
        lines = [
            f"🏠 <b>{html.escape(l.title or 'New apartment')}</b>",
            f"🌐 New apartment — {platform_label(l.platform)}",
            f"📍 {html.escape(l.address)}" if l.address else None,
            f"🚪 Rooms: {rooms}",
            f"📐 {html.escape(l.size)}" if l.size else None,
            f"💶 {html.escape(l.price)}" if l.price else None,
            f"🔗 {l.url}",
        ]
        if contact_status:
            lines.append(f"✉️ Contact request: {contact_status}")
        self.send("\n".join(x for x in lines if x), disable_preview=False)


def platform_label(name: str) -> str:
    return {
        "kleinanzeigen": "Kleinanzeigen",
        "immoscout24": "ImmobilienScout24",
        "immowelt": "Immowelt",
        "wg_gesucht": "WG-Gesucht",
        "volksheimstaette": "Volksheimstätte eG",
        "wg_eg": "Wohnungsgenossenschaft eG Göttingen",
        "vonovia": "Vonovia",
    }.get(name, name)
