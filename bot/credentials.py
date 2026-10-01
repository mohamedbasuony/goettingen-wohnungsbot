"""Store your Kleinanzeigen login in .env:  python -m bot.credentials

The password is read with a hidden prompt and written only to the local
.env file (which is gitignored). It is never printed or committed.
"""

import getpass

from .config import ROOT, env

KEYS = ("KLEINANZEIGEN_EMAIL", "KLEINANZEIGEN_PASSWORD")


def _write_env(updates: dict):
    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, val in updates.items():
        if key not in seen:
            out.append(f"{key}={val}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    print("=== Kleinanzeigen credentials ===")
    print("Stored only in the local .env file (gitignored). Never printed.\n")
    default_email = env("KLEINANZEIGEN_EMAIL", "")
    prompt = f"Kleinanzeigen email [{default_email}]: " if default_email else "Kleinanzeigen email: "
    email = input(prompt).strip() or default_email
    password = getpass.getpass("Kleinanzeigen password (hidden): ").strip()
    if not email or not password:
        raise SystemExit("Both email and password are required. Nothing saved.")
    _write_env({"KLEINANZEIGEN_EMAIL": email, "KLEINANZEIGEN_PASSWORD": password})
    print("\n✓ Saved to .env.")
    print("Next: run `python -m bot.login` once to establish the session (solve the captcha by hand).")


if __name__ == "__main__":
    main()
