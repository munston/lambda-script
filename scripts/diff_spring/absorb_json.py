#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

FORMAT = "LS_JSON_PATCH_V1"
DEFAULT_MESSAGE = "Absorb diff spring"

MESSAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,_:;()/+\-]{0,119}$")
KEYLIKE_RE = re.compile(
    r"(^|/)(id_ed25519|id_ed25519\.pub|id_rsa|id_rsa\.pub|.*\.pem|.*\.ppk|.*\.keyfile|.*\.keyfile\.pub|key\.keyfile|key\.keyfile\.pub)$",
    re.IGNORECASE,
)


class DiffSpringError(Exception):
    pass


def git_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise DiffSpringError("not inside a git repository")
    raw = proc.stdout.strip()
    try:
        cygpath = subprocess.run(
            ["cygpath", "-w", raw],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if cygpath.returncode == 0 and cygpath.stdout.strip():
            return Path(cygpath.stdout.strip())
    except FileNotFoundError:
        pass
    return Path(raw)


def spring_dirs(root: Path) -> tuple[Path, Path, Path]:
    spring = root / "spring" / "diff"
    return spring / "drop", spring / "archive", spring / "work"


def find_single_json(drop: Path) -> Path:
    drop.mkdir(parents=True, exist_ok=True)
    entries = [p for p in drop.iterdir() if p.name != ".gitignore"]
    if not entries:
        raise DiffSpringError("no .json patch in spring/diff/drop")
    bad = [p.name for p in entries if not p.is_file() or p.suffix.lower() != ".json"]
    if bad:
        raise DiffSpringError(f"non-json entries in drop: {', '.join(bad)}")
    if len(entries) > 1:
        raise DiffSpringError("more than one .json patch in spring/diff/drop")
    return entries[0]


def safe_relative_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise DiffSpringError("file path must be a non-empty string")
    path = raw.replace("\\", "/")
    if path.startswith("/") or re.match(r"^[A-Za-z]:/", path):
        raise DiffSpringError(f"absolute path rejected: {raw}")
    pure = PurePosixPath(path)
    parts = pure.parts
    if not parts or parts == (".",):
        raise DiffSpringError(f"empty path rejected: {raw}")
    if any(part in ("", ".", "..") for part in parts):
        raise DiffSpringError(f"path escape rejected: {raw}")
    clean = "/".join(parts)
    if clean.startswith(".git/") or clean == ".git":
        raise DiffSpringError(f".git path rejected: {raw}")
    if clean.startswith("spring/diff/") or clean == "spring/diff":
        raise DiffSpringError(f"diff spring self-write rejected: {raw}")
    if clean.startswith("spring/tarball/") or clean == "spring/tarball":
        raise DiffSpringError(f"tarball spring self-write rejected: {raw}")
    if KEYLIKE_RE.search(clean):
        raise DiffSpringError(f"key-like path rejected: {raw}")
    return clean


def safe_target(root: Path, relative_name: str) -> Path:
    target = (root / relative_name).resolve()
    root_resolved = root.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise DiffSpringError(f"path escapes repository: {relative_name}") from exc
    return target


def load_patch(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DiffSpringError(f"invalid JSON patch: {path}") from exc
    if not isinstance(data, dict):
        raise DiffSpringError("top-level JSON patch must be an object")
    if data.get("format") != FORMAT:
        raise DiffSpringError(f"format must be {FORMAT}")
    message = data.get("commit_message")
    if not isinstance(message, str) or not message.strip():
        raise DiffSpringError("commit_message must be a non-empty string")
    if not MESSAGE_RE.match(message.strip()):
        raise DiffSpringError("commit_message contains unsupported characters or is too long")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise DiffSpringError("files must be a non-empty list")
    return data


def commit_message(data: dict[str, Any]) -> str:
    raw = data["commit_message"].strip()
    if len(raw) > 120:
        raise DiffSpringError("commit_message is too long")
    return raw


def validate_patch(data: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for index, entry in enumerate(data["files"]):
        if not isinstance(entry, dict):
            raise DiffSpringError(f"files[{index}] must be an object")
        path = safe_relative_path(entry.get("path"))
        action = entry.get("action")
        if action not in ("create", "replace", "modify", "delete"):
            raise DiffSpringError(f"{path}: unsupported action {action!r}")
        if action in ("create", "replace"):
            if "content" not in entry or not isinstance(entry["content"], str):
                raise DiffSpringError(f"{path}: {action} requires string content")
        if action == "modify":
            edits = entry.get("edits")
            if not isinstance(edits, list) or not edits:
                raise DiffSpringError(f"{path}: modify requires non-empty edits")
            for edit_index, edit in enumerate(edits):
                if not isinstance(edit, dict):
                    raise DiffSpringError(f"{path}: edits[{edit_index}] must be an object")
                if edit.get("type") != "replace_exact":
                    raise DiffSpringError(f"{path}: only replace_exact edits are supported")
                if not isinstance(edit.get("old"), str) or not isinstance(edit.get("new"), str):
                    raise DiffSpringError(f"{path}: replace_exact requires string old and new")
                if edit["old"] == "":
                    raise DiffSpringError(f"{path}: replace_exact old text cannot be empty")
        seen.append(path)
    if len(seen) != len(set(seen)):
        raise DiffSpringError("patch contains duplicate file paths")
    return seen


def ensure_clean_for_patch() -> None:
    for args in (["git", "diff", "--quiet"], ["git", "diff", "--cached", "--quiet"]):
        proc = subprocess.run(args)
        if proc.returncode != 0:
            raise DiffSpringError("tracked changes already exist; commit/stash/revert them before absorbing a diff spring patch")


def apply_entry(root: Path, entry: dict[str, Any]) -> None:
    path = safe_relative_path(entry["path"])
    target = safe_target(root, path)
    action = entry["action"]

    if action == "create":
        if target.exists():
            raise DiffSpringError(f"{path}: create refused because file exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(entry["content"], encoding="utf-8", newline="")
        return

    if action == "replace":
        if not target.exists() or not target.is_file():
            raise DiffSpringError(f"{path}: replace refused because file does not exist")
        target.write_text(entry["content"], encoding="utf-8", newline="")
        return

    if action == "modify":
        if not target.exists() or not target.is_file():
            raise DiffSpringError(f"{path}: modify refused because file does not exist")
        text = target.read_text(encoding="utf-8")
        for edit in entry["edits"]:
            old = edit["old"]
            new = edit["new"]
            count = text.count(old)
            if count != 1:
                raise DiffSpringError(f"{path}: replace_exact expected exactly one match, found {count}")
            text = text.replace(old, new, 1)
        target.write_text(text, encoding="utf-8", newline="")
        return

    if action == "delete":
        if not target.exists() or not target.is_file():
            raise DiffSpringError(f"{path}: delete refused because file does not exist")
        target.unlink()
        return

    raise DiffSpringError(f"{path}: unsupported action {action!r}")


def archive_patch(patch_file: Path, archive: Path) -> Path:
    archive.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived = archive / f"{timestamp}-{patch_file.name}"
    shutil.move(str(patch_file), str(archived))
    return archived


def absorb(root: Path, patch_file: Path, archive: Path) -> str:
    data = load_patch(patch_file)
    paths = validate_patch(data)
    ensure_clean_for_patch()

    for entry in data["files"]:
        apply_entry(root, entry)

    archived = archive_patch(patch_file, archive)
    message = commit_message(data)
    print(f"OK absorbed {len(paths)} file operation(s)")
    print(f"ARCHIVED: {archived}")
    print(f"COMMIT_MESSAGE: {message}")
    return message


def self_test() -> None:
    sample = {
        "format": FORMAT,
        "commit_message": "Add sample",
        "files": [
            {
                "path": "docs/sample.txt",
                "action": "create",
                "content": "sample\n"
            }
        ]
    }
    paths = validate_patch(sample)
    assert paths == ["docs/sample.txt"]
    assert commit_message(sample) == "Add sample"
    print("OK diff spring parser self-test")


def main() -> None:
    parser = argparse.ArgumentParser(description="Absorb exactly one LS_JSON_PATCH_V1 file from the LambdaScript diff spring.")
    parser.add_argument("--message-only", action="store_true", help="Print the commit message for the pending patch and exit")
    parser.add_argument("--list", action="store_true", help="List file paths in the pending patch and exit")
    parser.add_argument("--self-test", action="store_true", help="Run parser self-test")
    args = parser.parse_args()

    try:
        if args.self_test:
            self_test()
            return

        root = git_root()
        drop, archive, _work = spring_dirs(root)
        patch_file = find_single_json(drop)
        data = load_patch(patch_file)
        paths = validate_patch(data)

        if args.message_only:
            print(commit_message(data))
            return
        if args.list:
            for path in paths:
                print(path)
            return

        absorb(root, patch_file, archive)
    except DiffSpringError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
