#!/usr/bin/env python3
"""Dry-run replay planner for committed Forks replay ledgers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import forks
import replay_ledger

PLAN_FORMAT = "LS_FORK_REPLAY_PLAN_V1"
REPLAYABLE_PREFIX_STATES = {"even", "behind-only", "ahead-only", "diverged"}


def git_text(root: Path, args: list[str], default: str = "") -> str:
    proc = forks.git(args, root, check=False)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip()


def normalize_branch_ref(raw: str) -> str:
    ref = raw.strip()
    if ref.startswith("origin/"):
        return ref
    return ref


def remote_ref(branch: str) -> str:
    if branch.startswith("origin/"):
        return branch
    return f"origin/{branch}"


def ref_exists(root: Path, ref: str) -> bool:
    return forks.ref_exists(root, ref)


def list_candidate_refs(root: Path) -> list[str]:
    text = git_text(
        root,
        [
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/heads/agents",
            "refs/remotes/origin/agents",
            "refs/heads/gadgets",
            "refs/remotes/origin/gadgets",
            "refs/heads/gadget-agents",
            "refs/remotes/origin/gadget-agents",
        ],
    )
    found: set[str] = set()
    for raw in text.splitlines():
        ref = normalize_branch_ref(raw)
        if ref == "origin/main" or ref == "main":
            continue
        if ref.startswith("agents/") or ref.startswith("origin/agents/"):
            found.add(ref)
            continue
        if ref.startswith("gadgets/") or ref.startswith("origin/gadgets/"):
            found.add(ref)
            continue
        if ref.startswith("gadget-agents/") or ref.startswith("origin/gadget-agents/"):
            found.add(ref)
            continue
    return sorted(found)


def list_ledger_paths(root: Path, ref: str) -> list[str]:
    if not ref_exists(root, ref):
        return []
    text = git_text(root, ["ls-tree", "-r", "--name-only", ref, replay_ledger.LEDGER_ROOT])
    return sorted(line for line in text.splitlines() if line.endswith(".json"))


def read_json_at_ref(root: Path, ref: str, path: str) -> dict[str, Any] | None:
    if not ref_exists(root, ref):
        return None
    proc = forks.git(["show", f"{ref}:{path}"], root, check=False)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON at {ref}:{path}: {exc}") from exc


def entry_key(entry: dict[str, Any]) -> tuple[Any, Any]:
    return entry.get("sequence"), entry.get("json_patch_sha256")


def longest_matching_prefix(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> int:
    limit = min(len(left), len(right))
    count = 0
    for i in range(limit):
        if entry_key(left[i]) != entry_key(right[i]):
            break
        count += 1
    return count


def entry_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": entry.get("sequence"),
        "title": entry.get("title", ""),
        "json_patch_sha256": entry.get("json_patch_sha256"),
        "file_count": entry.get("file_count", 0),
        "created_at": entry.get("created_at"),
    }


def ledger_summary(ledger: dict[str, Any] | None) -> dict[str, Any]:
    if ledger is None:
        return {
            "present": False,
            "entry_count": 0,
            "next_sequence": 1,
            "ledger_fingerprint": None,
        }
    return {
        "present": True,
        "entry_count": len(ledger.get("entries", [])),
        "next_sequence": ledger.get("next_sequence"),
        "ledger_fingerprint": replay_ledger.ledger_fingerprint(ledger),
    }


def compare_ledger(root: Path, ref: str, ledger_path: str) -> dict[str, Any]:
    main_ledger = read_json_at_ref(root, forks.MAIN_REF, ledger_path)
    branch_ledger = read_json_at_ref(root, ref, ledger_path)
    main_entries = list(main_ledger.get("entries", [])) if main_ledger else []
    branch_entries = list(branch_ledger.get("entries", [])) if branch_ledger else []
    prefix = longest_matching_prefix(main_entries, branch_entries)
    branch_replay = branch_entries[prefix:]
    main_extra = main_entries[prefix:]
    mismatch_at = None
    if prefix < len(main_entries) and prefix < len(branch_entries):
        mismatch_at = {
            "main": entry_summary(main_entries[prefix]),
            "branch": entry_summary(branch_entries[prefix]),
        }
    return {
        "path": ledger_path,
        "main": ledger_summary(main_ledger),
        "branch": ledger_summary(branch_ledger),
        "matching_prefix": prefix,
        "mismatch_at": mismatch_at,
        "branch_entries_to_replay": [entry_summary(item) for item in branch_replay],
        "main_entries_not_on_branch": [entry_summary(item) for item in main_extra],
        "replay_count": len(branch_replay),
        "main_extra_count": len(main_extra),
    }


def classify_replay(row: dict[str, Any]) -> str:
    ledgers = row.get("ledgers", [])
    if not ledgers:
        return "no-ledger"
    if any(item.get("mismatch_at") for item in ledgers):
        return "fingerprint-divergence"
    if any(item.get("main_extra_count", 0) > 0 for item in ledgers):
        return "main-has-unseen-ledger-entries"
    if any(item.get("replay_count", 0) > 0 for item in ledgers):
        return "replay-needed"
    return "no-replay-needed"


def plan_ref(root: Path, ref: str) -> dict[str, Any]:
    ahead, behind = forks.ahead_behind(root, ref, forks.MAIN_REF)
    state = forks.classify(ahead, behind)
    main_paths = set(list_ledger_paths(root, forks.MAIN_REF))
    branch_paths = set(list_ledger_paths(root, ref))
    paths = sorted(main_paths | branch_paths)
    ledgers = [compare_ledger(root, ref, path) for path in paths]
    row = {
        "ref": ref,
        "remote_ref": remote_ref(ref) if not ref.startswith("origin/") else ref,
        "head": forks.short_commit(root, ref) if ref_exists(root, ref) else None,
        "state_against_main": state,
        "ahead": ahead,
        "behind": behind,
        "ledger_count": len(ledgers),
        "ledgers": ledgers,
        "would_rewind_to": forks.MAIN_REF,
        "would_push": False,
        "destructive": False,
    }
    row["classification"] = classify_replay(row)
    row["total_replay_count"] = sum(item.get("replay_count", 0) for item in ledgers)
    row["total_main_extra_count"] = sum(item.get("main_extra_count", 0) for item in ledgers)
    row["safe_for_destructive_replay"] = (
        row["classification"] in {"replay-needed", "no-replay-needed"}
        and state in REPLAYABLE_PREFIX_STATES
        and all(item.get("mismatch_at") is None for item in ledgers)
    )
    return row


def build_plan(root: Path, refs: list[str], include_empty: bool) -> dict[str, Any]:
    forks.fetch_main(root)
    main_snapshot = forks.compact_snapshot(root, forks.MAIN_REF)
    rows = []
    for ref in refs:
        if not ref_exists(root, ref):
            alt = remote_ref(ref)
            if ref_exists(root, alt):
                ref = alt
            else:
                rows.append({
                    "ref": ref,
                    "exists": False,
                    "classification": "missing-ref",
                    "safe_for_destructive_replay": False,
                })
                continue
        row = plan_ref(root, ref)
        row["exists"] = True
        if include_empty or row.get("ledger_count", 0) > 0 or row.get("state_against_main") != "even":
            rows.append(row)
    return {
        "format": PLAN_FORMAT,
        "created_at": forks.now_iso(),
        "main": main_snapshot,
        "ref_count": len(rows),
        "refs": rows,
    }


def print_text(plan: dict[str, Any]) -> None:
    main = plan["main"]
    print(f"main {main['commit'][:12]} tree {main['tree']} manifest {main['manifest_hash']}")
    for row in plan["refs"]:
        if not row.get("exists", True):
            print(f"{row['ref']}: missing")
            continue
        print(
            f"{row['ref']}: {row['state_against_main']} "
            f"ahead={row['ahead']} behind={row['behind']} "
            f"classification={row['classification']} "
            f"replay={row['total_replay_count']} "
            f"main-extra={row['total_main_extra_count']} "
            f"safe={row['safe_for_destructive_replay']}"
        )
        for item in row.get("ledgers", []):
            if item.get("replay_count") or item.get("main_extra_count") or item.get("mismatch_at"):
                print(
                    f"  {item['path']}: prefix={item['matching_prefix']} "
                    f"replay={item['replay_count']} main-extra={item['main_extra_count']}"
                )
                if item.get("mismatch_at"):
                    print("    fingerprint divergence at matching prefix boundary")
                for entry in item.get("branch_entries_to_replay", []):
                    seq = entry.get("sequence")
                    title = entry.get("title", "")
                    digest = str(entry.get("json_patch_sha256", ""))[:12]
                    print(f"    replay #{seq} {digest} {title}")


def cmd_plan(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    refs = args.ref or list_candidate_refs(root)
    plan = build_plan(root, refs, args.include_empty)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print_text(plan)
    unsafe = [row for row in plan["refs"] if row.get("exists", True) and not row.get("safe_for_destructive_replay", False) and row.get("classification") not in {"no-ledger"}]
    return 1 if unsafe and args.fail_unsafe else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks replay-plan")
    parser.add_argument("ref", nargs="*", help="specific refs to inspect; defaults to agents, gadgets, and gadget-agent refs")
    parser.add_argument("--json", action="store_true", help="emit full JSON plan")
    parser.add_argument("--output", help="write JSON plan to this file")
    parser.add_argument("--include-empty", action="store_true", help="include even refs with no replay ledger")
    parser.add_argument("--fail-unsafe", action="store_true", help="exit nonzero when fingerprint divergence or unsafe replay is detected")
    return parser


def main(argv: list[str]) -> int:
    try:
        return cmd_plan(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"forks replay-plan: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
