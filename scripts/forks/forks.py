#!/usr/bin/env python3
"""
Forks: safe agent-lane orchestration for LambdaScript.

This is repository tooling, not LambdaScript language support. It keeps `main`
authoritative while letting agent branches preserve work until their patch can
be staged, verified, and submitted on top of the latest `origin/main`.

The invariant is snapshot-gated submission:

    patch = declared base-main snapshot + file changes + expected result snapshot

A candidate may be submitted only when it is built on current `origin/main`, its
recorded snapshot still matches its worktree, a matching verification receipt
has passed, and a normal non-force push or an explicit contents ship plan can
advance `main`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENTS = ("ed", "edd", "eddy", "guy")
MAIN_REF = "origin/main"
FORKS_DIR = ".forks"
SNAPSHOT_DIRS = ("patches", "candidates", "receipts", "worktrees", "snapshots", "conflicts", "ships")
FORBIDDEN_PATHS = {
    "tools/milk_metric.py",
    "glc/src/codegen/python.ts",
}


def run(args: list[str], cwd: Path, check: bool = True, *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(format_process_error(args, proc))
    return proc


def git(args: list[str], root: Path, check: bool = True, *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], root, check=check, input_text=input_text)


def git_text(args: list[str], root: Path, default: str = "") -> str:
    proc = git(args, root, check=False)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip()


def format_process_error(args: list[str], proc: subprocess.CompletedProcess[str]) -> str:
    return (
        f"command failed: {' '.join(args)}\n"
        f"exit: {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        print("forks: not inside a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(proc.stdout.strip())


def ensure_dirs(root: Path) -> None:
    for rel in SNAPSHOT_DIRS:
        (root / FORKS_DIR / rel).mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_agent(agent: str) -> str:
    name = agent.strip().replace("\\", "/")
    if name.startswith("origin/"):
        name = name[len("origin/"):]
    if name.startswith("agents/"):
        name = name[len("agents/"):]
    if "/" in name or not name:
        raise ValueError(f"invalid agent name: {agent!r}")
    return name


def agent_branch(agent: str) -> str:
    return f"agents/{normalize_agent(agent)}"


def ref_exists(root: Path, ref: str) -> bool:
    return git(["rev-parse", "--verify", "--quiet", ref], root, check=False).returncode == 0


def best_agent_ref(root: Path, agent: str) -> str:
    branch = agent_branch(agent)
    if ref_exists(root, branch):
        return branch
    remote = f"origin/{branch}"
    if ref_exists(root, remote):
        return remote
    raise RuntimeError(f"missing agent branch: {branch}")


def current_branch(root: Path) -> str:
    return git_text(["branch", "--show-current"], root)


def commit(root: Path, ref: str) -> str:
    value = git_text(["rev-parse", ref], root)
    if not value:
        raise RuntimeError(f"cannot resolve ref: {ref}")
    return value


def short_commit(root: Path, ref: str) -> str:
    return git_text(["rev-parse", "--short", ref], root)


def tree_hash(root: Path, ref: str) -> str:
    value = git_text(["rev-parse", f"{ref}^{{tree}}"], root)
    if not value:
        raise RuntimeError(f"cannot resolve tree for ref: {ref}")
    return value


def merge_base(root: Path, left: str, right: str) -> str:
    return git_text(["merge-base", left, right], root)


def ahead_behind(root: Path, ref: str, base: str = MAIN_REF) -> tuple[int, int]:
    text = git_text(["rev-list", "--left-right", "--count", f"{base}...{ref}"], root)
    parts = text.split()
    if len(parts) != 2:
        return 0, 0
    behind = int(parts[0])
    ahead = int(parts[1])
    return ahead, behind


def changed_files(root: Path, ref: str, base: str = MAIN_REF) -> list[dict[str, str]]:
    text = git_text(["diff", "--name-status", f"{base}...{ref}"], root)
    out: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0]
            path = parts[-1]
            item = {"status": status, "path": path}
            if status.startswith("R") and len(parts) >= 3:
                item["old_path"] = parts[1]
            out.append(item)
    return out


def fetch_main(root: Path) -> None:
    git(["fetch", "--prune", "origin"], root)
    if not ref_exists(root, MAIN_REF):
        raise RuntimeError(f"missing {MAIN_REF}; fetch did not produce it")


def local_branch_exists(root: Path, branch: str) -> bool:
    return ref_exists(root, branch)


def ensure_local_agent_branch(root: Path, agent: str) -> str:
    branch = agent_branch(agent)
    if local_branch_exists(root, branch):
        return branch
    remote = f"origin/{branch}"
    if ref_exists(root, remote):
        git(["branch", branch, remote], root)
        return branch
    git(["branch", branch, MAIN_REF], root)
    return branch


def classify(ahead: int, behind: int) -> str:
    if ahead == 0 and behind == 0:
        return "even"
    if ahead == 0 and behind > 0:
        return "behind-only"
    if ahead > 0 and behind == 0:
        return "ahead-only"
    return "diverged"


def list_agent_branches(root: Path) -> list[str]:
    text = git_text(["for-each-ref", "--format=%(refname:short)", "refs/heads/agents", "refs/remotes/origin/agents"], root)
    found: set[str] = set()
    for raw in text.splitlines():
        if raw.startswith("origin/"):
            raw = raw[len("origin/"):]
        if raw.startswith("agents/"):
            found.add(raw)
    for agent in AGENTS:
        branch = agent_branch(agent)
        if ref_exists(root, branch) or ref_exists(root, f"origin/{branch}"):
            found.add(branch)
    return sorted(found)


def guard_forbidden_paths(files: list[dict[str, str]]) -> list[str]:
    paths: list[str] = []
    for item in files:
        if item["path"] in FORBIDDEN_PATHS:
            paths.append(item["path"])
        if item.get("old_path") in FORBIDDEN_PATHS:
            paths.append(item["old_path"])
    return sorted(set(paths))


def patch_path(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "patches" / f"{normalize_agent(agent)}.json"


def candidate_path(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "candidates" / f"{normalize_agent(agent)}.json"


def receipt_path(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "receipts" / f"{normalize_agent(agent)}.json"


def ship_path(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "ships" / f"{normalize_agent(agent)}-contents.json"


def conflict_path(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "conflicts" / f"{normalize_agent(agent)}-stale-base.json"


def snapshot_path(root: Path, name: str) -> Path:
    safe = name.replace("/", "_").replace("\\", "_")
    return root / FORKS_DIR / "snapshots" / f"{safe}.json"


def candidate_worktree(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "worktrees" / f"{normalize_agent(agent)}-candidate"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_manifest(root: Path, ref: str) -> dict[str, Any]:
    proc = git(["ls-tree", "-rz", "-r", ref], root, check=True)
    entries: list[dict[str, str]] = []
    for raw in proc.stdout.split("\0"):
        if not raw:
            continue
        meta, path = raw.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 3:
            entries.append({"mode": parts[0], "type": parts[1], "object": parts[2], "path": path})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return {
        "format": "LS_FORK_MANIFEST_V1",
        "ref": ref,
        "commit": commit(root, ref),
        "tree": tree_hash(root, ref),
        "manifest_hash": sha256_text(payload),
        "entry_count": len(entries),
        "entries": entries,
    }


def compact_snapshot(root: Path, ref: str) -> dict[str, Any]:
    manifest = git_manifest(root, ref)
    return {
        "ref": ref,
        "commit": manifest["commit"],
        "tree": manifest["tree"],
        "manifest_hash": manifest["manifest_hash"],
        "entry_count": manifest["entry_count"],
    }


def snapshots_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a.get("tree") == b.get("tree")
        and a.get("manifest_hash") == b.get("manifest_hash")
        and a.get("entry_count") == b.get("entry_count")
    )


def snapshot_diff_summary(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    return {
        "expected": {
            "commit": expected.get("commit"),
            "tree": expected.get("tree"),
            "manifest_hash": expected.get("manifest_hash"),
            "entry_count": expected.get("entry_count"),
        },
        "actual": {
            "commit": actual.get("commit"),
            "tree": actual.get("tree"),
            "manifest_hash": actual.get("manifest_hash"),
            "entry_count": actual.get("entry_count"),
        },
    }


def candidate_identity(work: Path) -> dict[str, str]:
    return {
        "candidate_commit": commit(work, "HEAD"),
        "candidate_tree": tree_hash(work, "HEAD"),
    }


def compute_collisions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, list[str]] = {}
    for row in rows:
        if row["ahead"] <= 0:
            continue
        for path in row["files"]:
            by_path.setdefault(path, []).append(row["branch"])
    collisions = []
    for path, branches in sorted(by_path.items()):
        unique = sorted(set(branches))
        if len(unique) > 1:
            collisions.append({"path": path, "branches": unique})
    return collisions


def unique_commits(root: Path, ref: str, base: str = MAIN_REF) -> list[str]:
    text = git_text(["log", "--oneline", f"{base}..{ref}"], root)
    return [line for line in text.splitlines() if line]


def file_payload(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    payload: dict[str, Any] = {
        "size": len(data),
        "sha256": sha256_bytes(data),
    }
    try:
        payload["encoding"] = "utf-8"
        payload["content"] = data.decode("utf-8")
    except UnicodeDecodeError:
        payload["encoding"] = "base64"
        payload["content"] = base64.b64encode(data).decode("ascii")
    return payload


def make_contents_ship_plan(root: Path, data: dict[str, Any], receipt_data: dict[str, Any]) -> dict[str, Any]:
    work = Path(data["worktree"])
    files = changed_files(work, "HEAD")
    blocked = guard_forbidden_paths(files)
    if blocked:
        raise RuntimeError("candidate touches forbidden paths: " + ", ".join(blocked))
    current_main = compact_snapshot(root, MAIN_REF)
    staged_main = data.get("current_main_snapshot_at_stage", {})
    if not snapshots_match(current_main, staged_main):
        raise RuntimeError("origin/main moved since verification; rerun stage and verify")
    identity = candidate_identity(work)
    if data.get("candidate_commit") != identity["candidate_commit"]:
        raise RuntimeError("candidate HEAD changed after staging; rerun stage and verify")
    if data.get("candidate_tree") != identity["candidate_tree"]:
        raise RuntimeError("candidate tree changed after staging; rerun stage and verify")
    if receipt_data.get("candidate_commit") != identity["candidate_commit"]:
        raise RuntimeError("verification receipt does not match current candidate HEAD")
    if receipt_data.get("candidate_tree") != identity["candidate_tree"]:
        raise RuntimeError("verification receipt does not match current candidate tree")
    operations: list[dict[str, Any]] = []
    for item in files:
        status = item["status"]
        path = item["path"]
        if status.startswith("D"):
            operations.append({"op": "delete", "path": path, "status": status})
        elif status.startswith("R"):
            old_path = item.get("old_path")
            if old_path:
                operations.append({"op": "delete", "path": old_path, "status": status, "rename_target": path})
            operations.append({"op": "write", "path": path, "status": status, **file_payload(work / path)})
        else:
            operations.append({"op": "write", "path": path, "status": status, **file_payload(work / path)})
    plan_without_hash = {
        "format": "LS_FORK_CONTENTS_SHIP_V1",
        "created_at": now_iso(),
        "agent": data.get("agent"),
        "backend": "contents",
        "main_snapshot": current_main,
        "candidate_snapshot": data.get("candidate_snapshot"),
        "candidate_commit": identity["candidate_commit"],
        "candidate_tree": identity["candidate_tree"],
        "receipt": {
            "format": receipt_data.get("format"),
            "verified": receipt_data.get("verified"),
            "verified_at": receipt_data.get("verified_at"),
            "verify_command": receipt_data.get("verify_command"),
            "verify_exit_code": receipt_data.get("verify_exit_code"),
            "candidate_commit": receipt_data.get("candidate_commit"),
            "candidate_tree": receipt_data.get("candidate_tree"),
        },
        "changed_files": files,
        "operations": operations,
    }
    payload = json.dumps(plan_without_hash, sort_keys=True, separators=(",", ":"))
    return {
        **plan_without_hash,
        "operation_count": len(operations),
        "plan_sha256": sha256_text(payload),
    }


def cmd_status(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_dirs(root)
    if args.fetch:
        fetch_main(root)
    main_snapshot = compact_snapshot(root, MAIN_REF)
    rows = []
    for branch in list_agent_branches(root):
        ref = branch if ref_exists(root, branch) else f"origin/{branch}"
        ahead, behind = ahead_behind(root, ref)
        rows.append({
            "branch": branch,
            "ref": ref,
            "state": classify(ahead, behind),
            "ahead": ahead,
            "behind": behind,
            "head": short_commit(root, ref),
            "tree": tree_hash(root, ref),
            "files": [item["path"] for item in changed_files(root, ref)],
        })
    collisions = compute_collisions(rows)
    if args.json:
        print(json.dumps({"main": main_snapshot, "branches": rows, "collisions": collisions}, indent=2, sort_keys=True))
        return 0
    print(f"main {short_commit(root, MAIN_REF)} tree {main_snapshot['tree']} manifest {main_snapshot['manifest_hash']}")
    for row in rows:
        print(f"{row['branch']}: {row['state']} ahead={row['ahead']} behind={row['behind']} head={row['head']} files={len(row['files'])}")
    if collisions:
        print("collisions:")
        for item in collisions:
            print(f"  {item['path']}: {', '.join(item['branches'])}")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_dirs(root)
    ref = args.ref
    data = git_manifest(root, ref) if args.full else compact_snapshot(root, ref)
    data["created_at"] = now_iso()
    if args.write:
        out = snapshot_path(root, args.name or ref)
        write_json(out, data)
        print(f"wrote {out}")
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def make_patch(root: Path, agent: str) -> dict[str, Any]:
    fetch_main(root)
    ref = best_agent_ref(root, agent)
    base = merge_base(root, MAIN_REF, ref)
    if not base:
        raise RuntimeError(f"cannot find merge-base between {MAIN_REF} and {ref}")
    files = changed_files(root, ref)
    patch_text = git_text(["diff", "--binary", base, ref], root)
    ahead, behind = ahead_behind(root, ref)
    base_snapshot = compact_snapshot(root, base)
    source_snapshot = compact_snapshot(root, ref)
    current_main_snapshot = compact_snapshot(root, MAIN_REF)
    return {
        "format": "LS_FORK_PATCH_V1",
        "agent": normalize_agent(agent),
        "agent_branch": agent_branch(agent),
        "source_ref": ref,
        "base_snapshot": base_snapshot,
        "source_snapshot": source_snapshot,
        "current_main_snapshot_at_export": current_main_snapshot,
        "base_main_commit": base_snapshot["commit"],
        "base_main_tree": base_snapshot["tree"],
        "base_main_manifest_hash": base_snapshot["manifest_hash"],
        "expected_result_snapshot_on_original_base": source_snapshot,
        "patch_sha256": sha256_text(patch_text),
        "ahead": ahead,
        "behind": behind,
        "changed_files": files,
        "patch": patch_text,
        "created_at": now_iso(),
    }


def cmd_diff(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_dirs(root)
    patch = make_patch(root, args.agent)
    out = patch_path(root, args.agent)
    write_json(out, patch)
    stale = not snapshots_match(patch["base_snapshot"], patch["current_main_snapshot_at_export"])
    print(f"wrote {out}")
    print(f"agent={patch['agent']} ahead={patch['ahead']} behind={patch['behind']} files={len(patch['changed_files'])} stale_base={stale}")
    return 0


def remove_worktree(root: Path, path: Path) -> None:
    if path.exists():
        git(["worktree", "remove", "--force", str(path)], root, check=False)
    if path.exists():
        shutil.rmtree(path)
    git(["worktree", "prune"], root, check=False)


def write_conflict_report(root: Path, agent: str, patch: dict[str, Any], current_main: dict[str, Any], reason: str) -> Path:
    report = {
        "format": "LS_FORK_CONFLICT_V1",
        "agent": normalize_agent(agent),
        "reason": reason,
        "created_at": now_iso(),
        "base_vs_current": snapshot_diff_summary(patch["base_snapshot"], current_main),
        "patch_file": str(patch_path(root, agent)),
    }
    out = conflict_path(root, agent)
    write_json(out, report)
    return out


def ensure_patch_fresh_or_allowed(root: Path, agent: str, patch: dict[str, Any], allow_stale: bool) -> dict[str, Any]:
    current_main = compact_snapshot(root, MAIN_REF)
    if snapshots_match(patch["base_snapshot"], current_main):
        return current_main
    report = write_conflict_report(root, agent, patch, current_main, "patch base snapshot differs from current origin/main")
    if not allow_stale:
        raise RuntimeError(f"stale patch base; wrote {report}; rerun/rebase or pass --rebase-stale")
    return current_main


def cmd_stage(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_dirs(root)
    fetch_main(root)
    patch_file = patch_path(root, args.agent)
    patch = read_json(patch_file) if patch_file.exists() and not args.regenerate else make_patch(root, args.agent)
    if patch.get("format") != "LS_FORK_PATCH_V1":
        raise RuntimeError(f"invalid patch format in {patch_file}")
    if patch.get("patch_sha256") != sha256_text(patch.get("patch", "")):
        raise RuntimeError("patch payload hash mismatch")
    blocked = guard_forbidden_paths(patch["changed_files"])
    if blocked and not args.allow_forbidden:
        raise RuntimeError("refusing patch touching forbidden paths: " + ", ".join(blocked))
    current_main = ensure_patch_fresh_or_allowed(root, args.agent, patch, args.rebase_stale)
    work = candidate_worktree(root, args.agent)
    remove_worktree(root, work)
    git(["worktree", "add", "--detach", str(work), MAIN_REF], root)
    patch_text = patch.get("patch", "")
    if patch_text.strip():
        apply_proc = git(["apply", "--3way", "--whitespace=nowarn", "-"], work, check=False, input_text=patch_text)
        if apply_proc.returncode != 0:
            raise RuntimeError(format_process_error(["git", "apply", "--3way", "-"], apply_proc))
        git(["add", "-A"], work)
        if git_text(["status", "--porcelain=v1"], work):
            msg = f"Stage {normalize_agent(args.agent)} patch on current main"
            git(["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", msg], work)
    candidate_snapshot = compact_snapshot(work, "HEAD")
    expected_original = patch.get("expected_result_snapshot_on_original_base", {})
    exact_reproduction = snapshots_match(candidate_snapshot, expected_original)
    stale_rebase = not snapshots_match(patch["base_snapshot"], current_main)
    if not stale_rebase and not exact_reproduction:
        raise RuntimeError("candidate snapshot does not match expected result for original base")
    ahead, behind = ahead_behind(work, "HEAD")
    identity = candidate_identity(work)
    data = {
        "format": "LS_FORK_CANDIDATE_V1",
        "agent": normalize_agent(args.agent),
        "worktree": str(work),
        "patch_file": str(patch_file),
        "patch_sha256": patch["patch_sha256"],
        "base_snapshot_declared_by_patch": patch["base_snapshot"],
        "current_main_snapshot_at_stage": current_main,
        "expected_result_snapshot": expected_original if exact_reproduction else candidate_snapshot,
        "candidate_snapshot": candidate_snapshot,
        **identity,
        "rebased_from_stale_base": stale_rebase,
        "exact_reproduction_of_source_snapshot": exact_reproduction,
        "ahead": ahead,
        "behind": behind,
        "created_at": now_iso(),
        "verified": False,
    }
    write_json(candidate_path(root, args.agent), data)
    if args.write_patch:
        write_json(patch_file, patch)
    print(f"staged candidate at {work}")
    print(f"candidate {identity['candidate_commit'][:12]} ahead={ahead} behind={behind} exact_reproduction={exact_reproduction} stale_rebase={stale_rebase}")
    return 0


def run_verify_command(work: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(work), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def current_candidate_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    return compact_snapshot(Path(data["worktree"]), "HEAD")


def require_candidate_snapshot_intact(data: dict[str, Any]) -> None:
    actual = current_candidate_snapshot(data)
    recorded = data.get("candidate_snapshot", {})
    if not snapshots_match(actual, recorded):
        raise RuntimeError("candidate snapshot changed after staging; rerun stage and verify")


def cmd_verify(args: argparse.Namespace) -> int:
    root = repo_root()
    data_path = candidate_path(root, args.agent)
    if not data_path.exists():
        raise RuntimeError(f"missing candidate; run: forks stage {args.agent}")
    data = read_json(data_path)
    work = Path(data["worktree"])
    if not work.exists():
        raise RuntimeError(f"candidate worktree missing: {work}")
    require_candidate_snapshot_intact(data)
    fetch_main(root)
    current_main = compact_snapshot(root, MAIN_REF)
    staged_main = data.get("current_main_snapshot_at_stage", {})
    if not snapshots_match(current_main, staged_main):
        raise RuntimeError("origin/main moved since staging; rerun stage")
    ahead, behind = ahead_behind(work, "HEAD")
    files = changed_files(work, "HEAD")
    blocked = guard_forbidden_paths(files)
    if behind != 0:
        raise RuntimeError(f"candidate is stale: ahead={ahead} behind={behind}; rerun stage")
    if blocked and not args.allow_forbidden:
        raise RuntimeError("candidate touches forbidden paths: " + ", ".join(blocked))
    command = args.command or "verify.bat"
    proc = run_verify_command(work, command)
    ok = proc.returncode == 0
    identity = candidate_identity(work)
    verify_data = {
        **data,
        "format": "LS_FORK_VERIFY_RECEIPT_V1",
        "verified": ok,
        "verified_at": now_iso(),
        "verify_command": command,
        "verify_exit_code": proc.returncode,
        "verify_stdout": proc.stdout[-8000:],
        "verify_stderr": proc.stderr[-8000:],
        "ahead": ahead,
        "behind": behind,
        **identity,
    }
    write_json(data_path, verify_data)
    write_json(receipt_path(root, args.agent), verify_data)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if not ok:
        raise RuntimeError(f"verification failed with exit code {proc.returncode}")
    print(f"verified candidate for {normalize_agent(args.agent)}")
    return 0


def load_verified_candidate(root: Path, agent: str, no_verify_gate: bool) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    data_path = candidate_path(root, agent)
    receipt = receipt_path(root, agent)
    if not data_path.exists():
        raise RuntimeError(f"missing candidate; run: forks stage {agent}")
    data = read_json(data_path)
    if not no_verify_gate:
        if not receipt.exists():
            raise RuntimeError(f"missing verification receipt; run: forks verify {agent}")
        receipt_data = read_json(receipt)
        if not receipt_data.get("verified"):
            raise RuntimeError("candidate has not passed verification")
        if receipt_data.get("candidate_commit") != data.get("candidate_commit"):
            raise RuntimeError("verification receipt does not match staged candidate")
        if receipt_data.get("candidate_tree") != data.get("candidate_tree"):
            raise RuntimeError("verification receipt tree does not match staged candidate")
    else:
        receipt_data = data
    work = Path(data["worktree"])
    if not work.exists():
        raise RuntimeError(f"candidate worktree missing: {work}")
    fetch_main(root)
    current_main = compact_snapshot(root, MAIN_REF)
    staged_main = data.get("current_main_snapshot_at_stage", {})
    if not snapshots_match(current_main, staged_main):
        raise RuntimeError("origin/main moved since verification; rerun stage and verify")
    current_identity = candidate_identity(work)
    if data.get("candidate_commit") != current_identity["candidate_commit"]:
        raise RuntimeError("candidate HEAD changed after staging; rerun stage and verify")
    if data.get("candidate_tree") != current_identity["candidate_tree"]:
        raise RuntimeError("candidate tree changed after staging; rerun stage and verify")
    if not no_verify_gate:
        if receipt_data.get("candidate_commit") != current_identity["candidate_commit"]:
            raise RuntimeError("candidate HEAD changed after verification; rerun verify")
        if receipt_data.get("candidate_tree") != current_identity["candidate_tree"]:
            raise RuntimeError("candidate tree changed after verification; rerun verify")
    require_candidate_snapshot_intact(data)
    return work, data, receipt_data


def cmd_submit(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_dirs(root)
    work, data, receipt_data = load_verified_candidate(root, args.agent, args.no_verify_gate)
    ancestor = git(["merge-base", "--is-ancestor", MAIN_REF, "HEAD"], work, check=False)
    if ancestor.returncode != 0:
        raise RuntimeError("origin/main is not an ancestor of candidate HEAD; rerun stage")
    ahead, behind = ahead_behind(work, "HEAD")
    if behind != 0:
        raise RuntimeError(f"candidate is stale: ahead={ahead} behind={behind}; rerun stage")
    if ahead == 0:
        raise RuntimeError("candidate has no commits ahead of main; nothing to submit")
    blocked = guard_forbidden_paths(changed_files(work, "HEAD"))
    if blocked:
        raise RuntimeError("candidate touches forbidden paths: " + ", ".join(blocked))
    if args.backend == "contents":
        plan = make_contents_ship_plan(root, data, receipt_data)
        out = ship_path(root, args.agent)
        write_json(out, plan)
        print(f"wrote contents ship plan {out}")
        print(f"operations={plan['operation_count']} plan_sha256={plan['plan_sha256']}")
        return 0
    if args.dry_run:
        print(f"dry run: would push {commit(work, 'HEAD')} to main")
        return 0
    proc = git(["push", "origin", "HEAD:main"], work, check=False)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError("non-force push to main failed; main likely moved")
    print("submitted candidate to main")
    return 0


def cmd_ship_plan(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_dirs(root)
    work, data, receipt_data = load_verified_candidate(root, args.agent, args.no_verify_gate)
    ahead, behind = ahead_behind(work, "HEAD")
    if behind != 0:
        raise RuntimeError(f"candidate is stale: ahead={ahead} behind={behind}; rerun stage")
    if ahead == 0:
        raise RuntimeError("candidate has no commits ahead of main; nothing to ship")
    plan = make_contents_ship_plan(root, data, receipt_data)
    out = Path(args.output) if args.output else ship_path(root, args.agent)
    write_json(out, plan)
    print(f"wrote contents ship plan {out}")
    print(f"operations={plan['operation_count']} plan_sha256={plan['plan_sha256']}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    root = repo_root()
    fetch_main(root)
    branch = ensure_local_agent_branch(root, args.agent)
    ahead, behind = ahead_behind(root, branch)
    state = classify(ahead, behind)
    if state in {"even", "ahead-only"}:
        print(f"{branch}: {state}; no sync needed")
        return 0
    if state == "diverged":
        raise RuntimeError(f"{branch} has local progress and is behind main; use forks stage/reapply, not sync")
    if state == "behind-only":
        current = current_branch(root)
        if current == branch:
            git(["merge", "--ff-only", MAIN_REF], root)
        else:
            git(["branch", "-f", branch, MAIN_REF], root)
        print(f"{branch}: fast-forwarded to {short_commit(root, MAIN_REF)}")
        return 0
    raise RuntimeError(f"unexpected sync state: {state}")


def cmd_abandon(args: argparse.Namespace) -> int:
    root = repo_root()
    fetch_main(root)
    branch = ensure_local_agent_branch(root, args.agent)
    ahead, behind = ahead_behind(root, branch)
    files = changed_files(root, branch)
    commits = unique_commits(root, branch)
    print(f"{branch}: ahead={ahead} behind={behind}")
    if commits:
        print("unique commits to be discarded:")
        for line in commits:
            print(f"  {line}")
    if files:
        print("changed files to be discarded:")
        for item in files:
            print(f"  {item['status']} {item['path']}")
    if not args.yes:
        raise RuntimeError("refusing to abandon without --yes")
    current = current_branch(root)
    if current == branch:
        git(["reset", "--hard", MAIN_REF], root)
    else:
        git(["branch", "-f", branch, MAIN_REF], root)
    print(f"{branch}: abandoned to {short_commit(root, MAIN_REF)}")
    return 0


def cmd_check_patch(args: argparse.Namespace) -> int:
    root = repo_root()
    path = Path(args.path) if args.path else patch_path(root, args.agent)
    patch = read_json(path)
    fetch_main(root)
    current_main = compact_snapshot(root, MAIN_REF)
    ok_hash = patch.get("patch_sha256") == sha256_text(patch.get("patch", ""))
    ok_base = snapshots_match(patch.get("base_snapshot", {}), current_main)
    result = {
        "patch": str(path),
        "patch_hash_ok": ok_hash,
        "base_matches_current_main": ok_base,
        "base_vs_current": snapshot_diff_summary(patch.get("base_snapshot", {}), current_main),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ok_hash and ok_base else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks", description="Safe agent-fork orchestration for LambdaScript")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("status", help="show agent branch states against origin/main")
    p.add_argument("--fetch", action="store_true", help="fetch origin before reporting")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("snapshot", help="print or write commit/tree/manifest snapshot for a ref")
    p.add_argument("ref", nargs="?", default=MAIN_REF)
    p.add_argument("--full", action="store_true", help="include per-file manifest entries")
    p.add_argument("--write", action="store_true", help="write to .forks/snapshots")
    p.add_argument("--name", help="snapshot file name when using --write")
    p.set_defaults(func=cmd_snapshot)
    p = sub.add_parser("diff", help="export an agent branch patch")
    p.add_argument("agent")
    p.set_defaults(func=cmd_diff)
    p = sub.add_parser("check-patch", help="check patch hash and declared base against current main")
    p.add_argument("agent")
    p.add_argument("--path")
    p.set_defaults(func=cmd_check_patch)
    p = sub.add_parser("stage", help="apply an agent patch to a disposable current-main worktree")
    p.add_argument("agent")
    p.add_argument("--allow-forbidden", action="store_true")
    p.add_argument("--rebase-stale", action="store_true", help="explicitly attempt to apply a stale-base patch to current main")
    p.add_argument("--regenerate", action="store_true", help="regenerate patch from agent branch before staging")
    p.add_argument("--write-patch", action="store_true", help="write regenerated patch file during stage")
    p.set_defaults(func=cmd_stage)
    p = sub.add_parser("verify", help="verify a staged candidate and write a receipt")
    p.add_argument("agent")
    p.add_argument("--command", help="verification command to run in candidate worktree")
    p.add_argument("--allow-forbidden", action="store_true")
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser("ship-plan", help="write a connector-compatible contents ship plan")
    p.add_argument("agent")
    p.add_argument("--output")
    p.add_argument("--no-verify-gate", action="store_true", help="skip receipt authority check")
    p.set_defaults(func=cmd_ship_plan)
    p = sub.add_parser("submit", help="submit a verified candidate")
    p.add_argument("agent")
    p.add_argument("--backend", choices=("ref", "contents"), default="ref", help="ref pushes with git; contents writes a connector-compatible ship plan")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-verify-gate", action="store_true", help="skip receipt authority check")
    p.set_defaults(func=cmd_submit)
    p = sub.add_parser("sync", help="fast-forward an agent branch only when it has no unique commits")
    p.add_argument("agent")
    p.set_defaults(func=cmd_sync)
    p = sub.add_parser("abandon", help="destructively reset an agent branch to origin/main")
    p.add_argument("agent")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_abandon)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"forks: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
