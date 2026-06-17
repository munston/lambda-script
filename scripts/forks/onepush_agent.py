#!/usr/bin/env python3
"""Target-backed onepush button implementation.

This script is intentionally used behind generated batch files. The generated
``onepush-<name>.bat`` hardcodes agent, gizmo, gadget, source directory, and
destination path. Runtime users get only two controls:

    --ship
    --init-from-dir <directory>

No target, destination, verifier, replace flag, or message flag is exposed at
button-use time.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import forks
import process_result


def script(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        raise RuntimeError(f"missing required tool: {rel}")
    return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onepush-targeted",
        description="Submit a hardcoded target folder to an agent lane; add --ship to amalgamate and sync.",
    )
    parser.add_argument("agent")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("source")
    parser.add_argument("dest")
    parser.add_argument("--ship", action="store_true", help="after submission, amalgamate and sync")
    parser.add_argument("--init-from-dir", metavar="DIR", help="initialise the target from DIR before normal submission")
    return parser


def ingest(root: Path, args: argparse.Namespace, source: Path, *, initialise: bool) -> int:
    cmd = [
        sys.executable,
        script(root, "scripts/forks/gadget_ingest_folder.py"),
        args.gizmo,
        args.gadget,
        args.agent,
        "--source",
        str(source),
        "--dest",
        args.dest,
        "--message",
        f"onepush {args.gizmo}/{args.gadget}",
        "--replace",
        "--allow-existing-lane-work",
    ]
    if initialise:
        cmd.append("--init-if-missing")
    return process_result.run_step("lane submission", cmd, root)


def ship(root: Path, args: argparse.Namespace) -> int:
    code = process_result.run_step(
        "amalgamation",
        [
            sys.executable,
            script(root, "scripts/forks/gadget_amalgamate_safe.py"),
            "--gadget",
            args.gizmo,
            args.gadget,
            "--agents",
            args.agent,
            "--apply",
        ],
        root,
    )
    if code != 0:
        print("sync: skipped because amalgamation failed.")
        return code
    return process_result.run_step(
        "lane sync",
        [
            sys.executable,
            script(root, "scripts/forks/gadget_branches.py"),
            "sync-all",
            args.gizmo,
            args.gadget,
        ],
        root,
    )


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    args.agent = forks.normalize_agent(args.agent)
    if args.agent not in forks.AGENTS:
        raise RuntimeError(f"unsupported agent {args.agent!r}; expected one of {', '.join(forks.AGENTS)}")
    root = forks.repo_root()
    source = Path(args.init_from_dir or args.source).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        raise RuntimeError(f"source folder does not exist: {source}")

    print(f"onepush {args.agent} {args.gizmo}/{args.gadget}")
    print(f"  source: {source}")
    print(f"  dest: {args.dest}")
    print(f"  initialise: {'yes' if args.init_from_dir else 'no'}")
    print(f"  ship: {'yes' if args.ship else 'no'}")

    code = ingest(root, args, source, initialise=bool(args.init_from_dir))
    if code != 0:
        print("ship: skipped because lane submission failed.")
        return code
    if not args.ship:
        print("done: lane submitted; ship omitted.")
        return 0
    code = ship(root, args)
    if code == 0:
        print("done: submitted, shipped, and synced.")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"onepush: {exc}", file=sys.stderr)
        raise SystemExit(1)
