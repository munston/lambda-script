#!/usr/bin/env python3
"""Promote a gadget integration branch to repository main."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import forks
import gadget_branches
import gadget_verify_profiles
import main_history

AGENTS = ("ed", "edd", "eddy", "guy")
PROMOTION_DIR = "promotions"


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(args))
    return proc


def run_shell(command: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=str(cwd), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: " + command)
    return proc


def worktree_path(root: Path, gizmo: str, gadget: str) -> Path:
    safe = f"{gizmo}-{gadget}".replace("/", "-")
    return root / forks.FORKS_DIR / PROMOTION_DIR / safe


def remove_worktree(root: Path, work: Path) -> None:
    if work.exists():
        forks.git(["worktree", "remove", "--force", str(work)], root, check=False)
    if work.exists():
        shutil.rmtree(work)
    forks.git(["worktree", "prune"], root, check=False)


def fetch(root: Path) -> None:
    forks.git(["fetch", "--prune", "origin"], root)


def ensure_ref(root: Path, ref: str) -> None:
    if not forks.ref_exists(root, ref):
        raise RuntimeError(f"missing ref: {ref}")


def sync_repository_agent(root: Path, agent: str) -> None:
    branch = forks.agent_branch(agent)
    if not forks.ref_exists(root, branch):
        forks.git(["branch", branch, forks.MAIN_REF], root)
        print(f"{branch}: created at {forks.short_commit(root, forks.MAIN_REF)}")
        return

    ahead, behind = forks.ahead_behind(root, branch, forks.MAIN_REF)
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


def verify_with_profile(root: Path, work: Path, gizmo: str, gadget: str, profile: str | None) -> None:
    if profile:
        commands = gadget_verify_profiles.profile_commands(root, gizmo, gadget, profile)
        if commands is None:
            raise RuntimeError(f"missing verification profile {profile} for {gizmo}/{gadget}")
        print(f"verification profile: {profile}")
        for command in commands:
            print(f"> {command}")
            run_shell(command, work)
        return

    print("verification profile: full fallback")
    run(["cmd", "/c", "verify.bat"], work)


def require_ahead_only(root: Path, target_ref: str) -> tuple[int, int]:
    ahead, behind = forks.ahead_behind(root, target_ref, forks.MAIN_REF)
    if ahead == 0 and behind == 0:
        raise RuntimeError(f"{target_ref} is already even with {forks.MAIN_REF}")
    if behind != 0:
        raise RuntimeError(f"{target_ref} is not based on current {forks.MAIN_REF}: ahead={ahead} behind={behind}; sync/rebase the gadget before promotion")
    return ahead, behind


def stamp_promotion_history(work: Path, gizmo: str, gadget: str, target_ref: str, ahead: int) -> None:
    changed_files = forks.changed_files(work, "HEAD", forks.MAIN_REF)
    receipt = main_history.stamp_main_version(
        work,
        kind="gadget_promotion",
        agent="system",
        title=f"Promote {gizmo}/{gadget}",
        base_ref=forks.MAIN_REF,
        source_ref=target_ref,
        changed_files=changed_files,
        metadata={
            "gizmo": gizmo,
            "gadget": gadget,
            "target_ref": target_ref,
            "promoted_commits": ahead,
        },
    )
    print(f"main version: {receipt['version']}")


def cmd_promote(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    fetch(root)

    target_ref = gadget_branches.target_ref(args.gizmo, args.gadget)
    ensure_ref(root, forks.MAIN_REF)
    ensure_ref(root, target_ref)

    ahead, behind = require_ahead_only(root, target_ref)
    print(f"promoting {args.gizmo}/{args.gadget}")
    print(f"source={target_ref} ahead={ahead} behind={behind}")
    print(f"destination={forks.MAIN_REF}")

    work = worktree_path(root, args.gizmo, args.gadget)
    remove_worktree(root, work)
    forks.git(["worktree", "add", "--detach", str(work), target_ref], root)

    if not args.no_verify:
        profile = args.profile
        if profile is None:
            profile = "full" if args.full else "quick"
        verify_with_profile(root, work, args.gizmo, args.gadget, profile)
    else:
        print("verification skipped by --no-verify")

    fetch(root)
    ensure_ref(root, forks.MAIN_REF)
    ensure_ref(root, target_ref)
    ahead_after, behind_after = require_ahead_only(root, target_ref)
    if ahead_after != ahead or behind_after != behind:
        raise RuntimeError("source/destination relationship changed during verification; rerun promotion")

    if not args.no_history:
        stamp_promotion_history(work, args.gizmo, args.gadget, target_ref, ahead)

    ancestor = forks.git(["merge-base", "--is-ancestor", forks.MAIN_REF, "HEAD"], work, check=False)
    if ancestor.returncode != 0:
        raise RuntimeError(f"{forks.MAIN_REF} is not an ancestor of promotion candidate")

    if args.dry_run:
        print("dry-run submit")
        run(["git", "push", "--dry-run", "origin", "HEAD:main"], work)
        return 0

    print("submit")
    run(["git", "push", "origin", "HEAD:main"], work)

    fetch(root)
    print("syncing repository agent lanes")
    for agent in AGENTS:
        sync_repository_agent(root, agent)

    print("repository status")
    run(["cmd", "/c", "forks.bat", "status", "--fetch"], root)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks gadget-promote")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile", help="manifest verification profile to run before promotion; defaults to quick")
    parser.add_argument("--full", action="store_true", help="use the full manifest verification profile")
    parser.add_argument("--no-verify", action="store_true", help="skip verification gate")
    parser.add_argument("--no-history", action="store_true", help="do not append a main-history receipt before pushing")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return cmd_promote(args)
    except Exception as exc:
        print(f"forks gadget-promote: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
