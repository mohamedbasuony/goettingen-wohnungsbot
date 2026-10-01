#!/bin/bash
# Bot starten:  ./run.sh
cd "$(dirname "$0")"
source .venv/bin/activate
# caffeinate keeps the Mac awake while the bot runs:
#   -d display, -i idle system, -m disk, -s system (on AC), -u user-active.
# NOTE: a closed laptop lid still sleeps regardless — keep the lid OPEN and,
# ideally, the Mac plugged in. For true 24/7, see README (pmset / always-on host).
exec caffeinate -dimsu python -m bot.main
