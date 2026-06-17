#!/usr/bin/env python3
r"""Single high-level agent push button.

Shape:

    onepush-edd.bat [--ship] <gizmo> <gadget> [path-to-folder] [options]
    onepush-edd.bat [--ship] --repo [path-to-folder] --dest <repo/path> [options]

There are deliberately no mode words. Without --ship, onepush only submits a
lane checkpoint. With --ship, onepush submits first when a source folder is
provided, then amalgamates and syncs.

The non-destructive invariant is that a lane head is disposable only after the
work has been captured into the submission/replay stream. A later --ship may
rewind a lane, but it must not make an earlier onepush checkpoint unrecoverable.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import forks

VALID_AGENTS = set(forks.AGENTS)

ERROR_MARKERS = (
    "error:",
    "fatal:",
    "traceback",
    "assertionerror",
    "exception",
    "cabal-",
    "ghc-",
    "failed",
    "not found",
    "cannot ",
    "could not",
    "permission denied",
    "npm err",
    "type error",
    "parse error",
)


def quote_arg(value: str) -> str:
    if any(ch.isspace() for ch in value) or '"' in value:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def command_text(cmd: list[str]) -> str:
    return " ".join(quote_arg(str(x)) for x in cmd)


def interesting(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in ERROR_MARKERS)


def prune_text(text: str, *, limit: int = 24, context: int = 2) -> list[str]:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line.strip()]
    if not lines:
        return []
    hits = [i for i, line in enumerate(lines) if interesting(line)]
    if not hits:
        head = lines[: min(8, len(lines))]
        if len(lines) > len(head):
            head.append(f"... {len(lines) - len(head)} more line(s) suppressed")
        return head
    selected: list[str] = []
    seen: set[int] = set()
    for hit in hits:
        lo = max(0, hit - context)
        hi = min(len(lines), hit + context + 1)
        for idx in range(lo, hi):
            if idx not in seen:
                seen.add(idx)
                selected.append(lines[idx])
            if len(selected) >= limit:
                selected.append("... diagnostic output truncated")
                return selected
    return selected


def run_step(label: str, cmd: list[str], root: Path) -> int:
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode == 0:
        print(f"{label}: ok.")
        return 0
    print(f"{label}: failed (exit {proc.returncode}).")
    merged = "\n".join(part for part in (proc.stderr, proc.stdout) if part)
    for line in prune_text(merged):
        print("  " + line)
    print("  command: " + command_text(cmd))
    return int(proc.returncode)


def script(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        raise RuntimeError(f"missing support script: {path}")
    return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onepush-<agent>.bat",
        description=(
            "Submit one agent lane checkpoint; add --ship to amalgamate and sync. "
            "No mode argument is accepted."
        ),
    )
    parser.add_argument("agent", help="configured agent lane: ed, edd, eddy, or guy")
    parser.add_argument("target", nargs="*", help="gadget form: <gizmo> <gadget> [source]; repo form: [source] with --repo")
    parser.add_argument("--ship", action="store_true", help="after optional submission, amalgamate and sync")
    parser.add_argument("--repo", action="store_true", help="target agents/<agent> instead of a gadget-agent lane")
    parser.add_argument("--dest", help="destination path inside the target branch")
    parser.add_argument("--message", help="commit message for the lane checkpoint")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--no-default-excludes", action="store_true")
    parser.add_argument("--follow-symlinks", action="store_true")
    parser.add_argument("--verify-command", help="optional verifier for --ship; omitted means transport-only")
    parser.add_argument("--backend", choices=("ref", "contents"), default="ref", help="repository --ship backend")
    parser.add_argument("--allow-forbidden", action="store_true", help="repository --ship pass-through")
    parser.add_argument("--skip-replay-audit", action="store_true", help="gadget --ship pass-through")
    parser.add_argument("--require-ledgers", action="store_true", help="gadget --ship pass-through")
    return parser


def add_folder_options(cmd: list[str], args: argparse.Namespace) -> None:
    if args.dest:
        cmd.extend(["--dest", args.dest])
    if args.message:
        cmd.extend(["--message", args.message])
    if args.replace:
        cmd.append("--replace")
    cmd.append("--allow-existing-lane-work")
    if args.no_default_excludes:
        cmd.append("--no-default-excludes")
    if args.follow_symlinks:
        cmd.append("--follow-symlinks")
    for pattern in args.exclude:
        cmd.extend(["--exclude", pattern])


def repo_submit_command(root: Path, agent: str, source: str, args: argparse.Namespace) -> list[str]:
    if not args.dest:
        raise RuntimeError("--repo folder submission requires --dest")
    cmd = [sys.executable, script(root, "scripts/forks/agent_folder_submit.py"), agent, source]
    add_folder_options(cmd, args)
    return cmd


def gadget_submit_command(root: Path, agent: str, gizmo: str, gadget: str, source: str, args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, script(root, "scripts/forks/gadget_creation_agent.py"), agent, gizmo, gadget, source]
    add_folder_options(cmd, args)
    return cmd


def repo_ship_command(root: Path, agent: str, args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, script(root, "scripts/forks/agent_amalgamate_agent.py"), agent]
    if args.verify_command:
        cmd.extend(["--verify-command", args.verify_command])
    if args.backend:
        cmd.extend(["--backend", args.backend])
    if args.allow_forbidden:
        cmd.append("--allow-forbidden")
    return cmd


def gadget_ship_command(root: Path, agent: str, gizmo: str, gadget: str, args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, script(root, "scripts/forks/gadget_amalgamate_agent.py"), agent, gizmo, gadget]
    if args.verify_command:
        cmd.extend(["--verify-command", args.verify_command])
    if args.skip_replay_audit:
        cmd.append("--skip-replay-audit")
    if args.require_ledgers:
        cmd.append("--require-ledgers")
    return cmd


def gadget_sync_command(gizmo: str, gadget: str) -> list[str]:
    return ["cmd", "/c", "forks.bat", "gadget-sync-all", gizmo, gadget]


def repo_sync_command() -> list[str]:
    return ["cmd", "/c", "forks.bat", "sync-all"]


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    agent = forks.normalize_agent(args.agent)
    if agent not in VALID_AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of: {', '.join(forks.AGENTS)}")
    root = forks.repo_root()
    forks.ensure_dirs(root)

    print(f"onepush {agent}")
    print(f"  ship: {'yes' if args.ship else 'no'}")

    if args.repo:
        source = args.target[0] if args.target else None
        if len(args.target) > 1:
            raise RuntimeError("--repo accepts at most one positional source folder")
        if not source and not args.ship:
            raise RuntimeError("onepush without --ship requires a source folder")
        if source:
            code = run_step("lane submission", repo_submit_command(root, agent, source, args), root)
            if code != 0:
                print("ship: skipped because lane submission failed.")
                return code
        else:
            print("lane submission: skipped; shipping existing lane.")
        if not args.ship:
            print("ship: skipped.")
            print("checkpoint durable: submitted lane work may be captured/replayed even if the lane is later rewound by signover.")
            return 0
        code = run_step("repository amalgamation", repo_ship_command(root, agent, args), root)
        if code != 0:
            print("sync: skipped because amalgamation failed.")
            return code
        return run_step("repository sync", repo_sync_command(), root)

    if len(args.target) < 2:
        raise RuntimeError("gadget onepush requires <gizmo> <gadget> [source]")
    if len(args.target) > 3:
        raise RuntimeError("gadget onepush accepts <gizmo> <gadget> [source]")
    gizmo, gadget = args.target[0], args.target[1]
    source = args.target[2] if len(args.target) == 3 else None
    print(f"  target: {gizmo}/{gadget}")

    if not source and not args.ship:
        raise RuntimeError("onepush without --ship requires a source folder")
    if source:
        code = run_step("lane submission", gadget_submit_command(root, agent, gizmo, gadget, source, args), root)
        if code != 0:
            print("ship: skipped because lane submission failed.")
            return code
    else:
        print("lane submission: skipped; shipping existing lane.")
    if not args.ship:
        print("ship: skipped.")
        print("checkpoint durable: submitted lane work may be captured/replayed even if the lane is later rewound by signover.")
        return 0

    code = run_step("gadget amalgamation", gadget_ship_command(root, agent, gizmo, gadget, args), root)
    if code != 0:
        print("sync: skipped because amalgamation failed.")
        return code
    return run_step("gadget sync", gadget_sync_command(gizmo, gadget), root)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"onepush: {exc}", file=sys.stderr)
        raise SystemExit(1)
