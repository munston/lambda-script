#!/usr/bin/env python3
"""Target-backed onepush button implementation.

The generated onepush button hardcodes agent, gizmo, gadget, source directory,
and destination path. Runtime users get only two controls:

    --ship
    --init-from-dir <directory>

Plain invocation submits the hardcoded folder to the hardcoded lane.  --ship
ships the current lane without re-submitting the hardcoded folder.  If
--init-from-dir is supplied, that directory is submitted first; with --ship it
is then shipped in the same call.
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
    parser.add_argument("--ship", action="store_true", help="amalgamate and sync the current lane")
    parser.add_argument("--init-from-dir", metavar="DIR", help="initialise/submit from DIR before optional shipping")
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


def require_source(path_text: str) -> Path:
    source = Path(path_text).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        raise RuntimeError(f"source folder does not exist: {source}")
    return source


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    args.agent = forks.normalize_agent(args.agent)
    if args.agent not in forks.AGENTS:
        raise RuntimeError(f"unsupported agent {args.agent!r}; expected one of {', '.join(forks.AGENTS)}")
    root = forks.repo_root()

    submit_before_ship = bool(args.init_from_dir) or not args.ship
    source = require_source(args.init_from_dir or args.source) if submit_before_ship else None

    print(f"onepush {args.agent} {args.gizmo}/{args.gadget}")
    if source is None:
        print("  source: <not submitted during --ship>")
    else:
        print(f"  source: {source}")
    print(f"  dest: {args.dest}")
    print(f"  initialise: {'yes' if args.init_from_dir else 'no'}")
    print(f"  ship: {'yes' if args.ship else 'no'}")

    if submit_before_ship:
        code = ingest(root, args, source, initialise=bool(args.init_from_dir))
        if code != 0:
            print("ship: skipped because lane submission failed.")
            return code
        if not args.ship:
            print("done: lane submitted; ship omitted.")
            return 0
    else:
        print("lane submission: skipped; shipping existing lane.")

    code = ship(root, args)
    if code == 0:
        if submit_before_ship:
            print("done: submitted, shipped, and synced.")
        else:
            print("done: shipped and synced.")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"onepush: {exc}", file=sys.stderr)
        raise SystemExit(1)
