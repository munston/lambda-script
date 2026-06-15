#!/usr/bin/env python3
"""Import a pasted JSON patch into the forks submission-object workflow.

Input format:

{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "eddy",
  "title": "Short description",
  "files": [
    {"op": "upsert", "path": "some/file.txt", "encoding": "utf-8", "content": "text\n"},
    {"op": "delete", "path": "old/file.txt"}
  ]
}
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import forks
import replay_ledger
import submission_object

JSON_FORMAT = "LS_FORK_JSON_PATCH_V1"
IMPORT_DIR = "json-imports"


def import_worktree(root: Path, agent: str) -> Path:
    return root / forks.FORKS_DIR / IMPORT_DIR / forks.normalize_agent(agent)


def remove_worktree(root: Path, work: Path) -> None:
    if work.exists():
        forks.git(["worktree", "remove", "--force", str(work)], root, check=False)
    if work.exists():
        shutil.rmtree(work)
    forks.git(["worktree", "prune"], root, check=False)


def load_payload(path: str | None) -> dict[str, Any]:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    data = json.loads(text)
    if data.get("format") != JSON_FORMAT:
        raise RuntimeError(f"expected format {JSON_FORMAT}")
    if not isinstance(data.get("files"), list):
        raise RuntimeError("JSON patch must contain a files array")
    return data


def clean_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("file path must be a non-empty string")
    normal = raw.replace("\\", "/")
    if ":" in normal:
        raise RuntimeError(f"refusing path with drive or scheme: {raw}")
    posix = PurePosixPath(normal)
    if posix.is_absolute():
        raise RuntimeError(f"refusing absolute path: {raw}")
    parts = posix.parts
    if any(part in ("", ".", "..") for part in parts):
        raise RuntimeError(f"refusing unsafe path: {raw}")
    if parts and parts[0] == ".git":
        raise RuntimeError(f"refusing .git path: {raw}")
    return str(posix)


def apply_file_ops(work: Path, files: list[dict[str, Any]]) -> None:
    for item in files:
        op = item.get("op")
        path = clean_path(item.get("path"))
        target = work / path

        if op == "upsert":
            encoding = item.get("encoding", "utf-8")
            if encoding != "utf-8":
                raise RuntimeError(f"unsupported encoding for {path}: {encoding}")
            content = item.get("content")
            if not isinstance(content, str):
                raise RuntimeError(f"upsert requires string content: {path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            continue

        if op == "delete":
            if not target.exists():
                raise RuntimeError(f"delete target does not exist: {path}")
            if target.is_dir():
                raise RuntimeError(f"delete target is a directory, not a file: {path}")
            target.unlink()
            continue

        raise RuntimeError(f"unsupported file op for {path}: {op}")


def commit_candidate(work: Path, agent: str, title: str) -> bool:
    forks.git(["add", "-A"], work)
    if not forks.git_text(["diff", "--cached", "--name-status"], work):
        return False
    message = f"Import {agent} JSON submission"
    if title:
        message += f": {title}"
    forks.git(
        ["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", message],
        work,
    )
    return True


def fetch_target(root: Path, target_ref: str) -> None:
    forks.git(["fetch", "--prune", "origin"], root)
    if not forks.ref_exists(root, target_ref):
        raise RuntimeError(f"missing target ref after fetch: {target_ref}")


def make_submission(root: Path, agent: str, data: dict[str, Any], target_ref: str = forks.MAIN_REF) -> dict[str, Any]:
    fetch_target(root, target_ref)
    agent = forks.normalize_agent(agent)

    declared_agent = data.get("agent")
    if declared_agent is not None and forks.normalize_agent(str(declared_agent)) != agent:
        raise RuntimeError(f"agent mismatch: command says {agent}, JSON says {declared_agent}")

    work = import_worktree(root, agent)
    remove_worktree(root, work)
    forks.git(["worktree", "add", "--detach", str(work), target_ref], root)

    apply_file_ops(work, data["files"])
    ledger_result = replay_ledger.append_entry(work, agent, data, target_ref)
    if ledger_result.get("appended"):
        print(f"replay ledger: appended {ledger_result['path']}#{ledger_result['entry']['sequence']}")
    else:
        print(f"replay ledger: reused {ledger_result['path']}#{ledger_result['entry']['sequence']}")

    if not commit_candidate(work, agent, str(data.get("title", ""))):
        raise RuntimeError("JSON patch produced no file changes")

    files = forks.changed_files(work, "HEAD", target_ref)
    blocked = forks.guard_forbidden_paths(files)
    if blocked:
        raise RuntimeError("refusing submission touching forbidden paths: " + ", ".join(blocked))

    patch_text = forks.git(["diff", "--binary", target_ref, "HEAD"], work).stdout
    source_snapshot = forks.compact_snapshot(work, "HEAD")
    base_snapshot = forks.compact_snapshot(root, target_ref)
    ahead, behind = forks.ahead_behind(work, "HEAD", target_ref)

    return {
        "format": submission_object.SUBMISSION_FORMAT,
        "agent": agent,
        "agent_branch": forks.agent_branch(agent),
        "target_ref": target_ref,
        "target_snapshot_at_capture": base_snapshot,
        "source_ref": f"json-import:{data.get('title', agent)}",
        "source_snapshot": source_snapshot,
        "source_commit": source_snapshot["commit"],
        "base_snapshot": base_snapshot,
        "current_main_snapshot_at_capture": forks.compact_snapshot(root, forks.MAIN_REF),
        "current_target_snapshot_at_capture": base_snapshot,
        "base_main_commit": base_snapshot["commit"],
        "base_main_tree": base_snapshot["tree"],
        "base_main_manifest_hash": base_snapshot["manifest_hash"],
        "base_target_commit": base_snapshot["commit"],
        "base_target_tree": base_snapshot["tree"],
        "base_target_manifest_hash": base_snapshot["manifest_hash"],
        "expected_result_snapshot_on_original_base": source_snapshot,
        "patch_sha256": forks.sha256_text(patch_text),
        "json_patch_sha256": replay_ledger.json_sha256(data),
        "replay_ledger": ledger_result,
        "ahead": ahead,
        "behind": behind,
        "state_at_capture": forks.classify(ahead, behind),
        "changed_files": files,
        "patch": patch_text,
        "created_at": forks.now_iso(),
        "json_patch_title": data.get("title", ""),
    }


def cmd_import(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    payload = load_payload(args.file)
    submission = make_submission(root, args.agent, payload, args.target_ref)
    submission_object.write_submission(root, args.agent, submission)

    print(f"imported JSON submission for {submission['agent']}")
    print(f"target={submission['target_ref']}")
    print(f"wrote {submission_object.submission_path(root, args.agent)}")
    print(f"files={len(submission['changed_files'])} ahead={submission['ahead']} behind={submission['behind']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks import-json")
    parser.add_argument("--target-ref", default=forks.MAIN_REF, help="target integration ref; defaults to origin/main")
    parser.add_argument("agent")
    parser.add_argument("file", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return cmd_import(args)
    except Exception as exc:
        print(f"forks import-json: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
