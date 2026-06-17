#!/usr/bin/env python3
r"""Submit a local folder to a repository agent lane.

This is the repository-agent counterpart to gadget-creation-<agent>.bat.
It copies a folder into an agents/<agent> lane, commits it, and pushes that
lane. It does not amalgamate by default; agents can publish large checkpoints
without mutating main until signover.
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import sys
from pathlib import Path, PurePosixPath

import forks

VALID_AGENTS = set(forks.AGENTS)
DEFAULT_EXCLUDES = (
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".stack-work",
    "dist-newstyle",
    "node_modules",
    "*.hi",
    "*.o",
    "*.dyn_hi",
    "*.dyn_o",
)


def clean_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("destination path must be a non-empty string")
    normal = raw.replace("\\", "/").strip("/")
    if ":" in normal:
        raise RuntimeError(f"refusing destination path with drive or scheme: {raw}")
    posix = PurePosixPath(normal)
    if posix.is_absolute():
        raise RuntimeError(f"refusing absolute destination path: {raw}")
    if any(part in ("", ".", "..") for part in posix.parts):
        raise RuntimeError(f"refusing unsafe destination path: {raw}")
    if posix.parts and posix.parts[0] == ".git":
        raise RuntimeError(f"refusing .git destination path: {raw}")
    return str(posix)


def repo_rel_or_default(root: Path, source: Path) -> str:
    try:
        rel = source.resolve().relative_to(root.resolve())
        return str(rel).replace("\\", "/")
    except ValueError:
        return "projects/" + source.name


def ignore_factory(patterns: list[str]):
    def ignore(_directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            for pattern in patterns:
                if fnmatch.fnmatch(name, pattern):
                    ignored.add(name)
                    break
        return ignored
    return ignore


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
        if len(parts) >= 2:
            item = {"status": parts[0], "path": parts[-1]}
            if parts[0].startswith("R") and len(parts) >= 3:
                item["old_path"] = parts[1]
            files.append(item)
    return files


def choose_base(root: Path, agent: str, allow_existing_lane_work: bool) -> tuple[str, str]:
    branch = forks.agent_branch(agent)
    remote = "origin/" + branch
    if forks.ref_exists(root, remote):
        ahead, behind = forks.ahead_behind(root, remote, forks.MAIN_REF)
        state = forks.classify(ahead, behind)
        print(f"{branch}: remote state={state} ahead={ahead} behind={behind}")
        if ahead > 0:
            if not allow_existing_lane_work:
                raise RuntimeError(
                    f"{branch} already has unique work; pass --allow-existing-lane-work "
                    "to layer this folder checkpoint on top"
                )
            return remote, state
        return forks.MAIN_REF, state
    if forks.ref_exists(root, branch):
        ahead, behind = forks.ahead_behind(root, branch, forks.MAIN_REF)
        state = forks.classify(ahead, behind)
        print(f"{branch}: local state={state} ahead={ahead} behind={behind}")
        if ahead > 0:
            if not allow_existing_lane_work:
                raise RuntimeError(
                    f"{branch} already has local unique work; pass --allow-existing-lane-work "
                    "to layer this folder checkpoint on top"
                )
            return branch, state
    return forks.MAIN_REF, "missing"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-submit-<agent>.bat",
        description="Copy a local folder into agents/<agent> and push the lane without amalgamating.",
    )
    parser.add_argument("agent", help="configured repository agent lane: ed, edd, eddy, or guy")
    parser.add_argument("source", help="local folder to submit")
    parser.add_argument("--dest", help="destination path in the repository; defaults to repo-relative source path or projects/<folder>")
    parser.add_argument("--message", help="commit message for the agent lane")
    parser.add_argument("--replace", action="store_true", help="remove the destination before copying the source folder")
    parser.add_argument("--allow-existing-lane-work", action="store_true", help="layer this checkpoint on top of existing unique agent-lane work")
    parser.add_argument("--exclude", action="append", default=[], help="additional glob pattern to exclude; may be repeated")
    parser.add_argument("--no-default-excludes", action="store_true", help="disable default excludes")
    parser.add_argument("--follow-symlinks", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    agent = forks.normalize_agent(args.agent)
    if agent not in VALID_AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of: {', '.join(forks.AGENTS)}")
    root = forks.repo_root()
    forks.ensure_dirs(root)
    forks.fetch_main(root)

    source = Path(args.source)
    if not source.exists():
        raise RuntimeError(f"source folder does not exist: {source}")
    if not source.is_dir():
        raise RuntimeError(f"source is not a folder: {source}")

    dest = clean_path(args.dest or repo_rel_or_default(root, source))
    message = args.message or f"Submit {source.name} to agents/{agent}"
    branch = forks.agent_branch(agent)
    full_remote = "refs/heads/" + branch
    base_ref, base_state = choose_base(root, agent, args.allow_existing_lane_work)

    print("repository agent folder submission")
    print(f"  agent: {agent}")
    print(f"  source: {source}")
    print(f"  dest: {dest}")
    print(f"  base: {base_ref} ({base_state})")
    print("  amalgamate: no")

    work = root / forks.FORKS_DIR / "agent-folder-submit" / agent
    remove_worktree(root, work)
    forks.git(["worktree", "add", "--detach", str(work), base_ref], root)
    try:
        target = work / dest
        if args.replace and target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        patterns = [] if args.no_default_excludes else list(DEFAULT_EXCLUDES)
        patterns.extend(args.exclude)
        shutil.copytree(
            source,
            target,
            dirs_exist_ok=True,
            ignore=ignore_factory(patterns),
            symlinks=args.follow_symlinks,
        )

        forks.git(["add", "-A"], work)
        status = forks.git_text(["diff", "--cached", "--name-status"], work)
        if not status:
            print(f"{branch}: no file changes")
            return 0
        changed = parse_name_status(status)
        blocked = forks.guard_forbidden_paths(changed)
        if blocked:
            raise RuntimeError("refusing submission touching forbidden paths: " + ", ".join(blocked))

        forks.git(["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", message], work)
        print("changed files:")
        for item in changed[:80]:
            print(f"  {item['status']} {item['path']}")
        if len(changed) > 80:
            print(f"  ... {len(changed) - 80} more")
        forks.git(["push", "origin", "HEAD:" + full_remote], work)
        forks.git(["fetch", "--prune", "origin"], root)
        print(f"{branch}: pushed {forks.short_commit(root, 'origin/' + branch)}")
        return 0
    finally:
        remove_worktree(root, work)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"agent-folder-submit: {exc}", file=sys.stderr)
        raise SystemExit(1)
