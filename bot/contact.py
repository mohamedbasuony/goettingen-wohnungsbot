"""Automatische Besichtigungsanfrage auf Deutsch, direkt beim Inserenten.

Läuft über den persistenten Browser (data/browser-profile), d.h. mit deinen
echten Logins. Jeder Versuch endet mit einem Status, der 1:1 in die
Telegram-Nachricht wandert. Bei Unklarheit wird ein Screenshot unter
data/failures/ abgelegt, damit du nachvollziehen kannst, was passiert ist.
"""

import re

from .config import profile
from .models import Listing

SUCCESS_RE = re.compile(
    r"(nachricht\s+(wurde\s+)?gesendet|erfolgreich\s+(ge)?sendet|anfrage\s+(wurde\s+)?"
    r"(ge)?sendet|vielen\s+dank|danke\s+für\s+(deine|ihre)\s+(nachricht|anfrage))",
    re.IGNORECASE,
)

COOKIE_BUTTONS = [
    "#gdpr-banner-accept",
    "[data-testid='uc-accept-all-button']",
    "button:has-text('Alle akzeptieren')",
    "button:has-text('Alles akzeptieren')",
    "button:has-text('Akzeptieren')",
]


def _accept_cookies(page):
    for sel in COOKIE_BUTTONS:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                loc.click(timeout=3000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def _click_first(page, selectors) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                loc.click(timeout=5000)
                page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


def _fill_if_empty(page, selectors, value):
    if not value:
        return
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible() and not loc.input_value():
                loc.fill(value)
                return
        except Exception:
            continue


def _fill_personal_fields(page):
    p = profile()
    _fill_if_empty(page, ["input[type='email']", "input[name*='mail' i]"], p["email"])
    _fill_if_empty(page, ["input[type='tel']", "input[name*='phone' i]",
                          "input[name*='telefon' i]"], p["phone"])
    _fill_if_empty(page, ["input[name*='name' i]:not([name*='user' i])"], p["full_name"])


def _finish(browser, page, listing: Listing) -> str:
    page.wait_for_timeout(3500)
    try:
        body = page.inner_text("body")
    except Exception:
        body = ""
    if SUCCESS_RE.search(body):
        return "sent ✓"
    shot = browser.screenshot_failure(page, f"{listing.platform}-{listing.listing_id}")
    return f"unconfirmed — please check the ad yourself (screenshot: {shot})"


# ---------------------------------------------------------------- Kleinanzeigen

def contact_kleinanzeigen(browser, listing: Listing, message: str) -> str:
    page = browser.page()
    try:
        page.goto(listing.url, wait_until="domcontentloaded")
        _accept_cookies(page)

        textarea = page.locator("#viewad-contact-message")
        if not (textarea.count() and textarea.is_visible()):
            _click_first(page, [
                "#viewad-contact-button-login-modal",
                ".viewad-contact-button-login",
                "button:has-text('Nachricht schreiben')",
            ])
        if "einloggen" in page.url or page.locator("input[name='loginMail']").count():
            return "not logged in — please run `python -m bot.login` (Kleinanzeigen)"

        textarea = page.locator("#viewad-contact-message")
        textarea.wait_for(state="visible", timeout=10000)
        textarea.fill(message)
        _fill_if_empty(page, ["#contact-contactName-input"], profile()["full_name"])
        _fill_if_empty(page, ["#contact-phoneNumber-input"], profile()["phone"])
        if not _click_first(page, ["button.viewad-contact-submit",
                                   "button:has-text('Nachricht senden')"]):
            raise RuntimeError("send button not found")
        return _finish(browser, page, listing)
    finally:
        page.close()


# ------------------------------------------------- generisches Kontaktformular

def _generic_contact(browser, listing: Listing, message: str,
                     triggers: list[str], login_marker: str) -> str:
    page = browser.page()
    try:
        page.goto(listing.url, wait_until="domcontentloaded")
        _accept_cookies(page)
        _click_first(page, triggers)

        if login_marker and login_marker in page.url:
            return f"not logged in — please run `python -m bot.login` ({listing.platform})"

        filled = False
        for sel in ["textarea[name*='message' i]", "textarea[name*='nachricht' i]", "textarea"]:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible():
                    loc.fill(message)
                    filled = True
                    break
            except Exception:
                continue
        if not filled:
            shot = browser.screenshot_failure(page, f"{listing.platform}-{listing.listing_id}")
            return f"contact form not found — please contact manually (screenshot: {shot})"

        _fill_personal_fields(page)
        if not _click_first(page, [
            "button:has-text('Nachricht senden')",
            "button:has-text('Anfrage senden')",
            "button:has-text('Senden')",
            "button[type='submit']",
        ]):
            shot = browser.screenshot_failure(page, f"{listing.platform}-{listing.listing_id}")
            return f"send button not found (screenshot: {shot})"
        return _finish(browser, page, listing)
    finally:
        page.close()


def contact_immoscout24(browser, listing: Listing, message: str) -> str:
    return _generic_contact(browser, listing, message, triggers=[
        "button:has-text('Anbieter kontaktieren')",
        "a:has-text('Anbieter kontaktieren')",
        "button:has-text('Nachricht')",
        "[data-qa='contactButton']",
    ], login_marker="sso.immobilienscout24.de")


def contact_immowelt(browser, listing: Listing, message: str) -> str:
    return _generic_contact(browser, listing, message, triggers=[
        "button:has-text('Nachricht senden')",
        "button:has-text('Anbieter kontaktieren')",
        "button:has-text('Kontaktieren')",
        "a:has-text('Kontakt')",
    ], login_marker="")


HANDLERS = {
    "kleinanzeigen": contact_kleinanzeigen,
    "immoscout24": contact_immoscout24,
    "immowelt": contact_immowelt,
}
