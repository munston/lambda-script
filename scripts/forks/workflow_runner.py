#!/usr/bin/env python3
"""
Config-driven workflow runner for `forks`.

This is repository Git orchestration tooling. Workflow files define abstract
operations, not raw shell scripts. The runner maps those operations onto guarded
Git actions so common agent workflows can be invoked with one short command.
"""

from __future__ import annotations

import argparse
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
WORKFLOW_DIR = Path("scripts") / "forks" / "workflows"

BUILTIN_WORKFLOWS: dict[str, dict[str, Any]] = {
    "status": {
        "name": "status",
        "parameters": [],
        "steps": [
            {"op": "fetch_origin"},
            {"op": "status"},
        ],
    },
    "sync-lanes": {
        "name": "sync-lanes",
        "parameters": [],
        "steps": [
            {"op": "fetch_origin"},
            {"op": "assert_no_tracked_changes", "allow_untracked": True},
            {"op": "sync_lanes", "agents": ["ed", "edd", "eddy", "guy"]},
            {"op": "status"},
        ],
    },
    "verify-agent": {
        "name": "verify-agent",
        "parameters": ["agent"],
        "steps": [
            {"op": "fetch_origin"},
            {"op": "assert_no_tracked_changes", "allow_untracked": True},
            {"op": "require_agent_ahead_only", "agent": "$agent"},
            {"op": "stage_candidate_direct", "agent": "$agent"},
            {"op": "verify_candidate", "agent": "$agent", "command": "verify.bat"},
            {"op": "status"},
        ],
    },
    "land-agent": {
        "name": "land-agent",
        "parameters": ["agent"],
        "steps": [
            {"op": "fetch_origin"},
            {"op": "assert_no_tracked_changes", "allow_untracked": True},
            {"op": "require_agent_ahead_only", "agent": "$agent"},
            {"op": "stage_candidate_direct", "agent": "$agent"},
            {"op": "verify_candidate", "agent": "$agent", "command": "verify.bat"},
            {"op": "push_main_fast_forward", "agent": "$agent"},
            {"op": "sync_lanes", "agents": ["ed", "edd", "eddy", "guy"]},
            {"op": "status"},
        ],
    },
}


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        raise RuntimeError(format_process_error(args, proc))
    return proc


def git(args: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], root, check=check)


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
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        print("forks workflow: not inside a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(proc.stdout.strip())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def ahead_behind(root: Path, ref: str, base: str = MAIN_REF) -> tuple[int, int]:
    text = git_text(["rev-list", "--left-right", "--count", f"{base}...{ref}"], root)
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


def compact_snapshot(root: Path, ref: str) -> dict[str, Any]:
    return {
        "ref": ref,
        "commit": commit(root, ref),
        "tree": tree_hash(root, ref),
    }


def ensure_dirs(root: Path) -> None:
    for rel in ("worktrees", "candidates", "receipts", "workflow-runs"):
        (root / FORKS_DIR / rel).mkdir(parents=True, exist_ok=True)


def fetch_origin(root: Path) -> None:
    git(["fetch", "--prune", "origin"], root)
    if not ref_exists(root, MAIN_REF):
        raise RuntimeError(f"missing {MAIN_REF}; fetch did not produce it")


def assert_no_tracked_changes(root: Path, allow_untracked: bool = True) -> None:
    mode = "--untracked-files=normal" if not allow_untracked else "--untracked-files=no"
    text = git_text(["status", "--porcelain=v1", mode], root)
    if text:
        raise RuntimeError("working tree has tracked changes; commit, stash, or reset before running workflow\n" + text)


def candidate_worktree(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "worktrees" / f"{normalize_agent(agent)}-candidate"


def candidate_file(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "candidates" / f"{normalize_agent(agent)}.json"


def receipt_file(root: Path, agent: str) -> Path:
    return root / FORKS_DIR / "receipts" / f"{normalize_agent(agent)}.json"


def remove_worktree(root: Path, work: Path) -> None:
    if work.exists():
        git(["worktree", "remove", "--force", str(work)], root, check=False)
    if work.exists():
        shutil.rmtree(work)
    git(["worktree", "prune"], root, check=False)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_workflow(root: Path, name: str) -> dict[str, Any]:
    safe = name.strip().replace("\\", "/")
    if "/" in safe or not safe:
        raise RuntimeError(f"invalid workflow name: {name!r}")
    path = root / WORKFLOW_DIR / f"{safe}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    elif safe in BUILTIN_WORKFLOWS:
        data = BUILTIN_WORKFLOWS[safe]
    else:
        raise RuntimeError(f"missing workflow: {path}")
    if data.get("name") != safe:
        raise RuntimeError(f"workflow name mismatch for {safe}")
    return data


def bind_workflow(workflow: dict[str, Any], argv: list[str]) -> dict[str, str]:
    params = workflow.get("parameters", [])
    if len(argv) != len(params):
        raise RuntimeError(f"workflow {workflow.get('name')} expects {len(params)} argument(s): {', '.join(params)}")
    bound = {str(name): value for name, value in zip(params, argv)}
    if "agent" in bound:
        bound["agent"] = normalize_agent(bound["agent"])
    return bound


def subst(value: Any, env: dict[str, str]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        key = value[1:]
        if key not in env:
            raise RuntimeError(f"unknown workflow parameter: {value}")
        return env[key]
    if isinstance(value, list):
        return [subst(v, env) for v in value]
    if isinstance(value, dict):
        return {k: subst(v, env) for k, v in value.items()}
    return value


def op_fetch_origin(root: Path, step: dict[str, Any]) -> None:
    fetch_origin(root)
    print("ok fetch origin")


def op_assert_no_tracked_changes(root: Path, step: dict[str, Any]) -> None:
    assert_no_tracked_changes(root, bool(step.get("allow_untracked", True)))
    print("ok clean tracked worktree")


def op_require_agent_ahead_only(root: Path, step: dict[str, Any]) -> None:
    agent = normalize_agent(step["agent"])
    ref = best_agent_ref(root, agent)
    ahead, behind = ahead_behind(root, ref)
    state = classify(ahead, behind)
    if state != "ahead-only":
        raise RuntimeError(f"{agent_branch(agent)} must be ahead-only to land directly; state={state} ahead={ahead} behind={behind}")
    print(f"ok {agent_branch(agent)} ahead-only ahead={ahead}")


def op_stage_candidate_direct(root: Path, step: dict[str, Any]) -> None:
    agent = normalize_agent(step["agent"])
    ref = best_agent_ref(root, agent)
    ahead, behind = ahead_behind(root, ref)
    if classify(ahead, behind) != "ahead-only":
        raise RuntimeError(f"direct staging requires ahead-only branch; ahead={ahead} behind={behind}")
    work = candidate_worktree(root, agent)
    remove_worktree(root, work)
    git(["worktree", "add", "--detach", str(work), ref], root)
    data = {
        "format": "LS_FORK_WORKFLOW_CANDIDATE_V1",
        "agent": agent,
        "strategy": "direct-ahead-only",
        "worktree": str(work),
        "source_ref": ref,
        "current_main_snapshot_at_stage": compact_snapshot(root, MAIN_REF),
        "candidate_snapshot": compact_snapshot(work, "HEAD"),
        "candidate_commit": commit(work, "HEAD"),
        "candidate_tree": tree_hash(work, "HEAD"),
        "ahead": ahead,
        "behind": behind,
        "created_at": now_iso(),
    }
    write_json(candidate_file(root, agent), data)
    print(f"ok staged direct candidate {agent} at {work}")


def op_verify_candidate(root: Path, step: dict[str, Any]) -> None:
    agent = normalize_agent(step["agent"])
    command = str(step.get("command", "verify.bat"))
    data_path = candidate_file(root, agent)
    if not data_path.exists():
        raise RuntimeError(f"missing candidate file: {data_path}")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    work = Path(data["worktree"])
    if not work.exists():
        raise RuntimeError(f"candidate worktree missing: {work}")
    fetch_origin(root)
    if compact_snapshot(root, MAIN_REF)["tree"] != data["current_main_snapshot_at_stage"]["tree"]:
        raise RuntimeError("origin/main moved since staging; rerun workflow")
    ahead, behind = ahead_behind(work, "HEAD")
    if behind != 0:
        raise RuntimeError(f"candidate is stale: ahead={ahead} behind={behind}")
    proc = subprocess.run(command, cwd=str(work), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    receipt = {
        **data,
        "format": "LS_FORK_WORKFLOW_VERIFY_RECEIPT_V1",
        "verified": proc.returncode == 0,
        "verified_at": now_iso(),
        "verify_command": command,
        "verify_exit_code": proc.returncode,
        "verify_stdout": proc.stdout[-8000:],
        "verify_stderr": proc.stderr[-8000:],
        "ahead": ahead,
        "behind": behind,
        "candidate_commit": commit(work, "HEAD"),
        "candidate_tree": tree_hash(work, "HEAD"),
    }
    write_json(receipt_file(root, agent), receipt)
    if proc.returncode != 0:
        raise RuntimeError(f"verification failed with exit code {proc.returncode}")
    print(f"ok verified {agent}")


def op_push_main_fast_forward(root: Path, step: dict[str, Any]) -> None:
    agent = normalize_agent(step["agent"])
    data = json.loads(candidate_file(root, agent).read_text(encoding="utf-8"))
    receipt = json.loads(receipt_file(root, agent).read_text(encoding="utf-8"))
    if not receipt.get("verified"):
        raise RuntimeError("candidate lacks verified receipt")
    work = Path(data["worktree"])
    fetch_origin(root)
    if compact_snapshot(root, MAIN_REF)["tree"] != data["current_main_snapshot_at_stage"]["tree"]:
        raise RuntimeError("origin/main moved since verification; rerun workflow")
    if receipt.get("candidate_commit") != commit(work, "HEAD"):
        raise RuntimeError("candidate HEAD differs from verification receipt")
    ancestor = git(["merge-base", "--is-ancestor", MAIN_REF, "HEAD"], work, check=False)
    if ancestor.returncode != 0:
        raise RuntimeError("origin/main is not an ancestor of candidate HEAD")
    ahead, behind = ahead_behind(work, "HEAD")
    if behind != 0 or ahead == 0:
        raise RuntimeError(f"candidate cannot advance main: ahead={ahead} behind={behind}")
    proc = git(["push", "origin", "HEAD:main"], work, check=False)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError("non-force push to main failed; main likely moved")
    fetch_origin(root)
    print("ok pushed main fast-forward")


def sync_branch_to_main(root: Path, branch: str) -> None:
    if not ref_exists(root, branch):
        git(["branch", branch, MAIN_REF], root)
        print(f"{branch}: created at {short_commit(root, MAIN_REF)}")
        return
    ahead, behind = ahead_behind(root, branch)
    state = classify(ahead, behind)
    if state == "even":
        print(f"{branch}: even")
        return
    if state == "behind-only":
        if current_branch(root) == branch:
            git(["reset", "--hard", MAIN_REF], root)
        else:
            git(["branch", "-f", branch, MAIN_REF], root)
        print(f"{branch}: synced to {short_commit(root, MAIN_REF)}")
        return
    raise RuntimeError(f"refusing to sync {branch}; it has unique work state={state} ahead={ahead} behind={behind}")


def op_sync_lanes(root: Path, step: dict[str, Any]) -> None:
    fetch_origin(root)
    agents = step.get("agents", list(AGENTS))
    for agent in agents:
        sync_branch_to_main(root, agent_branch(str(agent)))


def op_status(root: Path, step: dict[str, Any]) -> None:
    fetch_origin(root)
    print(f"main {short_commit(root, MAIN_REF)}")
    for agent in AGENTS:
        branch = agent_branch(agent)
        ref = branch if ref_exists(root, branch) else f"origin/{branch}"
        if not ref_exists(root, ref):
            print(f"{branch}: missing")
            continue
        ahead, behind = ahead_behind(root, ref)
        print(f"{branch}: {classify(ahead, behind)} ahead={ahead} behind={behind} head={short_commit(root, ref)}")


OPS = {
    "fetch_origin": op_fetch_origin,
    "assert_no_tracked_changes": op_assert_no_tracked_changes,
    "require_agent_ahead_only": op_require_agent_ahead_only,
    "stage_candidate_direct": op_stage_candidate_direct,
    "verify_candidate": op_verify_candidate,
    "push_main_fast_forward": op_push_main_fast_forward,
    "sync_lanes": op_sync_lanes,
    "status": op_status,
}


def run_workflow(name: str, argv: list[str]) -> int:
    root = repo_root()
    ensure_dirs(root)
    workflow = load_workflow(root, name)
    env = bind_workflow(workflow, argv)
    print(f"workflow {name} start")
    for raw_step in workflow.get("steps", []):
        step = subst(raw_step, env)
        op = step.get("op")
        if op not in OPS:
            raise RuntimeError(f"unknown workflow op: {op}")
        print(f"-- {op}")
        OPS[op](root, step)
    run_record = {
        "format": "LS_FORK_WORKFLOW_RUN_V1",
        "workflow": name,
        "parameters": env,
        "completed_at": now_iso(),
    }
    write_json(root / FORKS_DIR / "workflow-runs" / f"{name}.json", run_record)
    print(f"workflow {name} complete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks workflow", description="Run abstract forks workflows")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="run a named workflow")
    p.add_argument("workflow")
    p.add_argument("args", nargs="*")
    p = sub.add_parser("land", help="land an ahead-only agent branch")
    p.add_argument("agent")
    p = sub.add_parser("sync-all", help="sync all agent lanes that have no unique work")
    p = sub.add_parser("verify-agent", help="stage and verify an ahead-only agent branch without pushing main")
    p.add_argument("agent")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return run_workflow(args.workflow, args.args)
        if args.command == "land":
            return run_workflow("land-agent", [args.agent])
        if args.command == "sync-all":
            return run_workflow("sync-lanes", [])
        if args.command == "verify-agent":
            return run_workflow("verify-agent", [args.agent])
        raise RuntimeError(f"unknown command: {args.command}")
    except Exception as exc:
        print(f"forks workflow: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
