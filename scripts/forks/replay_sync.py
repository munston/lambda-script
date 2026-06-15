#!/usr/bin/env python3
"""Replay synchronizer for Forks replay ledgers."""

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

SYNC_PLAN_FORMAT = "LS_FORK_REPLAY_SYNC_V1"
WORK_ROOT = "replay-sync"


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


def remote_refname(push_ref: str) -> str:
    return push_ref if push_ref.startswith("refs/heads/") else f"refs/heads/{push_ref}"


def lease_tracking_ref(push_ref: str) -> str:
    branch = push_ref[len("refs/heads/"):] if push_ref.startswith("refs/heads/") else push_ref
    return f"origin/{branch}"


def resolve_expected_push_oid(root: Path, ref: str) -> str:
    push_ref = push_ref_for(ref)
    tracking = lease_tracking_ref(push_ref)
    if forks.ref_exists(root, tracking):
        return forks.commit(root, tracking)
    if forks.ref_exists(root, ref):
        return forks.commit(root, ref)
    raise RuntimeError(f"cannot resolve expected push commit for {ref}")


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


def push_replayed_ref(root: Path, work: Path, ref: str, expected_oid: str) -> dict[str, Any]:
    push_ref = push_ref_for(ref)
    remote_ref = remote_refname(push_ref)
    tracking = lease_tracking_ref(push_ref)
    forks.git(["fetch", "--prune", "origin"], root)
    current_oid = forks.commit(root, tracking) if forks.ref_exists(root, tracking) else None
    if current_oid != expected_oid:
        return {
            "push_ref": push_ref,
            "remote_ref": remote_ref,
            "expected_oid": expected_oid,
            "current_oid": current_oid,
            "exit_code": 1,
            "ok": False,
            "fresh": False,
            "error": "remote ref changed before push",
        }
    proc = forks.git(
        ["push", f"--force-with-lease={remote_ref}:{expected_oid}", "origin", f"HEAD:{remote_ref}"],
        work,
        check=False,
    )
    return {
        "push_ref": push_ref,
        "remote_ref": remote_ref,
        "expected_oid": expected_oid,
        "current_oid": current_oid,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "fresh": True,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def replay_ref(root: Path, row: dict[str, Any], verify_command: str | None, apply: bool) -> dict[str, Any]:
    ref = row["ref"]
    if not row.get("safe_for_destructive_replay", False):
        return {
            "ref": ref,
            "status": "skipped",
            "reason": f"unsafe classification: {row.get('classification')}",
            "classification": row.get("classification"),
        }

    expected_oid = resolve_expected_push_oid(root, ref)
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
                    "expected_oid": expected_oid,
                    "applied": applied,
                    "verify": verify,
                }

        ahead, behind = forks.ahead_behind(work, "HEAD", forks.MAIN_REF)
        snapshot = forks.compact_snapshot(work, "HEAD")
        changed = forks.changed_files(work, "HEAD", forks.MAIN_REF)
        result = {
            "ref": ref,
            "status": "planned",
            "classification": row.get("classification"),
            "base": forks.MAIN_REF,
            "would_push": apply,
            "push_ref": push_ref_for(ref),
            "expected_oid": expected_oid,
            "worktree": str(work),
            "applied_count": len(applied),
            "applied": applied,
            "candidate_snapshot": snapshot,
            "ahead": ahead,
            "behind": behind,
            "changed_files": changed,
            "verify": verify,
        }
        if apply:
            push = push_replayed_ref(root, work, ref, expected_oid)
            result["push"] = push
            result["status"] = "applied" if push["ok"] else "push-failed"
        return result
    except Exception as exc:
        return {
            "ref": ref,
            "status": "failed",
            "classification": row.get("classification"),
            "expected_oid": expected_oid,
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
        rows.append(replay_ref(root, row, args.verify_command, args.apply))
    return {
        "format": SYNC_PLAN_FORMAT,
        "created_at": forks.now_iso(),
        "dry_run": not args.apply,
        "apply": args.apply,
        "main": base_plan["main"],
        "ref_count": len(rows),
        "refs": rows,
    }


def print_text(plan: dict[str, Any]) -> None:
    main = plan["main"]
    mode = "apply" if plan.get("apply") else "dry-run"
    print(f"{mode} main {main['commit'][:12]} tree {main['tree']} manifest {main['manifest_hash']}")
    for row in plan["refs"]:
        print(f"{row.get('ref')}: {row.get('status')} classification={row.get('classification')}")
        if row.get("status") in {"planned", "applied", "push-failed"}:
            print(f"  applied={row.get('applied_count')} ahead={row.get('ahead')} behind={row.get('behind')} push_ref={row.get('push_ref')}")
            print(f"  expected={str(row.get('expected_oid', ''))[:12]}")
            for item in row.get("applied", []):
                print(f"  replay #{item.get('sequence')} {str(item.get('json_patch_sha256', ''))[:12]} {item.get('title', '')}")
            if row.get("push"):
                push = row["push"]
                print(f"  push exit={push.get('exit_code')} ok={push.get('ok')} fresh={push.get('fresh')} remote_ref={push.get('remote_ref')}")
                if push.get("error"):
                    print(f"  push error: {push.get('error')}")
        if row.get("status") in {"failed", "verification-failed", "skipped"} and row.get("reason"):
            print(f"  reason: {row.get('reason')}")
        if row.get("error"):
            print(f"  error: {row.get('error')}")


def cmd_sync(args: argparse.Namespace) -> int:
    if args.apply and not args.verify_command:
        raise RuntimeError("--apply requires --verify-command")
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
    bad_status = {"failed", "verification-failed", "push-failed"}
    bad = [row for row in plan["refs"] if row.get("status") in bad_status]
    return 1 if bad and args.fail_failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks replay-sync")
    parser.add_argument("ref", nargs="*", help="specific refs to replay; defaults to agents, gadgets, and gadget-agent refs")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="build replay candidate worktrees without pushing")
    mode.add_argument("--apply", action="store_true", help="verify, rebuild, and push replayable refs using force-with-lease")
    parser.add_argument("--json", action="store_true", help="emit full JSON sync plan")
    parser.add_argument("--output", help="write JSON sync plan to this file")
    parser.add_argument("--include-empty", action="store_true", help="include refs with no replay ledger")
    parser.add_argument("--only-replay-needed", action="store_true", help="skip refs that have no pending replay entries")
    parser.add_argument("--verify-command", help="command to run inside each replay worktree before apply")
    parser.add_argument("--fail-failed", action="store_true", help="exit nonzero if any replay failed")
    return parser


def main(argv: list[str]) -> int:
    try:
        return cmd_sync(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"forks replay-sync: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
