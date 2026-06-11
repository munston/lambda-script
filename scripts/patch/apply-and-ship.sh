#!/usr/bin/env bash
set -euo pipefail

patch_file="${1:-}"

if [ -z "$patch_file" ]; then
  echo "usage: bash scripts/patch/apply-and-ship.sh PATCH_FILE" >&2
  exit 2
fi

if [ ! -f "$patch_file" ]; then
  echo "missing patch file: $patch_file" >&2
  exit 1
fi

cmd.exe //c pull.bat

message="$(python scripts/patch/apply_patch.py --message "$patch_file")"

python scripts/patch/apply_patch.py --check "$patch_file"
python scripts/patch/apply_patch.py "$patch_file"
python scripts/test/verify-interface.py

cmd.exe //c push.bat "$message"
