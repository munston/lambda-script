#!/usr/bin/env python3
"""Create a target-specific onepush batch button.

The generated button hardcodes all target information:

    agent, gizmo, gadget, source directory, destination path

At runtime the generated button accepts only:

    --ship
    --init-from-dir <directory>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import forks


VALID_AGENTS = set(forks.AGENTS)


def safe_name(raw: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", raw or ""):
        raise RuntimeError("button name must contain only letters, numbers, dot, underscore, or dash, and must not be empty")
    return raw


def quote_bat(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create-targeted-onepush",
        description="Create onepush-<name>.bat with hardcoded agent/gizmo/gadget/source/dest.",
    )
    parser.add_argument("name", help="button name; creates onepush-<name>.bat")
    parser.add_argument("agent", help="ed, edd, eddy, or guy")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("source", help="normal source folder for this button")
    parser.add_argument("dest", help="destination path inside the gadget branch")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = forks.repo_root()
    name = safe_name(args.name)
    agent = forks.normalize_agent(args.agent)
    if agent not in VALID_AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of {', '.join(forks.AGENTS)}")
    source = str(Path(args.source).expanduser().resolve())
    dest = args.dest.replace("\\", "/").strip("/")
    if not dest:
        raise RuntimeError("destination path is empty")

    path = root / f"onepush-{name}.bat"
    content = "\r\n".join([
        "@echo off",
        "setlocal",
        "cd /d \"%~dp0\"",
        "python scripts\\forks\\onepush_agent.py "
        + " ".join([
            quote_bat(agent),
            quote_bat(args.gizmo),
            quote_bat(args.gadget),
            quote_bat(source),
            quote_bat(dest),
            "%*",
        ]),
        "exit /b %ERRORLEVEL%",
        "",
    ])
    path.write_text(content, encoding="utf-8", newline="")
    print(f"created {path.name}")
    print("runtime controls:")
    print(f"  {path.name}")
    print(f"  {path.name} --ship")
    print(f"  {path.name} --init-from-dir <directory>")
    print(f"  {path.name} --ship --init-from-dir <directory>")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"create-targeted-onepush: {exc}", file=sys.stderr)
        raise SystemExit(1)
