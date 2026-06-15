#!/usr/bin/env python3
"""Decode a base64 image fixture into a binary file."""

from __future__ import annotations

import base64
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: decode_fixture.py input.png.b64 output.png", file=sys.stderr)
        return 1
    src = Path(argv[0])
    dst = Path(argv[1])
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(src.read_text(encoding="ascii"))
    dst.write_bytes(data)
    print(f"wrote {dst} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
