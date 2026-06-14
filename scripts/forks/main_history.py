#!/usr/bin/env python3
"""Main-branch version receipts.

A main version receipt is a small commit added immediately before a push to
`main`. It records the accepted patch/promotion as a replay marker. The Git
history remains the canonical archive; these receipts provide a stable,
machine-readable index over that history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import forks

HISTORY_DIR = Path("docs/forks/main-history")
PATCH_DIR = HISTORY_DIR / "patches"
INDEX_PATH = HISTORY_DIR / "index.json"
FORMAT = "LS_MAIN_HISTORY_V1"


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _index_default() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "description": "Replay index for accepted pushes to main.",
        "entries": [],
    }


def _next_number(index: dict[str, Any]) -> int:
    entries = index.get("entries", [])
    max_n = 0
    for entry in entries:
        try:
            max_n = max(max_n, int(entry.get("number", 0)))
        except Exception:
            pass
    return max_n + 1


def _commit(work: Path, message: str) -> None:
    forks.git(["add", str(INDEX_PATH), str(PATCH_DIR)], work)
    if not forks.git_text(["diff", "--cached", "--name-status"], work):
        return
    forks.git(
        ["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", message],
        work,
    )


def stamp_main_version(
    work: Path,
    *,
    kind: str,
    agent: str,
    title: str,
    base_ref: str,
    source_ref: str,
    changed_files: list[str],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a main-history receipt commit on top of the current worktree HEAD."""
    index = _read_json(work / INDEX_PATH, _index_default())
    if index.get("format") != FORMAT:
        raise RuntimeError(f"unsupported main history format in {INDEX_PATH}")

    number = _next_number(index)
    version = f"main-{number:06d}"
    receipt_path = PATCH_DIR / f"{version}.json"

    source_head = forks.git(["rev-parse", "HEAD"], work).stdout.strip()
    source_tree = forks.git(["rev-parse", "HEAD^{tree}"], work).stdout.strip()
    base_commit = forks.git(["rev-parse", base_ref], work).stdout.strip()
    receipt = {
        "format": FORMAT,
        "version": version,
        "number": number,
        "kind": kind,
        "agent": agent,
        "title": title,
        "created_at": forks.now_iso(),
        "base_ref": base_ref,
        "base_commit": base_commit,
        "source_ref": source_ref,
        "source_head_before_receipt": source_head,
        "source_tree_before_receipt": source_tree,
        "changed_files": list(changed_files),
        "metadata": metadata or {},
    }

    _write_json(work / receipt_path, receipt)

    entries = index.setdefault("entries", [])
    entries.append({
        "version": version,
        "number": number,
        "kind": kind,
        "agent": agent,
        "title": title,
        "receipt": str(receipt_path).replace("\\", "/"),
        "base_commit": base_commit,
        "source_head_before_receipt": source_head,
        "created_at": receipt["created_at"],
    })
    _write_json(work / INDEX_PATH, index)

    _commit(work, f"Record main version: {version}")
    receipt["receipt_commit"] = forks.git(["rev-parse", "HEAD"], work).stdout.strip()
    return receipt
