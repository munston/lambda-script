#!/usr/bin/env python3
"""Ingest a local folder into a forks gadget-agent lane.

This command is for large local trees that are awkward or impossible to encode as
LS_FORK_JSON_PATCH_V1 file entries. It copies a local source folder into a
throwaway worktree based on the selected gadget-agent lane, commits the resulting
tree delta on that lane, and pushes the lane. Existing gadget amalgamation then
turns the lane delta into the integration-branch patch.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any

import amalgamate_all
import forks
import gadget_branches

DEFAULT_EXCLUDES = (
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".stack-work",
    "dist-newstyle",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".env.*",
    "*.pyc",
    "*.pyo",
    "*.o",
    "*.hi",
    "*.dyn_o",
    "*.dyn_hi",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    ".DS_Store",
)


def clean_relative_path(kind: str, raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError(f"{kind} must be a non-empty relative path")
    normal = raw.replace("\\", "/").strip("/")
    if ":" in normal:
        raise RuntimeError(f"{kind} must not contain a drive or scheme: {raw}")
    posix = PurePosixPath(normal)
    if posix.is_absolute():
        raise RuntimeError(f"{kind} must be relative: {raw}")
    parts = posix.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError(f"{kind} is unsafe: {raw}")
    if parts[0] == ".git" or ".git" in parts:
        raise RuntimeError(f"{kind} must not traverse .git: {raw}")
    return str(posix)


def safe_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value)


def remote_ref(branch: str) -> str:
    return f"origin/{branch}"


def full_remote_ref(branch: str) -> str:
    return f"refs/heads/{branch}"


def remove_worktree(root: Path, work: Path) -> None:
    if work.exists():
        forks.git(["worktree", "remove", "--force", str(work)], root, check=False)
    if work.exists():
        shutil.rmtree(work)
    forks.git(["worktree", "prune"], root, check=False)


def parse_name_status(text: str) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        path = parts[-1]
        item = {"status": status, "path": path}
        if status.startswith("R") and len(parts) >= 3:
            item["old_path"] = parts[1]
        files.append(item)
    return files


def path_matches_any(rel: str, patterns: tuple[str, ...]) -> bool:
    parts = rel.split("/")
    for pattern in patterns:
        normal = pattern.replace("\\", "/")
        if any(fnmatch.fnmatch(part, normal) for part in parts):
            return True
        if fnmatch.fnmatch(rel, normal):
            return True
    return False


def copy_source_tree(
    source: Path,
    target: Path,
    excludes: tuple[str, ...],
    *,
    replace: bool,
    follow_symlinks: bool,
) -> tuple[int, int]:
    if replace and target.exists():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for dirpath, dirnames, filenames in os.walk(source, topdown=True, followlinks=follow_symlinks):
        current = Path(dirpath)
        rel_dir = current.relative_to(source).as_posix()
        if rel_dir == ".":
            rel_dir = ""

        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            rel = dirname if not rel_dir else f"{rel_dir}/{dirname}"
            full = current / dirname
            if path_matches_any(rel, excludes):
                skipped += 1
                continue
            if full.is_symlink() and not follow_symlinks:
                skipped += 1
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            rel = filename if not rel_dir else f"{rel_dir}/{filename}"
            src = current / filename
            if path_matches_any(rel, excludes):
                skipped += 1
                continue
            if src.is_symlink() and not follow_symlinks:
                skipped += 1
                continue
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
            copied += 1
    return copied, skipped


def ensure_initialized_if_requested(root: Path, args: argparse.Namespace) -> None:
    forks.git(["fetch", "--prune", "origin"], root)
    target = gadget_branches.target_ref(args.gizmo, args.gadget)
    lane = gadget_branches.gadget_agent_branch(args.agent, args.gizmo, args.gadget)
    missing = not forks.ref_exists(root, target) or not forks.ref_exists(root, remote_ref(lane))
    if missing and not args.init_if_missing:
        raise RuntimeError(
            f"missing gadget target or lane for {args.gizmo}/{args.gadget}; "
            "rerun with --init-if-missing"
        )
    if missing:
        print(f"initialising {args.gizmo}/{args.gadget}")
        init_args = SimpleNamespace(
            gizmo=args.gizmo,
            gadget=args.gadget,
            base_ref=args.base_ref,
            no_agents=False,
        )
        rc = gadget_branches.cmd_init(init_args)
        if rc != 0:
            raise RuntimeError("gadget initialization failed")
    forks.git(["fetch", "--prune", "origin"], root)
    if not forks.ref_exists(root, target):
        raise RuntimeError(f"missing gadget target after initialization: {target}")
    if not forks.ref_exists(root, remote_ref(lane)):
        raise RuntimeError(f"missing gadget agent lane after initialization: {remote_ref(lane)}")


def prepare_lane(root: Path, args: argparse.Namespace) -> tuple[str, str]:
    branch = gadget_branches.gadget_agent_branch(args.agent, args.gizmo, args.gadget)
    base_ref = gadget_branches.target_ref(args.gizmo, args.gadget)
    lane_remote = remote_ref(branch)

    ahead, behind = forks.ahead_behind(root, lane_remote, base_ref)
    state = forks.classify(ahead, behind)
    print(f"{branch}: pre-ingest {state} ahead={ahead} behind={behind}")

    if state in {"even", "behind-only"}:
        gadget_branches.sync_agent_lane(root, args.agent, args.gizmo, args.gadget)
        forks.git(["fetch", "--prune", "origin"], root)
    elif not args.allow_existing_lane_work:
        raise RuntimeError(
            f"{branch} already has unique work state={state} ahead={ahead} behind={behind}; "
            "amalgamate or pass --allow-existing-lane-work"
        )

    if not forks.ref_exists(root, branch):
        forks.git(["branch", branch, lane_remote], root)
    return branch, base_ref


def update_local_branch_from_remote(root: Path, branch: str) -> None:
    remote = remote_ref(branch)
    if not forks.ref_exists(root, remote):
        return
    if forks.current_branch(root) == branch:
        forks.git(["reset", "--hard", remote], root, check=False)
        return
    proc = forks.git(["branch", "-f", branch, remote], root, check=False)
    if proc.returncode != 0:
        print(f"warning: could not update local {branch}; remote was pushed", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)


def ingest_folder(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)

    args.agent = forks.normalize_agent(args.agent)
    if args.agent not in forks.AGENTS:
        raise RuntimeError(f"unsupported agent {args.agent!r}; expected one of {', '.join(forks.AGENTS)}")

    source = Path(args.source).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        raise RuntimeError(f"source folder does not exist or is not a directory: {source}")

    dest_rel = clean_relative_path("destination", args.dest)
    excludes = tuple(args.exclude)
    if not args.no_default_excludes:
        excludes = DEFAULT_EXCLUDES + excludes

    ensure_initialized_if_requested(root, args)
    branch, base_ref = prepare_lane(root, args)
    lane_ref = branch if forks.ref_exists(root, branch) else remote_ref(branch)
    expected_remote = forks.commit(root, remote_ref(branch))
    work = root / forks.FORKS_DIR / "worktrees" / safe_token(f"gadget-ingest-{args.gizmo}-{args.gadget}-{args.agent}")

    remove_worktree(root, work)
    forks.git(["worktree", "add", "--detach", str(work), lane_ref], root)
    try:
        target = work / dest_rel
        copied, skipped = copy_source_tree(
            source,
            target,
            excludes,
            replace=args.replace,
            follow_symlinks=args.follow_symlinks,
        )

        forks.git(["add", "-A", "--", dest_rel], work)
        status_text = forks.git_text(["diff", "--cached", "--name-status", "--", dest_rel], work)
        if not status_text:
            print(f"no changes after ingest copied={copied} skipped={skipped}")
            return 0

        changed = parse_name_status(status_text)
        blocked = forks.guard_forbidden_paths(changed)
        if blocked and not args.allow_forbidden:
            raise RuntimeError("refusing ingest touching forbidden paths: " + ", ".join(blocked))

        print(status_text)
        print(f"copied={copied} skipped={skipped} changed={len(changed)}")

        if args.dry_run:
            print("dry run: not committing or pushing")
            return 0

        message = args.message or f"Ingest folder for {args.gizmo}/{args.gadget}"
        forks.git(["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", message], work)
        full = full_remote_ref(branch)
        forks.git(
            ["push", f"--force-with-lease={full}:{expected_remote}", "origin", f"HEAD:{full}"],
            work,
        )
    finally:
        remove_worktree(root, work)

    forks.git(["fetch", "--prune", "origin"], root)
    update_local_branch_from_remote(root, branch)

    print(f"{branch}: pushed to {remote_ref(branch)} at {forks.short_commit(root, remote_ref(branch))}")
    print("next:")
    print(f"  forks.bat amalgamate-all --gadget {args.gizmo} {args.gadget} --agents {args.agent} --apply")

    if args.amalgamate:
        argv = [
            "--gadget", args.gizmo, args.gadget,
            "--agents", args.agent,
            "--apply",
            "--verify-command", args.verify_command,
        ]
        rc = amalgamate_all.main(argv)
        if rc != 0:
            return rc
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forks gadget-ingest-folder",
        description="Copy a local folder into a gadget-agent lane and push it for normal amalgamation.",
    )
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("agent")
    parser.add_argument("--source", required=True, help="local source folder to ingest")
    parser.add_argument("--dest", required=True, help="repository-relative destination folder")
    parser.add_argument("--message", help="commit message for the gadget-agent lane commit")
    parser.add_argument("--init-if-missing", action="store_true", help="create the gadget integration branch and configured lanes if missing")
    parser.add_argument("--base-ref", default=forks.MAIN_REF, help="base ref used when --init-if-missing creates branches")
    parser.add_argument("--replace", action="store_true", help="replace the destination folder before copying")
    parser.add_argument("--exclude", action="append", default=[], help="additional file or directory glob to skip; may be repeated")
    parser.add_argument("--no-default-excludes", action="store_true", help="disable default cache/build/binary excludes")
    parser.add_argument("--follow-symlinks", action="store_true", help="copy symlink targets instead of skipping symlinks")
    parser.add_argument("--allow-existing-lane-work", action="store_true", help="commit on top of an already-ahead gadget-agent lane")
    parser.add_argument("--allow-forbidden", action="store_true", help="allow paths normally blocked by forks guards")
    parser.add_argument("--dry-run", action="store_true", help="copy into a temporary worktree and show staged changes without committing")
    parser.add_argument("--amalgamate", action="store_true", help="run amalgamate-all for this gadget/agent after pushing the lane")
    parser.add_argument("--verify-command", default="verify.bat", help="verification command used when --amalgamate is set")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return ingest_folder(args)
    except Exception as exc:
        print(f"forks gadget-ingest-folder: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
