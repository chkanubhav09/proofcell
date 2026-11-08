#!/usr/bin/env bash
# Render deck/deck.html to deck/proofcell-deck.pdf (8 slides, 1280x720 each).
set -euo pipefail
cd "$(dirname "$0")/.."
google-chrome --headless --disable-gpu --no-sandbox \
  --print-to-pdf=deck/proofcell-deck.pdf --no-pdf-header-footer \
  "file://$PWD/deck/deck.html"
echo "wrote deck/proofcell-deck.pdf"
