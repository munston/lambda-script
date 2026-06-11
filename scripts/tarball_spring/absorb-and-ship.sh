#!/usr/bin/env bash
set -euo pipefail

cmd.exe //c pull.bat

message="$(python scripts/tarball_spring/absorb.py --message-only)"

python scripts/tarball_spring/absorb.py --list
python scripts/tarball_spring/absorb.py
python scripts/test/verify-interface.py

cmd.exe //c push.bat "$message"
