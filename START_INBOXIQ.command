#!/bin/bash
set -e
cd "$(dirname "$0")"

echo ""
echo "=============================================="
echo "        InboxIQ — Gmail Edition"
echo "=============================================="
echo ""

PYTHON="python3"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python 3 is not installed."
  echo "Install Python 3 from https://www.python.org/downloads/"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

echo "Installing/checking Python packages..."
"$PYTHON" -m pip install -r requirements.txt

echo ""
echo "Starting InboxIQ..."
echo "Open http://127.0.0.1:5000 in your browser."
echo "Press Ctrl+C in this window to stop InboxIQ."
echo ""
"$PYTHON" app.py
