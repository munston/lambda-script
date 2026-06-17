#!/usr/bin/env python3
"""Create a target-specific onepush/land batch-button pair.

The target definition is supplied once:

    create-targeted-onepush.bat <agent> <gizmo> <gadget> <source-dir> <dest-path>

The visible button name is derived from that tuple. For a self-named gadget
such as lambda-script/lambda-script and agent edd, this creates:

    onepush-lambda-script-edd.bat
    land-lambda-script-edd.bat

For a distinct gizmo/gadget pair such as metrics/text-metrics and agent guy,
this creates:

    onepush-metrics-text-metrics-guy.bat
    land-metrics-text-metrics-guy.bat
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import forks

VALID_AGENTS = set(forks.AGENTS)


def safe_component(kind: str, raw: str) -> str:
    value = (raw or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise RuntimeError(
            f"{kind} must contain only letters, numbers, dot, underscore, or dash, "
            "and must not be empty"
        )
    return value


def button_name(agent: str, gizmo: str, gadget: str) -> str:
    if gizmo == gadget:
        return f"{gadget}-{agent}"
    return f"{gizmo}-{gadget}-{agent}"


def quote_bat(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def gadget_target_ref(gizmo: str, gadget: str) -> str:
    return f"origin/gadgets/{gizmo}/{gadget}/main"


def gadget_lane_ref(gizmo: str, gadget: str, agent: str) -> str:
    return f"gadget-agents/{gizmo}/{gadget}/{agent}"


def write_onepush(root: Path, name: str, agent: str, gizmo: str, gadget: str, source: str, dest: str) -> Path:
    path = root / f"onepush-{name}.bat"
    content = "\r\n".join([
        "@echo off",
        "setlocal",
        "cd /d \"%~dp0\"",
        "python scripts\\forks\\onepush_agent.py "
        + " ".join([
            quote_bat(agent),
            quote_bat(gizmo),
            quote_bat(gadget),
            quote_bat(source),
            quote_bat(dest),
            "%*",
        ]),
        "exit /b %ERRORLEVEL%",
        "",
    ])
    path.write_text(content, encoding="utf-8", newline="")
    return path


def write_land(root: Path, name: str, agent: str, gizmo: str, gadget: str) -> Path:
    path = root / f"land-{name}.bat"
    target_ref = gadget_target_ref(gizmo, gadget)
    lane_ref = gadget_lane_ref(gizmo, gadget, agent)
    content = "\r\n".join([
        "@echo off",
        "setlocal",
        "cd /d \"%~dp0\"",
        "if \"%~1\"==\"\" (",
        f"  echo usage: land-{name}.bat ^<patch.json^>",
        "  exit /b 2",
        ")",
        "python scripts\\forks\\land_json_patch.py "
        + " ".join([
            "--require-file",
            "--target-ref",
            quote_bat(target_ref),
            "--push-ref",
            quote_bat(lane_ref),
            "--no-sync",
            quote_bat(agent),
            "\"%~1\"",
        ]),
        "exit /b %ERRORLEVEL%",
        "",
    ])
    path.write_text(content, encoding="utf-8", newline="")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create-targeted-onepush",
        description="Create onepush-<target>.bat and land-<target>.bat from agent/gizmo/gadget/source/dest.",
    )
    parser.add_argument("agent", help="ed, edd, eddy, or guy")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("source", help="normal source folder hardcoded into the onepush button")
    parser.add_argument("dest", help="destination path inside the gadget branch")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = forks.repo_root()
    agent = forks.normalize_agent(args.agent)
    if agent not in VALID_AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of {', '.join(forks.AGENTS)}")
    gizmo = safe_component("gizmo", args.gizmo)
    gadget = safe_component("gadget", args.gadget)
    source = str(Path(args.source).expanduser().resolve())
    dest = args.dest.replace("\\", "/").strip("/")
    if not dest:
        raise RuntimeError("destination path is empty")

    name = button_name(agent, gizmo, gadget)
    onepush = write_onepush(root, name, agent, gizmo, gadget, source, dest)
    land = write_land(root, name, agent, gizmo, gadget)

    print(f"created {onepush.name}")
    print(f"created {land.name}")
    print("runtime controls:")
    print(f"  {onepush.name}")
    print(f"  {onepush.name} --ship")
    print(f"  {onepush.name} --init-from-dir <directory>")
    print(f"  {onepush.name} --ship --init-from-dir <directory>")
    print(f"  {land.name} <patch.json>")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"create-targeted-onepush: {exc}", file=sys.stderr)
        raise SystemExit(1)
