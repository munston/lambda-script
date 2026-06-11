#!/usr/bin/env bash
set -euo pipefail

cmd.exe //c pull.bat

message="$(python scripts/diff_spring/absorb_json.py --message-only)"

python scripts/diff_spring/absorb_json.py --list
python scripts/diff_spring/absorb_json.py
python scripts/test/verify-interface.py

cmd.exe //c push.bat "$message"
