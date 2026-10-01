"""Health check:  python -m bot.doctor

Verifies .env, Telegram, Playwright, and runs every enabled scraper once.
"""

from .browser import Browser
from .config import ROOT, env, load_config
from .main import needs_browser
from .scrapers import ALL_SCRAPERS


def check(label: str, ok: bool, extra: str = ""):
    print(f"  {'✓' if ok else '✗'} {label}" + (f" — {extra}" if extra else ""))
    return ok


def main():
    print("=== Apartment bot doctor ===\n")
    cfg = load_config()

    print("[1] Configuration")
    check(".env exists", (ROOT / ".env").exists(), "if not: python -m bot.wizard")
    for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "FULL_NAME", "EMAIL", "PHONE"):
        check(var, bool(env(var)))

    print("\n[2] Telegram")
    try:
        from .telegram import Telegram
        Telegram().send("🩺 Doctor test: Telegram is working.")
        check("test message sent", True)
    except Exception as e:
        check("test message sent", False, str(e))

    print("\n[3] Browser")
    browser = None
    browser_ctx = None
    if not needs_browser(cfg):
        print("  - not needed (link-only mode, no login)")
    else:
        try:
            browser_ctx = Browser(headless=cfg.get("headless", True))
            browser = browser_ctx.__enter__()
            check(f"{browser.engine} starts", True)
        except Exception as e:
            check("browser starts", False, f"{e} — fix: playwright install chromium")

    print("\n[4] Scrapers (one trial run each)")
    for name, scraper_cls in ALL_SCRAPERS.items():
        pconf = cfg["platforms"].get(name) or {}
        if not pconf.get("enabled"):
            print(f"  - {name}: disabled")
            continue
        try:
            listings = scraper_cls(cfg).fetch(browser)
            check(name, True, f"{len(listings)} listings found")
        except Exception as e:
            check(name, False, f"{type(e).__name__}: {e}")

    if browser_ctx is not None:
        browser_ctx.__exit__(None, None, None)

    print("\nDone. If everything is ✓: ./run.sh")


if __name__ == "__main__":
    main()
