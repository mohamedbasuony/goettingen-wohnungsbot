#!/bin/bash
# Einmalige Installation. Ausführen mit:  ./install.sh
set -e
cd "$(dirname "$0")"

echo "==> Python-Umgebung anlegen..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> Abhängigkeiten installieren..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "==> Browser für Playwright installieren (einmalig, ~150 MB)..."
python -m playwright install chromium

echo ""
echo "✓ Installation fertig. Jetzt einrichten mit:"
echo "    source .venv/bin/activate"
echo "    python -m bot.wizard"
