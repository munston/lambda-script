#!/usr/bin/env python3
"""Dry-run replay synchronizer for Forks replay ledgers."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import forks
import import_json_patch
import replay_ledger
import replay_plan

SYNC_PLAN_FORMAT = "LS_FORK_REPLAY_SYNC_DRY_RUN_V1"
WORK_ROOT = "replay-sync"


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


def worktree_path(root: Path, ref: str) -> Path:
    return root / forks.FORKS_DIR / WORK_ROOT / replay_ledger.safe_token(ref)


def remove_worktree(root: Path, work: Path) -> None:
    if work.exists():
        forks.git(["worktree", "remove", "--force", str(work)], root, check=False)
    if work.exists():
        shutil.rmtree(work)
    forks.git(["worktree", "prune"], root, check=False)


def push_ref_for(ref: str) -> str:
    if ref.startswith("origin/"):
        return ref[len("origin/"):]
    return ref


def load_branch_ledger(root: Path, ref: str, path: str) -> dict[str, Any]:
    data = replay_plan.read_json_at_ref(root, ref, path)
    if data is None:
        raise RuntimeError(f"missing branch ledger {ref}:{path}")
    return data


def load_payload(root: Path, ref: str, entry: dict[str, Any]) -> dict[str, Any]:
    digest = entry.get("json_patch_sha256")
    if not isinstance(digest, str) or not digest:
        raise RuntimeError("ledger entry missing json_patch_sha256")
    path = entry.get("payload_path")
    if not isinstance(path, str) or not path:
        path = replay_ledger.payload_relpath(digest)
    data = replay_plan.read_json_at_ref(root, ref, path)
    if data is None:
        raise RuntimeError(f"missing replay payload {ref}:{path}")
    replay_ledger.validate_payload_object(data, digest)
    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError(f"payload object has no JSON patch payload: {ref}:{path}")
    return payload


def commit_step(work: Path, entry: dict[str, Any]) -> bool:
    forks.git(["add", "-A"], work)
    if not forks.git_text(["diff", "--cached", "--name-status"], work):
        return False
    seq = entry.get("sequence", "?")
    title = str(entry.get("title", "")).strip()
    digest = str(entry.get("json_patch_sha256", ""))[:12]
    msg = f"Replay ledger entry {seq} {digest}"
    if title:
        msg += f": {title}"
    forks.git(["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", msg], work)
    return True


def pending_entries_for_ledger(root: Path, ref: str, ledger_row: dict[str, Any]) -> list[dict[str, Any]]:
    ledger = load_branch_ledger(root, ref, ledger_row["path"])
    entries = list(ledger.get("entries", []))
    prefix = int(ledger_row.get("matching_prefix", 0))
    return entries[prefix:]


def replay_ref(root: Path, row: dict[str, Any], verify_command: str | None) -> dict[str, Any]:
    ref = row["ref"]
    if not row.get("safe_for_destructive_replay", False):
        return {
            "ref": ref,
            "status": "skipped",
            "reason": f"unsafe classification: {row.get('classification')}",
            "classification": row.get("classification"),
        }

    work = worktree_path(root, ref)
    remove_worktree(root, work)
    forks.git(["worktree", "add", "--detach", str(work), forks.MAIN_REF], root)

    applied: list[dict[str, Any]] = []
    try:
        for ledger_row in row.get("ledgers", []):
            for entry in pending_entries_for_ledger(root, ref, ledger_row):
                payload = load_payload(root, ref, entry)
                import_json_patch.apply_file_ops(work, payload.get("files", []))
                agent = str(entry.get("agent") or payload.get("agent") or "unknown")
                target_ref = str(entry.get("target_ref_at_capture") or ref)
                ledger_result = replay_ledger.append_entry(work, agent, payload, target_ref)
                committed = commit_step(work, entry)
                applied.append({
                    "sequence": entry.get("sequence"),
                    "title": entry.get("title", ""),
                    "json_patch_sha256": entry.get("json_patch_sha256"),
                    "payload_path": entry.get("payload_path") or replay_ledger.payload_relpath(str(entry.get("json_patch_sha256", ""))),
                    "ledger_path": ledger_result.get("path"),
                    "committed": committed,
                })

        verify = None
        if verify_command:
            proc = run_shell(verify_command, work, check=False)
            verify = {
                "command": verify_command,
                "exit_code": proc.returncode,
                "ok": proc.returncode == 0,
                "stdout_tail": proc.stdout[-4000:],
                "stderr_tail": proc.stderr[-4000:],
            }
            if proc.returncode != 0:
                return {
                    "ref": ref,
                    "status": "verification-failed",
                    "classification": row.get("classification"),
                    "applied": applied,
                    "verify": verify,
                }

        ahead, behind = forks.ahead_behind(work, "HEAD", forks.MAIN_REF)
        snapshot = forks.compact_snapshot(work, "HEAD")
        changed = forks.changed_files(work, "HEAD", forks.MAIN_REF)
        return {
            "ref": ref,
            "status": "planned",
            "classification": row.get("classification"),
            "base": forks.MAIN_REF,
            "would_push": False,
            "push_ref": push_ref_for(ref),
            "worktree": str(work),
            "applied_count": len(applied),
            "applied": applied,
            "candidate_snapshot": snapshot,
            "ahead": ahead,
            "behind": behind,
            "changed_files": changed,
            "verify": verify,
        }
    except Exception as exc:
        return {
            "ref": ref,
            "status": "failed",
            "classification": row.get("classification"),
            "applied": applied,
            "error": str(exc),
        }


def build_sync_plan(args: argparse.Namespace) -> dict[str, Any]:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    refs = args.ref or replay_plan.list_candidate_refs(root)
    base_plan = replay_plan.build_plan(root, refs, args.include_empty)
    rows = []
    for row in base_plan["refs"]:
        if not row.get("exists", True):
            rows.append({
                "ref": row.get("ref"),
                "status": "skipped",
                "reason": "missing ref",
                "classification": row.get("classification"),
            })
            continue
        if args.only_replay_needed and row.get("classification") != "replay-needed":
            continue
        if row.get("classification") == "no-ledger" and not args.include_empty:
            continue
        rows.append(replay_ref(root, row, args.verify_command))
    return {
        "format": SYNC_PLAN_FORMAT,
        "created_at": forks.now_iso(),
        "dry_run": True,
        "main": base_plan["main"],
        "ref_count": len(rows),
        "refs": rows,
    }


def print_text(plan: dict[str, Any]) -> None:
    main = plan["main"]
    print(f"main {main['commit'][:12]} tree {main['tree']} manifest {main['manifest_hash']}")
    for row in plan["refs"]:
        print(f"{row.get('ref')}: {row.get('status')} classification={row.get('classification')}")
        if row.get("status") == "planned":
            print(f"  applied={row.get('applied_count')} ahead={row.get('ahead')} behind={row.get('behind')} push_ref={row.get('push_ref')}")
            for item in row.get("applied", []):
                print(f"  replay #{item.get('sequence')} {str(item.get('json_patch_sha256', ''))[:12]} {item.get('title', '')}")
        if row.get("status") in {"failed", "verification-failed", "skipped"} and row.get("reason"):
            print(f"  reason: {row.get('reason')}")
        if row.get("error"):
            print(f"  error: {row.get('error')}")


def cmd_sync(args: argparse.Namespace) -> int:
    if not args.dry_run:
        raise RuntimeError("replay-sync currently supports --dry-run only")
    plan = build_sync_plan(args)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print_text(plan)
    bad = [row for row in plan["refs"] if row.get("status") in {"failed", "verification-failed"}]
    return 1 if bad and args.fail_failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks replay-sync")
    parser.add_argument("ref", nargs="*", help="specific refs to dry-run; defaults to agents, gadgets, and gadget-agent refs")
    parser.add_argument("--dry-run", action="store_true", help="required; build replay candidate worktrees without pushing")
    parser.add_argument("--json", action="store_true", help="emit full JSON sync plan")
    parser.add_argument("--output", help="write JSON sync plan to this file")
    parser.add_argument("--include-empty", action="store_true", help="include refs with no replay ledger")
    parser.add_argument("--only-replay-needed", action="store_true", help="skip refs that have no pending replay entries")
    parser.add_argument("--verify-command", help="optional command to run inside each replay worktree")
    parser.add_argument("--fail-failed", action="store_true", help="exit nonzero if any dry-run replay failed")
    return parser


def main(argv: list[str]) -> int:
    try:
        return cmd_sync(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"forks replay-sync: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
