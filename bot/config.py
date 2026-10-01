import os
import pathlib

import yaml
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

load_dotenv(ROOT / ".env")


def load_config() -> dict:
    path = ROOT / "config.yaml"
    if not path.exists():
        raise SystemExit("config.yaml is missing. See the README / run install.sh.")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(
            f"Environment variable {name} is missing. Add it to the .env file "
            f"(template: .env.example, or run `python -m bot.wizard`)."
        )
    return value


def parse_rooms_spec(spec: str) -> tuple[float, float]:
    """'3' -> (3,3); '3-3.5' / '3 - 3,5' -> (3,3.5); '2+' -> (2, 99); '' -> (0, 99)."""
    s = (spec or "").replace(",", ".").strip()
    if not s:
        return 0.0, 99.0
    if "-" in s:
        a, b = s.split("-", 1)
        return float(a.strip()), float(b.strip())
    if s.endswith("+"):
        return float(s[:-1].strip()), 99.0
    v = float(s)
    return v, v


def resolve_filters(cfg: dict) -> dict:
    """Effective filters: config.yaml defaults, overridden by what setup wrote to .env
    (SEARCH_ROOMS, SEARCH_POSTAL_CODES)."""
    f = dict(cfg.get("filters") or {})
    rooms = env("SEARCH_ROOMS")
    if rooms:
        f["min_rooms"], f["max_rooms"] = parse_rooms_spec(rooms)
    plz = env("SEARCH_POSTAL_CODES")
    if plz is not None:
        f["postal_codes"] = [p.strip() for p in plz.split(",") if p.strip()]
    f.setdefault("postal_codes", f.get("postal_codes") or [])
    return f


def profile() -> dict:
    """Personal data used to fill the German contact message."""
    return {
        "full_name": env("FULL_NAME", ""),
        "email": env("EMAIL", ""),
        "phone": env("PHONE", ""),
        "occupation": env("OCCUPATION", ""),
        "household": env("HOUSEHOLD", ""),
    }


def kleinanzeigen_credentials() -> tuple[str | None, str | None]:
    """(email, password) for auto-login. Password lives only in .env (gitignored)."""
    return env("KLEINANZEIGEN_EMAIL"), env("KLEINANZEIGEN_PASSWORD")
