#!/usr/bin/env python3
"""Run gadget amalgamation for one target or all initialized configured targets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_AGENTS = ["ed", "edd", "eddy", "guy"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_capture(cmd: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(cmd) + "\n" + proc.stdout + proc.stderr)
    return proc


def run(cmd: list[str], root: Path) -> None:
    print("> " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(root), text=True)
    if proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(cmd))


def ref_exists(root: Path, ref: str) -> bool:
    proc = run_capture(["git", "rev-parse", "--verify", "--quiet", ref], root, check=False)
    return proc.returncode == 0


def integration_ref(gizmo: str, gadget: str) -> str:
    return f"origin/gadgets/{gizmo}/{gadget}/main"


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


def initialized_targets(root: Path, targets: list[tuple[str, str]], *, include_uninitialized: bool) -> list[tuple[str, str]]:
    if include_uninitialized:
        return targets
    kept: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    for gizmo, gadget in targets:
        if ref_exists(root, integration_ref(gizmo, gadget)):
            kept.append((gizmo, gadget))
        else:
            skipped.append((gizmo, gadget))
    if skipped:
        print("skipping uninitialized gadget target(s):")
        for gizmo, gadget in skipped:
            print(f"  {gizmo}/{gadget} missing {integration_ref(gizmo, gadget)}")
        print("initialize a skipped target before amalgamating it, or pass --include-uninitialized to fail loudly")
    return kept


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
    parser.add_argument("--all", action="store_true", help="amalgamate every initialized configured gizmo/gadget target")
    parser.add_argument("--include-uninitialized", action="store_true", help="do not skip configured targets whose integration branch is missing")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        run(["git", "fetch", "origin", "--prune"], root)
        if args.gizmo or args.gadget:
            if not args.gizmo or not args.gadget:
                raise RuntimeError("provide both gizmo and gadget, or provide neither for all initialized targets")
            targets = [(args.gizmo, args.gadget)]
            if not args.include_uninitialized and not ref_exists(root, integration_ref(args.gizmo, args.gadget)):
                raise RuntimeError(f"missing gadget integration ref: {integration_ref(args.gizmo, args.gadget)}")
        else:
            targets = initialized_targets(root, load_gizmo_targets(root), include_uninitialized=args.include_uninitialized)
        if not targets:
            raise RuntimeError("no initialized gadget targets found")
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
