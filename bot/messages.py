from .config import profile
from .models import Listing


def build_contact_message(cfg: dict, listing: Listing) -> str:
    p = profile()
    household_line = f"{p['household'].strip()} " if p.get("household") else ""
    template = cfg["contact"]["message_template"]
    return template.format(
        title=listing.title or "Ihre Wohnungsanzeige",
        full_name=p["full_name"],
        email=p["email"],
        phone=p["phone"],
        occupation=p["occupation"],
        household_line=household_line,
    ).strip()
