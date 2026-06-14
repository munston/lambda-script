#!/usr/bin/env python3
"""Import, verify, submit, and sync a JSON forks patch in one command."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import forks
import import_json_patch

AGENTS = ("ed", "edd", "eddy", "guy")


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(cwd), text=True)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(args))
    return proc


def sync_agent(root: Path, agent: str) -> None:
    branch = forks.agent_branch(agent)
    if not forks.ref_exists(root, branch):
        forks.git(["branch", branch, forks.MAIN_REF], root)
        print(f"{branch}: created at {forks.short_commit(root, forks.MAIN_REF)}")
        return

    ahead, behind = forks.ahead_behind(root, branch)
    state = forks.classify(ahead, behind)

    if state == "even":
        print(f"{branch}: even")
        return

    if state == "behind-only":
        if forks.current_branch(root) == branch:
            forks.git(["reset", "--hard", forks.MAIN_REF], root)
        else:
            forks.git(["branch", "-f", branch, forks.MAIN_REF], root)
        print(f"{branch}: synced to {forks.short_commit(root, forks.MAIN_REF)}")
        return

    raise RuntimeError(f"refusing to sync {branch}; state={state} ahead={ahead} behind={behind}")


def require_candidate_fresh(work: Path) -> None:
    forks.fetch_main(work)
    ancestor = forks.git(["merge-base", "--is-ancestor", forks.MAIN_REF, "HEAD"], work, check=False)
    if ancestor.returncode != 0:
        raise RuntimeError("origin/main is not an ancestor of imported candidate")

    ahead, behind = forks.ahead_behind(work, "HEAD")
    if ahead <= 0 or behind != 0:
        raise RuntimeError(f"imported candidate is not fresh ahead-only: ahead={ahead} behind={behind}")


def cmd_land(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    forks.fetch_main(root)

    if args.require_file and not args.file:
        raise RuntimeError("land-json-file requires a JSON patch file path")

    payload = import_json_patch.load_payload(args.file)
    submission = import_json_patch.make_submission(root, args.agent, payload)
    import_json_patch.submission_object.write_submission(root, args.agent, submission)

    work = import_json_patch.import_worktree(root, args.agent)
    require_candidate_fresh(work)

    print(f"imported JSON candidate for {submission['agent']}: {work}")
    print(f"files={len(submission['changed_files'])} ahead={submission['ahead']} behind={submission['behind']}")

    print("verifying imported candidate")
    if args.full:
        run(["cmd", "/c", "verify.bat"], work)
    else:
        run([
            sys.executable,
            "-m",
            "py_compile",
            "scripts/forks/forks.py",
            "scripts/forks/submission_object.py",
            "scripts/forks/import_json_patch.py",
            "scripts/forks/land_json_patch.py",
        ], work)

    require_candidate_fresh(work)

    print("dry-run submit")
    run(["git", "push", "--dry-run", "origin", "HEAD:main"], work)

    print("submit")
    run(["git", "push", "origin", "HEAD:main"], work)

    forks.fetch_main(root)

    print("syncing agent lanes")
    for agent in AGENTS:
        sync_agent(root, agent)

    print("final status")
    run(["cmd", "/c", "forks.bat", "status", "--fetch"], root)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks land-json")
    parser.add_argument("--require-file", action="store_true")
    parser.add_argument("--full", action="store_true", help="run full verify.bat instead of quick Python tooling verification")
    parser.add_argument("agent")
    parser.add_argument("file", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return cmd_land(args)
    except Exception as exc:
        print(f"forks land-json: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
