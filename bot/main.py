import logging
import time

from . import contact, klein_login
from .browser import Browser
from .config import DATA_DIR, kleinanzeigen_credentials, load_config
from .messages import build_contact_message
from .models import Listing
from .scrapers import ALL_SCRAPERS
from .storage import Store
from .telegram import Telegram, platform_label

log = logging.getLogger("wohnungsbot")


def setup_logging():
    DATA_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(DATA_DIR / "bot.log", encoding="utf-8"),
        ],
    )


def passes_filters(cfg: dict, l: Listing) -> bool:
    import re
    from .config import resolve_filters
    f = resolve_filters(cfg)

    # rooms
    if l.rooms is None:
        if not f.get("include_unknown_rooms", True):
            return False
    elif not (f["min_rooms"] <= l.rooms <= f["max_rooms"]):
        return False

    # max cold rent
    if f.get("max_rent_cold"):
        m = re.search(r"(\d[\d.]*)", l.price.replace(".", ""))
        if m and float(m.group(1)) > f["max_rent_cold"]:
            return False

    # postal code(s) within Göttingen — only if the user restricted to some.
    # Lenient: a listing whose address has no 5-digit PLZ is let through.
    codes = f.get("postal_codes") or []
    if codes:
        m = re.search(r"\b(\d{5})\b", l.address or "")
        if m and m.group(1) not in codes:
            return False

    return True


def try_contact(cfg, store: Store, browser, l: Listing) -> str | None:
    """Send the German viewing request. Returns a human-readable status."""
    handler = contact.HANDLERS.get(l.platform)
    if handler is None:
        return None
    if l.rooms is None:
        return "skipped (room count unknown — please check the ad yourself)"
    limit = cfg["contact"].get("max_per_hour", 8)
    if store.contacts_last_hour() >= limit:
        return f"skipped (limit of {limit}/hour reached — please contact manually)"
    message = build_contact_message(cfg, l)
    try:
        status = handler(browser, l, message)
        store.mark_contacted(l.platform, l.listing_id, status)
        return status
    except Exception as e:
        log.exception("Contact attempt failed: %s", l.url)
        return f"FAILED ({type(e).__name__}) — please contact manually"


def scan_platform(cfg, store, tg, browser, name, scraper_cls, allow_contact) -> bool:
    """Scan one platform; notify on new matches, optionally auto-contact them.

    Returns True if the fetch succeeded, False if it failed (e.g. rate-limited).
    """
    pconf = cfg["platforms"].get(name) or {}
    try:
        listings = scraper_cls(cfg).fetch(browser)
    except Exception as e:
        log.warning("Scraper %s failed: %s: %s", name, type(e).__name__, e)
        return False

    baseline = store.count(name) == 0
    fresh = [l for l in listings if not store.is_known(l.platform, l.listing_id)]
    if fresh or baseline:
        log.info("%s: %d listings, %d new%s", name, len(listings), len(fresh),
                 " (baseline run, no auto-contact)" if baseline else "")

    first_run_cap = cfg.get("first_run_max_per_platform", 15)
    sent = 0
    for l in fresh:
        store.add(l)
        if not passes_filters(cfg, l):
            continue
        if baseline and sent >= first_run_cap:
            continue
        status = None
        # Auto-contact ONLY genuinely new ads (never the baseline backlog),
        # and only where enabled + a browser session exists.
        if (allow_contact and not baseline and pconf.get("auto_contact")
                and browser is not None):
            status = try_contact(cfg, store, browser, l)
        try:
            tg.send_listing(l, status)
            sent += 1
            time.sleep(1.2)  # stay under Telegram's rate limit
        except Exception:
            log.exception("Telegram delivery failed for %s", l.url)

    if baseline:
        matched = sum(1 for l in fresh if passes_filters(cfg, l))
        more = matched - sent
        if more > 0:
            _safe_tg(tg, f"ℹ️ {platform_label(name)}: showed {sent} of {matched} currently-listed "
                     f"matches (+{more} more already online). From now on you'll get each new one.")
    return True


def rooms_label(cfg: dict) -> str:
    """Human label for the configured room count, e.g. '3 Zimmer', '3–3.5 Zimmer', '3+ Zimmer'."""
    f = cfg.get("filters") or {}
    lo, hi = f.get("min_rooms"), f.get("max_rooms")
    if lo is None:
        return "Wohnungen"
    if hi is None or hi >= 99:
        return f"{lo:g}+ Zimmer"
    if lo == hi:
        return f"{lo:g} Zimmer"
    return f"{lo:g}–{hi:g} Zimmer"


def _safe_tg(tg, text):
    """Send a Telegram note but never let a network/Telegram error crash the loop."""
    try:
        tg.send(text)
    except Exception:
        log.warning("Telegram notify failed (continuing): %s", text[:50])


def needs_browser(cfg) -> bool:
    for name, scraper_cls in ALL_SCRAPERS.items():
        pconf = cfg["platforms"].get(name) or {}
        if pconf.get("enabled") and (scraper_cls.uses_browser or pconf.get("auto_contact")):
            return True
    return False


def run_loop(cfg, store, tg, browser):
    klein_interval = cfg.get("kleinanzeigen_interval_seconds", 30)
    others_interval = cfg.get("poll_interval_seconds", 300)
    klein_enabled = (cfg["platforms"].get("kleinanzeigen") or {}).get("enabled")

    # One-time login attempt so auto-contact has a session.
    if browser is not None and klein_enabled:
        email, password = kleinanzeigen_credentials()
        ok, status = klein_login.attempt_login(browser, email, password)
        log.info("Kleinanzeigen login: %s", status)
        _safe_tg(tg, ("🔐 Kleinanzeigen logged in — auto-messaging is active."
                      if ok else f"⚠️ Kleinanzeigen not logged in: {status} "
                                 "New ads will still be sent to you as links until then."))

    # Adaptive back-off: if Kleinanzeigen starts rate-limiting the fast polling,
    # slow down (exponentially, capped) until it recovers, so we don't get the IP
    # blocked. base = configured interval; max_backoff caps the slow-down.
    max_backoff = max(120, klein_interval * 8)
    current = klein_interval
    fails = 0
    backoff_notified = False

    last_others = 0.0
    while True:
        start = time.monotonic()

        if klein_enabled:
            ok = scan_platform(cfg, store, tg, browser, "kleinanzeigen",
                               ALL_SCRAPERS["kleinanzeigen"], allow_contact=True)
            if ok:
                if fails and backoff_notified:
                    _safe_tg(tg, f"✅ Kleinanzeigen recovered — back to a {klein_interval}s scan.")
                fails = 0
                current = klein_interval
                backoff_notified = False
            else:
                fails += 1
                current = min(klein_interval * (2 ** fails), max_backoff)
                log.warning("Kleinanzeigen scan failed (%dx) — backing off to %ss", fails, current)
                if fails >= 3 and not backoff_notified:
                    _safe_tg(tg, f"⚠️ Kleinanzeigen is rate-limiting the {klein_interval}s scan. "
                             f"Backing off to {current}s to protect the IP; I'll speed back up "
                             f"once it recovers. (Raise kleinanzeigen_interval_seconds if this persists.)")
                    backoff_notified = True

        if time.monotonic() - last_others >= others_interval:
            for name, scraper_cls in ALL_SCRAPERS.items():
                if name == "kleinanzeigen":
                    continue
                if not (cfg["platforms"].get(name) or {}).get("enabled"):
                    continue
                scan_platform(cfg, store, tg, browser, name, scraper_cls, allow_contact=False)
            last_others = time.monotonic()

        time.sleep(max(1.0, current - (time.monotonic() - start)))


def main():
    setup_logging()
    cfg = load_config()
    store = Store()
    tg = Telegram()
    klein_interval = cfg.get("kleinanzeigen_interval_seconds", 30)
    others_interval = cfg.get("poll_interval_seconds", 300)
    label = rooms_label(cfg)
    klein_auto = (cfg["platforms"].get("kleinanzeigen") or {}).get("auto_contact")
    klein_line = (f"• Kleinanzeigen: every {klein_interval}s + auto-message new matches"
                  if klein_auto else
                  f"• Kleinanzeigen: every {klein_interval}s (links only)")

    _safe_tg(tg, f"🤖 Göttingen apartment bot started — searching {label}.\n{klein_line}\n"
             f"• Other platforms: every {others_interval // 60} min (links only)")
    log.info("Started. Kleinanzeigen %ss, others %ss", klein_interval, others_interval)

    try:
        if needs_browser(cfg):
            with Browser(headless=cfg.get("headless", True)) as browser:
                run_loop(cfg, store, tg, browser)
        else:
            run_loop(cfg, store, tg, None)
    except KeyboardInterrupt:
        log.info("Stopped.")
    except Exception:
        log.exception("Fatal error — exiting (launchd will restart).")
        raise


if __name__ == "__main__":
    main()
