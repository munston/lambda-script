#!/usr/bin/env python3
r"""Agent-specific gadget creation wrapper.

This command is intended to sit behind the root batch wrappers:

    gadget-creation-edd.bat <gizmo> <gadget> <path-to-folder>

It initializes the gadget branch set when required and ingests the supplied local
folder into the selected gadget-agent lane. Amalgamation is deliberately opt-in:
pass --amalgamate when the lane should also be applied to the gadget integration
branch.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import forks

VALID_AGENTS = {"ed", "edd", "eddy", "guy"}


def repo_rel_or_default(root: Path, source: Path, gadget: str) -> str:
    try:
        rel = source.resolve().relative_to(root.resolve())
        return str(rel).replace("\\", "/")
    except ValueError:
        return f"projects/{gadget}"


def run(args: list[str], root: Path) -> int:
    print("> " + " ".join(quote_arg(x) for x in args))
    proc = subprocess.run(args, cwd=str(root), text=True)
    return int(proc.returncode)


def quote_arg(value: str) -> str:
    if any(ch.isspace() for ch in value) or '"' in value:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def default_verify_command(dest: str) -> str:
    win_dest = dest.replace("/", "\\")
    return f'if exist "{win_dest}" (exit /b 0) else (echo missing {win_dest} & exit /b 1)'


def ingest_script(root: Path) -> Path:
    path = root / "scripts" / "forks" / "gadget_ingest_folder.py"
    if not path.exists():
        raise RuntimeError(f"missing gadget ingest support: {path}")
    return path


def safe_amalgamate_script(root: Path) -> Path:
    path = root / "scripts" / "forks" / "gadget_amalgamate_safe.py"
    if not path.exists():
        raise RuntimeError(f"missing safe gadget amalgamation support: {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gadget-creation-<agent>.bat",
        description="Initialize a gizmo/gadget if needed and ingest a local folder into this agent lane.",
    )
    parser.add_argument("agent", help="configured agent lane: ed, edd, eddy, or guy")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("source", help="local folder to ingest")
    parser.add_argument("--dest", help="destination path inside the gadget branch; defaults to repo-relative source path or projects/<gadget>")
    parser.add_argument("--message", help="commit message for the gadget-agent lane")
    parser.add_argument("--verify-command", help="verification command for optional amalgamation; defaults to checking that --dest exists")
    parser.add_argument("--replace", action="store_true", help="remove the destination before copying the source folder")
    parser.add_argument("--exclude", action="append", default=[], help="additional glob pattern to exclude; may be repeated")
    parser.add_argument("--no-default-excludes", action="store_true", help="disable the ingest command's default excludes")
    parser.add_argument("--follow-symlinks", action="store_true")
    parser.add_argument("--allow-existing-lane-work", action="store_true")
    parser.add_argument("--amalgamate", action="store_true", help="after ingesting, safely apply the lane to the gadget integration branch")
    parser.add_argument("--no-amalgamate", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--skip-replay-audit", action="store_true", help="pass through to safe amalgamation when --amalgamate is used")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    agent = forks.normalize_agent(args.agent)
    if agent not in VALID_AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of: ed, edd, eddy, guy")

    root = forks.repo_root()
    forks.ensure_dirs(root)

    source = Path(args.source)
    if not source.exists():
        raise RuntimeError(f"source folder does not exist: {source}")
    if not source.is_dir():
        raise RuntimeError(f"source is not a folder: {source}")

    dest = (args.dest or repo_rel_or_default(root, source, args.gadget)).replace("\\", "/").strip("/")
    if not dest:
        raise RuntimeError("destination path is empty")

    message = args.message or f"Materialise {args.gizmo}/{args.gadget} from {source.name}"
    verify = args.verify_command or default_verify_command(dest)

    print("gadget creation")
    print(f"  agent: {agent}")
    print(f"  gizmo/gadget: {args.gizmo}/{args.gadget}")
    print(f"  source: {source}")
    print(f"  dest: {dest}")
    print(f"  amalgamate: {'yes' if args.amalgamate else 'no'}")
    if args.amalgamate:
        print(f"  verify-command: {verify}")

    ingest = [
        sys.executable,
        str(ingest_script(root)),
        args.gizmo,
        args.gadget,
        agent,
        "--init-if-missing",
        "--source",
        str(source),
        "--dest",
        dest,
        "--message",
        message,
    ]

    if args.replace:
        ingest.append("--replace")
    if args.no_default_excludes:
        ingest.append("--no-default-excludes")
    if args.follow_symlinks:
        ingest.append("--follow-symlinks")
    if args.allow_existing_lane_work:
        ingest.append("--allow-existing-lane-work")
    for pattern in args.exclude:
        ingest.extend(["--exclude", pattern])

    code = run(ingest, root)
    if code != 0:
        return code

    if not args.amalgamate:
        print("ingest complete; amalgamation skipped by default")
        print(f"run safe amalgamation explicitly when ready: python scripts\\forks\\gadget_amalgamate_safe.py --gadget {args.gizmo} {args.gadget} --agents {agent} --apply --verify-command <command>")
        return 0

    amalgamate = [
        sys.executable,
        str(safe_amalgamate_script(root)),
        "--gadget",
        args.gizmo,
        args.gadget,
        "--agents",
        agent,
        "--apply",
        "--verify-command",
        verify,
    ]
    if args.skip_replay_audit:
        amalgamate.append("--skip-replay-audit")
    return run(amalgamate, root)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"gadget-creation: {exc}", file=sys.stderr)
        raise SystemExit(1)
