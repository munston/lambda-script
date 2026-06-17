#!/usr/bin/env python3
"""Target-backed onepush button implementation.

The generated button hardcodes agent, gizmo, gadget, source directory, and
destination path. Runtime users get only two controls:

    --ship
    --init-from-dir <directory>
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


def target_name(agent: str, gizmo: str, gadget: str) -> str:
    if gizmo == gadget:
        return f"{gadget}-{agent}"
    return f"{gizmo}-{gadget}-{agent}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onepush-targeted",
        description="Submit a hardcoded target folder to an agent lane; add --ship to ship the lane.",
    )
    parser.add_argument("agent")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("source")
    parser.add_argument("dest")
    parser.add_argument("--ship", action="store_true", help="ship the existing lane")
    parser.add_argument("--init-from-dir", metavar="DIR", help="initialise and submit from DIR before optional shipping")
    return parser


def ingest(root: Path, args: argparse.Namespace, source: Path, *, initialise: bool, name: str) -> int:
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
    return process_result.run_step(
        "lane submission",
        cmd,
        root,
        failure_label=f"onepush-{name}: lane submission failed",
    )


def ship(root: Path, args: argparse.Namespace, name: str) -> int:
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
        failure_label=f"onepush-{name}: amalgamation failed",
    )
    if code != 0:
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
        failure_label=f"onepush-{name}: sync failed",
    )


def checked_source(path: str) -> Path:
    source = Path(path).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        raise RuntimeError(f"source folder does not exist: {source}")
    return source


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    args.agent = forks.normalize_agent(args.agent)
    if args.agent not in forks.AGENTS:
        raise RuntimeError(f"unsupported agent {args.agent!r}; expected one of {', '.join(forks.AGENTS)}")
    root = forks.repo_root()
    name = target_name(args.agent, args.gizmo, args.gadget)

    if args.init_from_dir:
        code = ingest(root, args, checked_source(args.init_from_dir), initialise=True, name=name)
        if code != 0:
            return code
        if not args.ship:
            print(f"onepush-{name}: lane submitted.")
            return 0
        code = ship(root, args, name)
        if code == 0:
            print(f"onepush-{name}: shipped.")
        return code

    if args.ship:
        code = ship(root, args, name)
        if code == 0:
            print(f"onepush-{name}: shipped.")
        return code

    code = ingest(root, args, checked_source(args.source), initialise=False, name=name)
    if code == 0:
        print(f"onepush-{name}: lane submitted.")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"onepush: {exc}", file=sys.stderr)
        raise SystemExit(1)
