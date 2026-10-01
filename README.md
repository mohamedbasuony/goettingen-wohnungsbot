# 🏠 Göttingen Wohnungsbot

A bot that scans for **3-Zimmer apartments in Göttingen** across the major German
rental platforms and pings you on Telegram. Two speeds:

- **Kleinanzeigen** — scanned **every 30 seconds**, and it **auto-sends your German
  viewing request** to every new matching ad (needs a one-time login).
- **All other platforms** — scanned **every 5 minutes**, **links only** (no login).

> **Why 3 Zimmer?** In Germany the living room counts as a room. An apartment with
> 2 bedrooms + living room + kitchen + bathroom is a **3-Zimmer-Wohnung**.
> The filter is set to 3–3.5 Zimmer in [config.yaml](config.yaml).

> ⚠️ **Account risk.** Scanning Kleinanzeigen every 30s *and* auto-messaging is
> aggressive — it's the behaviour most likely to get the account flagged/banned by
> their bot-detection. Dial `kleinanzeigen_interval_seconds` up to 60–90 in
> [config.yaml](config.yaml) if you want to play it safer. A per-hour message cap
> (`contact.max_per_hour`) is on by default as a brake.

## Platforms covered

| Platform | Status | Notes |
|---|---|---|
| Kleinanzeigen.de | ✅ 30s + **auto-message** | logs in, messages every new match |
| Immowelt | ✅ 5 min, links only | big portal, lots of listings |
| WG-Gesucht | ✅ 5 min, links only | whole-flat listings |
| Volksheimstätte eG | ✅ 5 min, links only | local co-op, first-come-first-served |
| Wohnungsgenossenschaft eG | ✅ 5 min, links only | local co-op |
| Vonovia | ✅ 5 min, links only | Germany's biggest landlord |
| ImmobilienScout24 | ⏸️ off | behind a bot-wall a headless browser can't pass |
| Städtische Wohnungsbau (SWB) | ❌ n/a | no online listings — see below |

> **ImmoScout24 is off by default.** Its "Ich bin kein Roboter" wall blocks headless
> browsers. To include it anyway, set `immoscout24 enabled: true` **and**
> `headless: false` in [config.yaml](config.yaml) — a Chrome window will then be
> visible while it scans. Most people leave it off; the other platforms cover plenty.

> **SWB Göttingen has no online listings.** They allocate from a registered applicant
> pool. Do this ONCE, by hand: download the "Fragebogen für Wohnungsinteressenten" from
> [swb-goettingen.de](https://www.swb-goettingen.de/deutsch/wohnen/mieten/index.html)
> and submit it (Vermietungsteam: 0551 / 4967-20).

---

## Setup (5 minutes)

### 0. Prerequisites
- macOS with Python 3.10+ (`python3 --version`)
- A Telegram account

### 1. Install
```bash
cd ~/goettingen-wohnungsbot
./install.sh
source .venv/bin/activate
```

### 2. Connect Telegram & choose what to search for
1. In Telegram, open **@BotFather** → send `/newbot` → pick a name → copy the **token**.
2. Run the wizard — it takes the token, auto-detects your chat id, sends a test message,
   and asks **what to search for in Göttingen**:
```bash
python -m bot.wizard
```
It asks three things about the search:
- **Rooms (Zimmer):** `3` (exactly 3), `3-3.5` (a range), `2-4`, or `3+`. German counting —
  the living room counts, so a 2-bedroom + living room flat is a **3-Zimmer**.
- **Postal codes:** limit to specific Göttingen PLZ (e.g. `37073,37083`), or leave blank for
  all of Göttingen. PLZ: `37073 37075 37077 37079 37081 37083 37085`.
- Your name / email / phone (used only to fill contact-form fields).

(The wizard writes these to `.env`; they override the defaults in [config.yaml](config.yaml).)

### 3. Kleinanzeigen auto-messaging (login once)
```bash
python -m bot.credentials   # enter Kleinanzeigen email + password (password hidden)
./login.sh                  # opens Chrome; YOU solve the "human" checkbox and log in
```
`login.sh` stops the bot, opens the login window, and restarts the bot afterward — so
the browser profile isn't locked. Re-run it whenever the session expires. The session
is saved in `data/browser-profile` and reused (also headless).
*(The other platforms are links-only and need none of this.)*

### 4. Run automatically at login (recommended, macOS)
```bash
./install-autostart.sh
```
This installs a launchd agent (filling in your path automatically) so the bot starts
with your Mac and restarts itself if it crashes.
Stop it with `launchctl unload ~/Library/LaunchAgents/com.wohnungsbot.goettingen.plist`.
The **first run per platform is a baseline** (records what's already listed; never
auto-messages the backlog). After that, every **new** match is sent — and new
Kleinanzeigen matches are messaged automatically.

---

## Daily operations

**What a Telegram notification looks like:**
```
🏠 Moderne 3-Zimmer-Wohnung mit Terrasse in Göttingen
🌐 New apartment — Kleinanzeigen
📍 37083 Göttingen
🚪 Rooms: 3
📐 82 m²
💶 1.440 €
🔗 https://www.kleinanzeigen.de/s-anzeige/...
✉️ Contact request: sent ✓
```
For Kleinanzeigen the `✉️ Contact request` line tells you whether the auto-message went
out (`sent ✓`, `not logged in`, `skipped (limit reached)`, or `unconfirmed`). For the
other platforms there's no contact line — tap the link and apply yourself.

**Change rooms or postal codes later:** just re-run `python -m bot.wizard` (fastest), or
edit `.env` (`SEARCH_ROOMS`, `SEARCH_POSTAL_CODES`), then restart.

> **PLZ filter note:** it works where the platform shows a postal code — Kleinanzeigen,
> Immowelt, Vonovia. WG-Gesucht shows districts (e.g. "Geismar") not PLZ, so those listings
> come through regardless of the postal filter.

**Other tuning** (edit [config.yaml](config.yaml), then restart):
- `filters.max_rent_cold: 900` — cap the cold rent
- `poll_interval_seconds: 180` — check other platforms more often (don't go below ~120)
- `platforms.<name>.enabled: false` — turn a platform off

**Check it's working:**
```bash
python -m bot.doctor      # tests Telegram + runs each enabled scraper once
```

**Logs:** `tail -f data/bot.log` · **Database:** `data/listings.db` (delete it to re-baseline)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No Telegram messages | Run `python -m bot.doctor`; check the token/chat id in `.env`. Remember the **first run is a baseline** — new messages only start on genuinely new listings. |
| Kleinanzeigen: `not logged in` on the contact line | Session expired or never set. Run `./login.sh` and log in again. |
| Kleinanzeigen login checkbox won't clear / keeps flagging | It's their bot-detection. Move the mouse slowly, pause before ticking. If it persists, wait ~30 min and try `./login.sh` again; auto-messaging stays off until login succeeds (you still get the links). |
| Want to see it found something now | `python -m bot.doctor` prints how many listings each platform returns. |
| A platform suddenly finds 0 ads | The site changed its HTML. Check `data/bot.log`; selectors live in `bot/scrapers/<platform>.py`. |
| Too many / too few results | Re-run `python -m bot.wizard` to change rooms/postal codes, or edit `SEARCH_ROOMS` / `SEARCH_POSTAL_CODES` in `.env`; `max_rent_cold` lives in config.yaml. |
| Long gaps between scans / "quiet for hours" | Your Mac is sleeping — the bot freezes while asleep. `run.sh` runs `caffeinate -dimsu`, but a **closed lid still sleeps**. Keep the lid **open** and plugged in. To force it, run once: `sudo pmset -a disablesleep 1` (undo with `sudo pmset -a disablesleep 0`). For real 24/7 without tying up your Mac, run it on an always-on box — but prefer your home connection, since datacenter IPs get blocked by some portals. |
| "Only got one notification" | Telegram groups messages that arrive within seconds into one banner. All the individual apartment links are in the chat — scroll up. After the first batch you're only pinged on genuinely new matches. |
| Want ImmoScout24 too | Set `immoscout24 enabled: true` and `headless: false` in config.yaml (a visible Chrome window will scan it). |

## Notes

- Most platforms are **read-only** (scan + link). **Kleinanzeigen is different**: the
  bot logs into your account and auto-sends your message to new matches. That plus the
  30s scan cadence violates Kleinanzeigen's terms and carries a real risk of the
  account being flagged or banned — that risk is yours. Dial the interval up and keep
  `contact.max_per_hour` modest to reduce it.
- Watch your Kleinanzeigen inbox and reply fast when a landlord answers — the bot gets
  you in early; a quick, human follow-up wins the viewing.
