#!/usr/bin/env python3
r"""Agent-specific safe gadget amalgamation wrapper.

Usage:
  gadget-amalgamate-guy.bat <gizmo> <gadget> [--verify-command "..."]

The explicit <gizmo> <gadget> arguments prevent a wrapper from silently
amalgamating the wrong gadget. Verification is transport-only by default.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import forks
import process_result

VALID_AGENTS = set(forks.AGENTS)


def quote_arg(value: str) -> str:
    return process_result.quote_arg(value)


def safe_amalgamate_script(root: Path) -> Path:
    path = root / "scripts" / "forks" / "gadget_amalgamate_safe.py"
    if not path.exists():
        raise RuntimeError(f"missing safe gadget amalgamation support: {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gadget-amalgamate-<agent>.bat",
        description="Safely amalgamate one gadget-agent lane into its gadget integration branch.",
    )
    parser.add_argument("agent", help="configured agent lane: ed, edd, eddy, or guy")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("--plan", action="store_true", help="show the plan without applying it")
    parser.add_argument("--verify-command", help="optional gadget-local verifier; omitted means transport-only")
    parser.add_argument("--skip-replay-audit", action="store_true")
    parser.add_argument("--require-ledgers", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    agent = forks.normalize_agent(args.agent)
    if agent not in VALID_AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of: {', '.join(forks.AGENTS)}")
    root = forks.repo_root()

    cmd = [
        sys.executable,
        str(safe_amalgamate_script(root)),
        "--gadget",
        args.gizmo,
        args.gadget,
        "--agents",
        agent,
    ]
    if not args.plan:
        cmd.append("--apply")
    if args.verify_command:
        cmd.extend(["--verify-command", args.verify_command])
    if args.skip_replay_audit:
        cmd.append("--skip-replay-audit")
    if args.require_ledgers:
        cmd.append("--require-ledgers")

    print("gadget amalgamation")
    print(f"  agent: {agent}")
    print(f"  gizmo/gadget: {args.gizmo}/{args.gadget}")
    print(f"  mode: {'plan' if args.plan else 'apply'}")
    print(f"  verify-command: {args.verify_command if args.verify_command else '<none; transport-only>'}")
    result = process_result.run_process("safe gadget amalgamation", cmd, root)
    print(process_result.summarize(result))
    return int(result.returncode)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"gadget-amalgamate: {exc}", file=sys.stderr)
        raise SystemExit(1)
