#!/usr/bin/env python3
"""Guarded amalgamation for agent lanes.

This command is the operator-facing "freshen then sync" layer. It captures each
agent lane that has unique work into a submission object, replays that submission
onto current main, verifies it, submits it, then optionally rewinds the captured
lane to the new main only after the captured commit check succeeds.

By default it is a dry plan. Pass --apply to mutate.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import forks

DEFAULT_AGENTS = ("ed", "edd", "eddy")


def script_path(name: str) -> Path:
    return Path(__file__).with_name(name)


def run_py(root: Path, script: str, args: list[str]) -> None:
    proc = subprocess.run([sys.executable, str(script_path(script)), *args], cwd=str(root), text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: python scripts/forks/{script} {' '.join(args)}")


def tracked_status(root: Path) -> str:
    return forks.git_text(["status", "--porcelain=v1", "--untracked-files=no"], root)


def require_clean_tracked(root: Path) -> None:
    status = tracked_status(root)
    if status.strip():
        raise RuntimeError("working tree has tracked changes; commit, stash, or restore before amalgamate-all\n" + status)


def best_ref_or_none(root: Path, agent: str) -> str | None:
    branch = forks.agent_branch(agent)
    if forks.ref_exists(root, branch):
        return branch
    remote = f"origin/{branch}"
    if forks.ref_exists(root, remote):
        return remote
    return None


def command_line(agent: str, ref: str, args: argparse.Namespace) -> list[list[str]]:
    capture = ["capture", agent, "--from-ref", ref]
    replay = ["replay", agent, "--rebase-stale"]
    verify = ["verify-submission", agent, "--command", args.verify_command]
    dry_submit = ["submit-submission", agent, "--backend", args.backend, "--dry-run"]
    submit = ["submit-submission", agent, "--backend", args.backend]
    if args.allow_forbidden:
        capture.append("--allow-forbidden")
        replay.append("--allow-forbidden")
        verify.append("--allow-forbidden")
    out = [capture, replay, verify, dry_submit, submit]
    if args.sync_lanes:
        out.append(["sync-captured-lane", agent, "--yes"])
    return out


def print_plan(agent: str, ref: str, state: str, ahead: int, behind: int, args: argparse.Namespace) -> None:
    print(f"{agent}: {state} ahead={ahead} behind={behind} source={ref}")
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no unique work to capture")
        return
    for cmd in command_line(agent, ref, args):
        print("  forks.bat " + " ".join(cmd))


def apply_agent(root: Path, agent: str, ref: str, state: str, ahead: int, behind: int, args: argparse.Namespace) -> None:
    print(f"{agent}: {state} ahead={ahead} behind={behind} source={ref}")
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no unique work to capture")
        return

    capture = ["capture", agent, "--from-ref", ref]
    if args.allow_forbidden:
        capture.append("--allow-forbidden")
    run_py(root, "submission_object.py", capture)

    replay = ["replay", agent, "--rebase-stale"]
    if args.allow_forbidden:
        replay.append("--allow-forbidden")
    run_py(root, "submission_object.py", replay)

    verify = ["verify", agent, "--command", args.verify_command]
    if args.allow_forbidden:
        verify.append("--allow-forbidden")
    run_py(root, "submission_object.py", verify)

    run_py(root, "submission_object.py", ["submit", agent, "--backend", args.backend, "--dry-run"])
    run_py(root, "submission_object.py", ["submit", agent, "--backend", args.backend])

    forks.fetch_main(root)
    if args.sync_lanes:
        run_py(root, "submission_object.py", ["sync-lane", agent, "--yes"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forks amalgamate-all",
        description="Capture, replay, verify, submit, and optionally rewind agent lanes with unique work.",
    )
    parser.add_argument("--agents", nargs="+", default=list(DEFAULT_AGENTS), help="agent lanes to inspect; default: ed edd eddy")
    parser.add_argument("--verify-command", default="verify.bat", help="verification command run in the replayed candidate")
    parser.add_argument("--backend", choices=("ref", "contents"), default="ref", help="submission backend")
    parser.add_argument("--allow-forbidden", action="store_true", help="allow guarded paths during capture/replay/verify")
    parser.add_argument("--apply", action="store_true", help="mutate: capture, replay, verify, submit, and sync captured lanes")
    parser.add_argument("--no-sync-lanes", dest="sync_lanes", action="store_false", help="do not rewind captured lanes after submit")
    parser.set_defaults(sync_lanes=True)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = forks.repo_root()
    forks.ensure_dirs(root)
    try:
        require_clean_tracked(root)
        forks.fetch_main(root)
        if not args.apply:
            print("amalgamate-all plan only; pass --apply to mutate")
        for raw_agent in args.agents:
            agent = forks.normalize_agent(raw_agent)
            ref = best_ref_or_none(root, agent)
            if not ref:
                print(f"{agent}: missing lane; skipped")
                continue
            ahead, behind = forks.ahead_behind(root, ref)
            state = forks.classify(ahead, behind)
            if args.apply:
                apply_agent(root, agent, ref, state, ahead, behind, args)
            else:
                print_plan(agent, ref, state, ahead, behind, args)
        if args.apply:
            print("amalgamate-all complete")
        return 0
    except Exception as exc:
        print(f"forks amalgamate-all: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
