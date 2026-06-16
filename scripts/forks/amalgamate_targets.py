#!/usr/bin/env python3
"""Run gadget amalgamation for one target or all configured targets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_AGENTS = ["ed", "edd", "eddy", "guy"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_gizmo_targets(root: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    examples = root / "examples" / "gizmos"
    if not examples.exists():
        return out
    for path in sorted(examples.glob("*.gizmo.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"failed to read {path}: {exc}") from exc
        gizmo = data.get("name")
        gadgets = data.get("gadgets")
        if not isinstance(gizmo, str) or not gizmo:
            raise RuntimeError(f"{path}: missing non-empty name")
        if not isinstance(gadgets, dict):
            raise RuntimeError(f"{path}: missing gadgets object")
        for gadget in sorted(gadgets):
            out.append((gizmo, gadget))
    return out


def run(cmd: list[str], root: Path) -> None:
    print("> " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(root), text=True)
    if proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(cmd))


def amalgamate_target(root: Path, gizmo: str, gadget: str, agents: list[str]) -> None:
    run([
        sys.executable,
        "scripts/forks/amalgamate_all.py",
        "--gadget",
        gizmo,
        gadget,
        "--agents",
        *agents,
        "--apply",
    ], root)
    run([sys.executable, "scripts/forks/gadget_branches.py", "status", gizmo, gadget], root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="amalgamate")
    parser.add_argument("gizmo", nargs="?")
    parser.add_argument("gadget", nargs="?")
    parser.add_argument("--agents", nargs="+", default=list(DEFAULT_AGENTS))
    parser.add_argument("--all", action="store_true", help="amalgamate every configured gizmo/gadget target")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        run(["git", "fetch", "origin", "--prune"], root)
        if args.gizmo or args.gadget:
            if not args.gizmo or not args.gadget:
                raise RuntimeError("provide both gizmo and gadget, or provide neither for all targets")
            targets = [(args.gizmo, args.gadget)]
        else:
            targets = load_gizmo_targets(root)
        if not targets:
            raise RuntimeError("no configured gadget targets found")
        print("amalgamation targets:")
        for gizmo, gadget in targets:
            print(f"  {gizmo}/{gadget}")
        for gizmo, gadget in targets:
            print(f"amalgamate {gizmo}/{gadget} start")
            amalgamate_target(root, gizmo, gadget, args.agents)
        print("amalgamate complete")
        return 0
    except Exception as exc:
        print(f"amalgamate: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
