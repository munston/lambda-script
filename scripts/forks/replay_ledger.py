#!/usr/bin/env python3
"""Committed replay ledger support for Forks JSON submissions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import forks

LEDGER_FORMAT = "LS_FORK_REPLAY_LEDGER_V1"
ENTRY_FORMAT = "LS_FORK_REPLAY_LEDGER_ENTRY_V1"
LEDGER_ROOT = "forks/replay-ledger"


def safe_token(raw: str) -> str:
    value = str(raw).strip().replace("\\", "/")
    if not value or value in {".", ".."}:
        raise RuntimeError(f"unsafe ledger token: {raw!r}")
    if ":" in value:
        raise RuntimeError(f"unsafe ledger token: {raw!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RuntimeError(f"unsafe ledger token: {raw!r}")
    return "_".join(parts)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def json_sha256(value: Any) -> str:
    return forks.sha256_text(canonical_json(value))


def target_descriptor(payload: dict[str, Any], target_ref: str) -> dict[str, Any]:
    target = payload.get("target")
    if isinstance(target, dict):
        kind = target.get("kind", "gadget")
        if kind == "gadget" and isinstance(target.get("gizmo"), str):
            gadget = target.get("gadget") or target.get("lane")
            if isinstance(gadget, str) and gadget:
                return {
                    "kind": "gadget",
                    "gizmo": target["gizmo"],
                    "gadget": gadget,
                    "target_ref": target_ref,
                }
    return {
        "kind": "ref",
        "target_ref": target_ref,
    }


def ledger_relpath(agent: str, target: dict[str, Any]) -> str:
    clean_agent = safe_token(agent)
    if target.get("kind") == "gadget":
        gizmo = safe_token(str(target.get("gizmo", "")))
        gadget = safe_token(str(target.get("gadget", "")))
        return f"{LEDGER_ROOT}/gadgets/{gizmo}/{gadget}/{clean_agent}.json"
    ref = safe_token(str(target.get("target_ref", "unknown")))
    return f"{LEDGER_ROOT}/refs/{ref}/{clean_agent}.json"


def file_fingerprint(item: dict[str, Any]) -> dict[str, Any]:
    op = item.get("op")
    path = item.get("path")
    out: dict[str, Any] = {
        "op": op,
        "path": path,
    }
    if op == "upsert":
        content = item.get("content")
        encoding = item.get("encoding", "utf-8")
        out["encoding"] = encoding
        out["content_sha256"] = forks.sha256_text(content if isinstance(content, str) else "")
        out["content_length"] = len(content) if isinstance(content, str) else None
    return out


def patch_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    files = payload.get("files", [])
    return {
        "json_patch_sha256": json_sha256(payload),
        "title": payload.get("title", ""),
        "agent": payload.get("agent"),
        "file_count": len(files) if isinstance(files, list) else 0,
        "files": [file_fingerprint(item) for item in files] if isinstance(files, list) else [],
    }


def empty_ledger(agent: str, target: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": LEDGER_FORMAT,
        "agent": forks.normalize_agent(agent),
        "target": target,
        "created_at": forks.now_iso(),
        "updated_at": forks.now_iso(),
        "next_sequence": 1,
        "entries": [],
    }


def read_ledger(path: Path, agent: str, target: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return empty_ledger(agent, target)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != LEDGER_FORMAT:
        raise RuntimeError(f"invalid replay ledger format: {path}")
    if data.get("agent") != forks.normalize_agent(agent):
        raise RuntimeError(f"replay ledger agent mismatch: {path}")
    if not isinstance(data.get("entries"), list):
        raise RuntimeError(f"invalid replay ledger entries: {path}")
    if not isinstance(data.get("next_sequence"), int):
        data["next_sequence"] = len(data["entries"]) + 1
    return data


def find_entry(ledger: dict[str, Any], json_patch_sha256: str) -> dict[str, Any] | None:
    for entry in ledger.get("entries", []):
        if entry.get("json_patch_sha256") == json_patch_sha256:
            return entry
    return None


def append_entry(work: Path, agent: str, payload: dict[str, Any], target_ref: str) -> dict[str, Any]:
    agent = forks.normalize_agent(agent)
    target = target_descriptor(payload, target_ref)
    relpath = ledger_relpath(agent, target)
    path = work / relpath
    fingerprint = patch_fingerprint(payload)
    ledger = read_ledger(path, agent, target)
    existing = find_entry(ledger, fingerprint["json_patch_sha256"])
    if existing is not None:
        return {
            "path": relpath,
            "entry": existing,
            "appended": False,
            "reason": "json patch fingerprint already present",
        }
    sequence = int(ledger.get("next_sequence", len(ledger.get("entries", [])) + 1))
    entry = {
        "format": ENTRY_FORMAT,
        "sequence": sequence,
        "agent": agent,
        "target": target,
        "title": fingerprint["title"],
        "json_patch_sha256": fingerprint["json_patch_sha256"],
        "file_count": fingerprint["file_count"],
        "file_fingerprints": fingerprint["files"],
        "target_ref_at_capture": target_ref,
        "created_at": forks.now_iso(),
    }
    ledger["target"] = target
    ledger["updated_at"] = forks.now_iso()
    ledger["next_sequence"] = sequence + 1
    ledger["entries"].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "path": relpath,
        "entry": entry,
        "appended": True,
    }


def ledger_fingerprint(ledger: dict[str, Any]) -> str:
    stable = {
        "format": ledger.get("format"),
        "agent": ledger.get("agent"),
        "target": ledger.get("target"),
        "entries": ledger.get("entries", []),
    }
    return json_sha256(stable)
