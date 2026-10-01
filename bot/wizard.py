"""Interactive setup:  python -m bot.wizard

Asks for the Telegram token and your personal data, auto-detects your
chat id, sends a test message, and writes the .env file.
"""

import time

import httpx

from .config import ROOT, parse_rooms_spec


def detect_chat_id(token: str) -> str | None:
    print("\nNow open Telegram and send your bot any message (e.g. 'hello').")
    print("Waiting... (up to 60 seconds)")
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            r = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15)
            for upd in reversed(r.json().get("result", [])):
                msg = upd.get("message") or upd.get("channel_post")
                if msg and msg.get("chat"):
                    return str(msg["chat"]["id"])
        except Exception:
            pass
        time.sleep(2)
    return None


def ask(label: str, example: str = "") -> str:
    hint = f" (e.g. {example})" if example else ""
    return input(f"{label}{hint}: ").strip()


def main():
    print("=== Göttingen apartment bot — setup ===\n")
    print("Step 1: Create a bot on Telegram with @BotFather (/newbot)")
    token = ask("Bot token from @BotFather")
    if not token:
        raise SystemExit("Cannot continue without a token. Aborting.")

    chat_id = detect_chat_id(token)
    if chat_id:
        print(f"✓ Chat id found: {chat_id}")
    else:
        chat_id = ask("Could not detect the chat id automatically. Please enter it manually")

    print("\nStep 2: What to search for in Göttingen.")
    print("Rooms (Zimmer, German counting — the living room counts). Examples:")
    print("  3        = exactly 3-Zimmer     3-3.5    = 3 to 3.5     2-4 = 2 up to 4     3+ = 3 or more")
    rooms = ask("Rooms", "3-3.5") or "3-3.5"
    print("\nPostal codes to limit the search to (within Göttingen). Comma-separated.")
    print("  Göttingen PLZ: 37073 37075 37077 37079 37081 37083 37085")
    print("  Leave blank to search ALL of Göttingen.")
    postal = ask("Postal codes (blank = all)", "")

    print("\nStep 3: Your details — used to fill the name/email/phone fields on contact forms.")
    full_name = ask("Full name")
    email = ask("Email")
    phone = ask("Phone number", "+49 151 2345678")
    occupation = ask("Occupation (German)", "Software Engineer mit unbefristetem Vertrag")
    household = ask("One sentence about your household (optional, German)", "")

    env_path = ROOT / ".env"
    env_path.write_text(
        f"TELEGRAM_BOT_TOKEN={token}\n"
        f"TELEGRAM_CHAT_ID={chat_id}\n"
        f"SEARCH_ROOMS={rooms}\n"
        f"SEARCH_POSTAL_CODES={postal}\n"
        f"FULL_NAME={full_name}\n"
        f"EMAIL={email}\n"
        f"PHONE={phone}\n"
        f"OCCUPATION={occupation}\n"
        f"HOUSEHOLD={household}\n",
        encoding="utf-8",
    )
    lo, hi = parse_rooms_spec(rooms)
    where = postal.strip() or "all of Göttingen"
    print(f"\n✓ Saved: {env_path}")
    print(f"  Searching {lo:g}–{hi:g} Zimmer in {where}.")

    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id,
                  "text": "✅ Setup complete! The Göttingen apartment bot is ready to start."},
            timeout=15,
        ).raise_for_status()
        print("✓ Test message sent to Telegram — check your chat.")
    except Exception as e:
        print(f"! Test message failed: {e}")

    print("\nNext steps:")
    print("  1. python -m bot.login    (log in to the platforms once)")
    print("  2. python -m bot.doctor   (test everything)")
    print("  3. ./run.sh               (start the bot)")


if __name__ == "__main__":
    main()
