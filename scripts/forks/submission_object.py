#!/usr/bin/env python3
"""Replayable submission objects for forks.

This module is intentionally separate from branch sync. It captures pending work
into .forks/submissions and replays that saved patch onto current main.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import forks

SUBMISSION_DIR = "submissions"


def submission_path(root: Path, agent: str) -> Path:
    return root / forks.FORKS_DIR / SUBMISSION_DIR / f"{forks.normalize_agent(agent)}.json"


def ensure_dirs(root: Path) -> None:
    forks.ensure_dirs(root)
    (root / forks.FORKS_DIR / SUBMISSION_DIR).mkdir(parents=True, exist_ok=True)


def run_forks(root: Path, args: list[str]) -> int:
    script = Path(__file__).with_name("forks.py")
    proc = subprocess.run([sys.executable, str(script), *args], cwd=str(root), text=True)
    return proc.returncode


def compatible_patch(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "LS_FORK_PATCH_V1",
        "agent": data["agent"],
        "agent_branch": data["agent_branch"],
        "source_ref": data["source_ref"],
        "base_snapshot": data["base_snapshot"],
        "source_snapshot": data["source_snapshot"],
        "current_main_snapshot_at_export": data["current_main_snapshot_at_capture"],
        "base_main_commit": data["base_main_commit"],
        "base_main_tree": data["base_main_tree"],
        "base_main_manifest_hash": data["base_main_manifest_hash"],
        "expected_result_snapshot_on_original_base": data["expected_result_snapshot_on_original_base"],
        "patch_sha256": data["patch_sha256"],
        "ahead": data["ahead"],
        "behind": data["behind"],
        "changed_files": data["changed_files"],
        "patch": data["patch"],
        "created_at": data["created_at"],
        "submission_source": "LS_FORK_SUBMISSION_V1",
    }


def write_submission(root: Path, agent: str, data: dict[str, Any]) -> None:
    forks.write_json(submission_path(root, agent), data)
    forks.write_json(forks.patch_path(root, agent), compatible_patch(data))


def load_submission(root: Path, agent: str) -> dict[str, Any]:
    path = submission_path(root, agent)
    if not path.exists():
        raise RuntimeError(f"missing submission: {path}; run forks capture {agent}")
    data = forks.read_json(path)
    if data.get("format") != "LS_FORK_SUBMISSION_V1":
        raise RuntimeError(f"invalid submission format: {path}")
    if data.get("patch_sha256") != forks.sha256_text(data.get("patch", "")):
        raise RuntimeError("submission patch hash mismatch")
    return data


def make_submission(root: Path, agent: str, source_ref: str | None) -> dict[str, Any]:
    forks.fetch_main(root)
    ref = source_ref or forks.best_agent_ref(root, agent)
    base = forks.merge_base(root, forks.MAIN_REF, ref)
    if not base:
        raise RuntimeError(f"cannot find merge-base between {forks.MAIN_REF} and {ref}")
    patch_text = forks.git(["diff", "--binary", base, ref], root).stdout
    files = forks.changed_files(root, ref, base)
    if not patch_text.strip() or not files:
        raise RuntimeError(f"source ref has no captured work: {ref}")
    ahead, behind = forks.ahead_behind(root, ref)
    base_snapshot = forks.compact_snapshot(root, base)
    source_snapshot = forks.compact_snapshot(root, ref)
    current_main = forks.compact_snapshot(root, forks.MAIN_REF)
    return {
        "format": "LS_FORK_SUBMISSION_V1",
        "agent": forks.normalize_agent(agent),
        "agent_branch": forks.agent_branch(agent),
        "source_ref": ref,
        "base_snapshot": base_snapshot,
        "source_snapshot": source_snapshot,
        "current_main_snapshot_at_capture": current_main,
        "base_main_commit": base_snapshot["commit"],
        "base_main_tree": base_snapshot["tree"],
        "base_main_manifest_hash": base_snapshot["manifest_hash"],
        "expected_result_snapshot_on_original_base": source_snapshot,
        "patch_sha256": forks.sha256_text(patch_text),
        "ahead": ahead,
        "behind": behind,
        "changed_files": files,
        "patch": patch_text,
        "created_at": forks.now_iso(),
    }


def cmd_capture(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    ensure_dirs(root)
    data = make_submission(root, args.agent, args.from_ref)
    blocked = forks.guard_forbidden_paths(data["changed_files"])
    if blocked and not args.allow_forbidden:
        raise RuntimeError("refusing submission touching forbidden paths: " + ", ".join(blocked))
    write_submission(root, args.agent, data)
    print(f"wrote {submission_path(root, args.agent)}")
    print(f"agent={data['agent']} source={data['source_ref']} ahead={data['ahead']} behind={data['behind']} files={len(data['changed_files'])}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    ensure_dirs(root)
    data = load_submission(root, args.agent)
    forks.fetch_main(root)
    current = forks.compact_snapshot(root, forks.MAIN_REF)
    result = {
        "agent": data["agent"],
        "source_ref": data["source_ref"],
        "source_commit": data["source_snapshot"]["commit"],
        "base_matches_current_main": forks.snapshots_match(data["base_snapshot"], current),
        "files": data["changed_files"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    ensure_dirs(root)
    data = load_submission(root, args.agent)
    forks.write_json(forks.patch_path(root, args.agent), compatible_patch(data))
    cmd = ["stage", args.agent]
    if args.rebase_stale:
        cmd.append("--rebase-stale")
    if args.allow_forbidden:
        cmd.append("--allow-forbidden")
    return run_forks(root, cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks submission")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("capture")
    p.add_argument("agent")
    p.add_argument("--from-ref")
    p.add_argument("--allow-forbidden", action="store_true")
    p.set_defaults(func=cmd_capture)
    p = sub.add_parser("status")
    p.add_argument("agent")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("replay")
    p.add_argument("agent")
    p.add_argument("--rebase-stale", action="store_true")
    p.add_argument("--allow-forbidden", action="store_true")
    p.set_defaults(func=cmd_replay)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"forks submission: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
