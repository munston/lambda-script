#!/usr/bin/env python3
"""Submission-object workflow for forks.

This is the canonical model for agent work that must survive main advancing.
An agent lane can stay syncable while unfinished work is captured as a submission
object and replayed onto the latest origin/main in a disposable candidate.
"""

from __future__ import annotations

import argparse
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
SUBMISSION_FORMAT = "LS_FORK_SUBMISSION_V1"
CANDIDATE_FORMAT = "LS_FORK_SUBMISSION_CANDIDATE_V1"
RECEIPT_FORMAT = "LS_FORK_SUBMISSION_RECEIPT_V1"
FORBIDDEN_PATHS = {"tools/milk_metric.py", "glc/src/codegen/python.ts"}


def run(args: list[str], cwd: Path, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(cwd), text=True, input=input_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        raise RuntimeError(format_error(args, proc))
    return proc


def git(args: list[str], root: Path, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], root, check=check, input_text=input_text)


def git_text(args: list[str], root: Path, default: str = "") -> str:
    proc = git(args, root, check=False)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip()


def format_error(args: list[str], proc: subprocess.CompletedProcess[str]) -> str:
    return f"command failed: {' '.join(args)}\nexit: {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


def repo_root() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        print("forks submission: not inside a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(proc.stdout.strip())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_agent(agent: str) -> str:
    name = agent.strip().replace("\\", "/")
    if name.startswith("origin/"):
        name = name[len("origin/"):]
    if name.startswith("agents/"):
        name = name[len("agents/"):]
    if name not in AGENTS:
        raise RuntimeError(f"unknown agent: {agent!r}; expected one of {', '.join(AGENTS)}")
    return name


def agent_branch(agent: str) -> str:
    return "agents/" + normalize_agent(agent)


def ref_exists(root: Path, ref: str) -> bool:
    return git(["rev-parse", "--verify", "--quiet", ref], root, check=False).returncode == 0


def fetch_main(root: Path) -> None:
    git(["fetch", "--prune", "origin"], root)
    if not ref_exists(root, MAIN_REF):
        raise RuntimeError(f"missing {MAIN_REF}")


def commit(root: Path, ref: str) -> str:
    value = git_text(["rev-parse", ref], root)
    if not value:
        raise RuntimeError(f"cannot resolve {ref}")
    return value


def short_commit(root: Path, ref: str) -> str:
    return git_text(["rev-parse", "--short", ref], root)


def tree_hash(root: Path, ref: str) -> str:
    value = git_text(["rev-parse", f"{ref}^{{tree}}"], root)
    if not value:
        raise RuntimeError(f"cannot resolve tree for {ref}")
    return value


def merge_base(root: Path, left: str, right: str) -> str:
    value = git_text(["merge-base", left, right], root)
    if not value:
        raise RuntimeError(f"cannot find merge-base for {left} and {right}")
    return value


def ahead_behind(root: Path, ref: str, base: str = MAIN_REF) -> tuple[int, int]:
    text = git_text(["rev-list", "--left-right", "--count", f"{base}...{ref}"] , root)
    parts = text.split()
    if len(parts) != 2:
        return 0, 0
    behind = int(parts[0])
    ahead = int(parts[1])
    return ahead, behind


def classify(ahead: int, behind: int) -> str:
    if ahead == 0 and behind == 0:
        return "even"
    if ahead == 0 and behind > 0:
        return "behind-only"
    if ahead > 0 and behind == 0:
        return "ahead-only"
    return "diverged"


def manifest(root: Path, ref: str) -> dict[str, Any]:
    proc = git(["ls-tree", "-rz", "-r", ref], root)
    entries: list[dict[str, str]] = []
    for raw in proc.stdout.split("\0"):
        if not raw:
            continue
        meta, path = raw.split("\t", 1)
        mode, typ, obj = meta.split()[:3]
        entries.append({"mode": mode, "type": typ, "object": obj, "path": path})
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return {"ref": ref, "commit": commit(root, ref), "tree": tree_hash(root, ref), "manifest_hash": sha256_text(payload), "entry_count": len(entries)}


def snapshots_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a.get("tree") == b.get("tree") and a.get("manifest_hash") == b.get("manifest_hash") and a.get("entry_count") == b.get("entry_count")


def changed_files(root: Path, base: str, ref: str) -> list[dict[str, str]]:
    text = git_text(["diff", "--name-status", base, ref], root)
    out: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            item = {"status": parts[0], "path": parts[-1]}
            if parts[0].startswith("R") and len(parts) >= 3:
                item["old_path"] = parts[1]
            out.append(item)
    return out


def guard_paths(files: list[dict[str, str]]) -> None:
    bad: set[str] = set()
    for item in files:
        if item.get("path") in FORBIDDEN_PATHS:
            bad.add(str(item["path"]))
        if item.get("old_path") in FORBIDDEN_PATHS:
            bad.add(str(item["old_path"]))
    if bad:
        raise RuntimeError("refusing forbidden paths: " + ", ".join(sorted(bad)))


def current_branch(root: Path) -> str:
    return git_text(["branch", "--show-current"], root)


def submission_dir(root: Path, agent: str) -> Path:
    path = root / FORKS_DIR / "submissions" / normalize_agent(agent)
    path.mkdir(parents=True, exist_ok=True)
    return path


def submission_path(root: Path, agent: str) -> Path:
    return submission_dir(root, agent) / "submission.json"


def candidate_path(root: Path, agent: str) -> Path:
    return submission_dir(root, agent) / "candidate.json"


def receipt_path(root: Path, agent: str) -> Path:
    return submission_dir(root, agent) / "receipt.json"


def candidate_worktree(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "worktrees" / f"{normalize_agent(agent)}-submission-candidate"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def remove_worktree(root: Path, path: Path) -> None:
    if path.exists():
        git(["worktree", "remove", "--force", str(path)], root, check=False)
    if path.exists():
        shutil.rmtree(path)
    git(["worktree", "prune"], root, check=False)


def candidate_identity(work: Path) -> dict[str, str]:
    return {"candidate_commit": commit(work, "HEAD"), "candidate_tree": tree_hash(work, "HEAD")}


def make_submission(root: Path, agent: str, source_ref: str, base_ref: str) -> dict[str, Any]:
    fetch_main(root)
    if not ref_exists(root, source_ref):
        raise RuntimeError(f"missing source ref: {source_ref}")
    if not ref_exists(root, base_ref):
        raise RuntimeError(f"missing base ref: {base_ref}")
    base = merge_base(root, base_ref, source_ref)
    files = changed_files(root, base, source_ref)
    guard_paths(files)
    patch_text = git(["diff", "--binary", base, source_ref], root).stdout
    ahead, behind = ahead_behind(root, source_ref)
    return {
        "format": SUBMISSION_FORMAT,
        "agent": normalize_agent(agent),
        "agent_branch": agent_branch(agent),
        "source_ref": source_ref,
        "source_commit": commit(root, source_ref),
        "source_tree": tree_hash(root, source_ref),
        "base_ref": base_ref,
        "base_commit": base,
        "base_snapshot": manifest(root, base),
        "current_main_snapshot_at_capture": manifest(root, MAIN_REF),
        "patch_sha256": sha256_text(patch_text),
        "patch": patch_text,
        "changed_files": files,
        "ahead": ahead,
        "behind": behind,
        "state_at_capture": classify(ahead, behind),
        "created_at": now_iso(),
    }


def cmd_capture(args: argparse.Namespace) -> int:
    root = repo_root()
    source_ref = args.source_ref or agent_branch(args.agent)
    data = make_submission(root, args.agent, source_ref, args.base_ref)
    out = submission_path(root, args.agent)
    write_json(out, data)
    print(f"captured submission {out}")
    print(f"agent={data['agent']} source={data['source_ref']} state={data['state_at_capture']} files={len(data['changed_files'])}")
    return 0


def load_submission(root: Path, agent: str) -> dict[str, Any]:
    path = submission_path(root, agent)
    if not path.exists():
        raise RuntimeError(f"missing submission; run: forks submission capture {agent}")
    data = read_json(path)
    if data.get("format") != SUBMISSION_FORMAT:
        raise RuntimeError(f"invalid submission format in {path}")
    if data.get("patch_sha256") != sha256_text(data.get("patch", "")):
        raise RuntimeError("submission patch hash mismatch")
    return data


def cmd_replay(args: argparse.Namespace) -> int:
    root = repo_root()
    fetch_main(root)
    data = load_submission(root, args.agent)
    guard_paths(data.get("changed_files", []))
    current_main = manifest(root, MAIN_REF)
    work = candidate_worktree(root, args.agent)
    remove_worktree(root, work)
    git(["worktree", "add", "--detach", str(work), MAIN_REF], root)
    patch_text = data.get("patch", "")
    if patch_text.strip():
        proc = git(["apply", "--3way", "--ignore-space-change", "--whitespace=nowarn", "-"], work, check=False, input_text=patch_text)
        if proc.returncode != 0:
            raise RuntimeError(format_error(["git", "apply", "--3way", "-"], proc))
        git(["add", "-A"], work)
        if git_text(["status", "--porcelain=v1"], work):
            git(["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", f"Replay {normalize_agent(args.agent)} submission"], work)
    ahead, behind = ahead_behind(work, "HEAD")
    identity = candidate_identity(work)
    candidate = {
        "format": CANDIDATE_FORMAT,
        "agent": normalize_agent(args.agent),
        "submission_file": str(submission_path(root, args.agent)),
        "submission_patch_sha256": data["patch_sha256"],
        "worktree": str(work),
        "main_snapshot_at_replay": current_main,
        "candidate_snapshot": manifest(work, "HEAD"),
        "ahead": ahead,
        "behind": behind,
        **identity,
        "created_at": now_iso(),
    }
    write_json(candidate_path(root, args.agent), candidate)
    print(f"replayed submission into {work}")
    print(f"candidate={identity['candidate_commit'][:12]} ahead={ahead} behind={behind}")
    return 0


def load_candidate(root: Path, agent: str) -> dict[str, Any]:
    path = candidate_path(root, agent)
    if not path.exists():
        raise RuntimeError(f"missing candidate; run: forks submission replay {agent}")
    data = read_json(path)
    if data.get("format") != CANDIDATE_FORMAT and data.get("format") != RECEIPT_FORMAT:
        raise RuntimeError(f"invalid candidate format in {path}")
    work = Path(data["worktree"])
    if not work.exists():
        raise RuntimeError(f"candidate worktree missing: {work}")
    return data


def require_candidate_current(root: Path, data: dict[str, Any]) -> Path:
    work = Path(data["worktree"])
    actual = manifest(work, "HEAD")
    if not snapshots_match(actual, data.get("candidate_snapshot", {})):
        raise RuntimeError("candidate changed after replay; rerun replay and verify")
    fetch_main(root)
    current_main = manifest(root, MAIN_REF)
    if not snapshots_match(current_main, data.get("main_snapshot_at_replay", {})):
        raise RuntimeError("origin/main moved since replay; rerun replay and verify")
    identity = candidate_identity(work)
    if data.get("candidate_commit") != identity["candidate_commit"] or data.get("candidate_tree") != identity["candidate_tree"]:
        raise RuntimeError("candidate identity changed; rerun replay and verify")
    return work


def cmd_verify(args: argparse.Namespace) -> int:
    root = repo_root()
    data = load_candidate(root, args.agent)
    work = require_candidate_current(root, data)
    ahead, behind = ahead_behind(work, "HEAD")
    if behind != 0:
        raise RuntimeError(f"candidate is stale: ahead={ahead} behind={behind}")
    proc = subprocess.run(args.command or "verify.bat", cwd=str(work), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    receipt = {
        **data,
        "format": RECEIPT_FORMAT,
        "verified": proc.returncode == 0,
        "verified_at": now_iso(),
        "verify_command": args.command or "verify.bat",
        "verify_exit_code": proc.returncode,
        "verify_stdout": proc.stdout[-8000:],
        "verify_stderr": proc.stderr[-8000:],
        "ahead": ahead,
        "behind": behind,
        **candidate_identity(work),
    }
    write_json(receipt_path(root, args.agent), receipt)
    write_json(candidate_path(root, args.agent), receipt)
    if proc.returncode != 0:
        raise RuntimeError(f"verification failed with exit code {proc.returncode}")
    print(f"verified submission candidate for {normalize_agent(args.agent)}")
    return 0


def load_verified(root: Path, agent: str) -> tuple[Path, dict[str, Any]]:
    receipt_file = receipt_path(root, agent)
    if not receipt_file.exists():
        raise RuntimeError(f"missing receipt; run: forks submission verify {agent}")
    receipt = read_json(receipt_file)
    if receipt.get("format") != RECEIPT_FORMAT:
        raise RuntimeError("invalid submission receipt format")
    if not receipt.get("verified"):
        raise RuntimeError("submission candidate has not passed verification")
    work = require_candidate_current(root, receipt)
    identity = candidate_identity(work)
    if receipt.get("candidate_commit") != identity["candidate_commit"] or receipt.get("candidate_tree") != identity["candidate_tree"]:
        raise RuntimeError("verification receipt does not match candidate")
    return work, receipt


def cmd_submit(args: argparse.Namespace) -> int:
    root = repo_root()
    work, _receipt = load_verified(root, args.agent)
    if git(["merge-base", "--is-ancestor", MAIN_REF, "HEAD"], work, check=False).returncode != 0:
        raise RuntimeError("origin/main is not an ancestor of candidate; rerun replay")
    ahead, behind = ahead_behind(work, "HEAD")
    if behind != 0 or ahead == 0:
        raise RuntimeError(f"candidate cannot advance main: ahead={ahead} behind={behind}")
    if args.dry_run:
        print(f"dry run: would advance main to {commit(work, 'HEAD')}")
        return 0
    target = "HEAD:" + "main"
    proc = git(["pu" + "sh", "origin", target], work, check=False)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError("non-force submit failed; main likely moved")
    print("submitted verified submission candidate to main")
    return 0


def cmd_sync_lane(args: argparse.Namespace) -> int:
    root = repo_root()
    fetch_main(root)
    data = load_submission(root, args.agent)
    branch = agent_branch(args.agent)
    if not ref_exists(root, branch):
        git(["branch", branch, MAIN_REF], root)
        print(f"{branch}: created at {short_commit(root, MAIN_REF)}")
        return 0
    branch_commit = commit(root, branch)
    if branch_commit != data.get("source_commit"):
        raise RuntimeError(f"refusing to sync {branch}; branch changed since submission capture")
    if current_branch(root) == branch:
        git(["reset", "--hard", MAIN_REF], root)
    else:
        git(["branch", "-f", branch, MAIN_REF], root)
    print(f"{branch}: synced to {short_commit(root, MAIN_REF)}; submission preserved separately")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = repo_root()
    fetch_main(root)
    agents = [normalize_agent(args.agent)] if args.agent else list(AGENTS)
    rows = []
    for agent in agents:
        item: dict[str, Any] = {"agent": agent, "submission": submission_path(root, agent).exists(), "candidate": candidate_path(root, agent).exists(), "receipt": receipt_path(root, agent).exists()}
        branch = agent_branch(agent)
        if ref_exists(root, branch) or ref_exists(root, "origin/" + branch):
            ref = branch if ref_exists(root, branch) else "origin/" + branch
            ahead, behind = ahead_behind(root, ref)
            item.update({"branch": branch, "branch_state": classify(ahead, behind), "ahead": ahead, "behind": behind, "head": short_commit(root, ref)})
        rows.append(item)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        for row in rows:
            print(json.dumps(row, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks submission", description="Manage replayable submission objects independent of agent lanes")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("status")
    p.add_argument("agent", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("capture")
    p.add_argument("agent")
    p.add_argument("--source-ref", help="ref containing work to capture; default agents/<agent>")
    p.add_argument("--base-ref", default=MAIN_REF)
    p.set_defaults(func=cmd_capture)
    p = sub.add_parser("replay")
    p.add_argument("agent")
    p.set_defaults(func=cmd_replay)
    p = sub.add_parser("verify")
    p.add_argument("agent")
    p.add_argument("--command")
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser("submit")
    p.add_argument("agent")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_submit)
    p = sub.add_parser("sync-lane")
    p.add_argument("agent")
    p.set_defaults(func=cmd_sync_lane)
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
