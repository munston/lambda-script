#!/usr/bin/env python3
r"""Agent-specific repository amalgamation wrapper.

By default this is transport-only: it uses a no-op verifier so a repository
agent lane can be captured, replayed, and submitted without accidentally running
verify.bat, Cabal, npm, or another project-local build gate. Pass
--verify-command explicitly when signover should be build-gated.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import forks

VALID_AGENTS = set(forks.AGENTS)


def quote_arg(value: str) -> str:
    if any(ch.isspace() for ch in value) or '"' in value:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def amalgamate_script(root: Path) -> Path:
    path = root / "scripts" / "forks" / "amalgamate_all.py"
    if not path.exists():
        raise RuntimeError(f"missing repository amalgamation support: {path}")
    return path


def noop_verify_command() -> str:
    return '"' + sys.executable + '" -c "import sys; sys.exit(0)"'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-amalgamate-<agent>.bat",
        description="Amalgamate one agents/<agent> lane into main. Transport-only by default.",
    )
    parser.add_argument("agent", help="configured repository agent lane: ed, edd, eddy, or guy")
    parser.add_argument("--plan", action="store_true", help="show the amalgamation plan without applying it")
    parser.add_argument("--verify-command", help="optional verifier to run during replay; default is transport-only no-op")
    parser.add_argument("--backend", choices=("ref", "contents"), default="ref")
    parser.add_argument("--allow-forbidden", action="store_true")
    parser.add_argument("--skip-final-sync", action="store_true")
    parser.add_argument("--skip-final-assert", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    agent = forks.normalize_agent(args.agent)
    if agent not in VALID_AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of: {', '.join(forks.AGENTS)}")
    root = forks.repo_root()
    verify = args.verify_command or noop_verify_command()

    cmd = [
        sys.executable,
        str(amalgamate_script(root)),
        "--agents",
        agent,
        "--verify-command",
        verify,
        "--backend",
        args.backend,
    ]
    if not args.plan:
        cmd.append("--apply")
    if args.allow_forbidden:
        cmd.append("--allow-forbidden")
    if args.skip_final_sync:
        cmd.append("--skip-final-sync")
    if args.skip_final_assert:
        cmd.append("--skip-final-assert")

    print("repository agent amalgamation")
    print(f"  agent: {agent}")
    print(f"  mode: {'plan' if args.plan else 'apply'}")
    print(f"  verify-command: {verify if args.verify_command else '<transport-only no-op>'}")
    print("> " + " ".join(quote_arg(x) for x in cmd))
    proc = subprocess.run(cmd, cwd=str(root))
    return int(proc.returncode)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"agent-amalgamate: {exc}", file=sys.stderr)
        raise SystemExit(1)
