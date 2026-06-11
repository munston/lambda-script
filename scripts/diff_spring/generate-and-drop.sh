#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 \"commit message\""
  exit 1
fi

MSG="$1"
TIMESTAMP=$(date +'%Y%m%dT%H%M%S')
DROP_DIR="spring/diff/drop"
TMP_DIR="$(mktemp -d)"
JSON_TMP="$TMP_DIR/patch-${TIMESTAMP}.json"
JSON_FINAL="$DROP_DIR/patch-${TIMESTAMP}.json"

mkdir -p "$DROP_DIR"

python scripts/diff_spring/generate-json-patch.py "$MSG" > "$JSON_TMP"

mv "$JSON_TMP" "$JSON_FINAL"
rmdir "$TMP_DIR" 2>/dev/null || true

echo "✅ Generated valid patch:"
echo "   $JSON_FINAL"
echo "Now run: bash scripts/diff_spring/absorb-and-ship.sh"
