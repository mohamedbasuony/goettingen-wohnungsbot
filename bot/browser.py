"""Shared browser with a persistent profile.

One profile directory holds the logins for all platforms: run
`python -m bot.login` once, sign in by hand, and every future
(headless) run reuses those sessions and cookies.

We prefer **patchright** over vanilla Playwright: it removes the
`Runtime.enable` CDP leak that anti-bot systems (e.g. the "Bestätigen Sie,
dass Sie ein Mensch sind" check on Kleinanzeigen) use to detect automation —
which is the real reason such a checkbox refuses to validate. Patchright
manages its own stealth flags, so we deliberately do NOT inject
webdriver/plugin spoofs (those are detectable and can make things worse).
"""

from .config import DATA_DIR

PROFILE_DIR = DATA_DIR / "browser-profile"
FAILURE_DIR = DATA_DIR / "failures"

# Fallback-only stealth (used if patchright isn't available).
_FALLBACK_STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"


def _load_engine():
    """Return (sync_playwright, is_patchright)."""
    try:
        from patchright.sync_api import sync_playwright
        return sync_playwright, True
    except Exception:
        from playwright.sync_api import sync_playwright
        return sync_playwright, False


class Browser:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self.context = None
        self.engine = None  # "patchright" or "playwright"

    def __enter__(self):
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        sync_playwright, is_patchright = _load_engine()
        self.engine = "patchright" if is_patchright else "playwright"
        self._pw = sync_playwright().start()

        if is_patchright:
            # Patchright best practice: real Chrome, NO explicit viewport
            # (no_viewport avoids a fingerprint mismatch), NO extra args/flags —
            # patchright owns the anti-detection.
            options = dict(
                headless=self.headless,
                locale="de-DE",
                timezone_id="Europe/Berlin",
                no_viewport=True,
            )
        else:
            options = dict(
                headless=self.headless,
                locale="de-DE",
                timezone_id="Europe/Berlin",
                viewport={"width": 1440, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )

        try:
            # Real Google Chrome passes bot checks far more often than bundled Chromium.
            self.context = self._pw.chromium.launch_persistent_context(
                str(PROFILE_DIR), channel="chrome", **options)
        except Exception:
            self.context = self._pw.chromium.launch_persistent_context(
                str(PROFILE_DIR), **options)

        if not is_patchright:
            self.context.add_init_script(_FALLBACK_STEALTH_JS)
        return self

    def __exit__(self, *exc):
        try:
            self.context.close()
        finally:
            self._pw.stop()

    def page(self):
        page = self.context.new_page()
        page.set_default_timeout(20000)
        return page

    def screenshot_failure(self, page, name: str) -> str:
        FAILURE_DIR.mkdir(parents=True, exist_ok=True)
        path = FAILURE_DIR / f"{name}.png"
        try:
            page.screenshot(path=str(path), full_page=True)
        except Exception:
            pass
        return str(path)
