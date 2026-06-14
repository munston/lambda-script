#!/usr/bin/env python3
"""Gadget branch management for forks-backed gizmos.

This tool creates and inspects gadget integration branches and the corresponding
agent lanes. It does not land patches. Patch landing is handled by the JSON
landing path with --target-ref.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import forks

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
AGENTS = forks.AGENTS


def clean_name(kind: str, value: str) -> str:
    name = value.strip()
    if not NAME_RE.match(name):
        raise RuntimeError(f"invalid {kind} name: {value!r}")
    return name


def integration_branch(gizmo: str, gadget: str) -> str:
    return f"gadgets/{clean_name('gizmo', gizmo)}/{clean_name('gadget', gadget)}/main"


def target_ref(gizmo: str, gadget: str) -> str:
    return f"origin/{integration_branch(gizmo, gadget)}"


def gadget_agent_branch(agent: str, gizmo: str, gadget: str) -> str:
    return f"gadget-agents/{clean_name('gizmo', gizmo)}/{clean_name('gadget', gadget)}/{forks.normalize_agent(agent)}"


def remote_ref(branch: str) -> str:
    return f"origin/{branch}"


def fetch(root: Path) -> None:
    forks.git(["fetch", "--prune", "origin"], root)


def ensure_ref(root: Path, ref: str) -> None:
    if not forks.ref_exists(root, ref):
        raise RuntimeError(f"missing ref: {ref}")


def local_branch_exists(root: Path, branch: str) -> bool:
    return forks.ref_exists(root, branch)


def remote_branch_exists(root: Path, branch: str) -> bool:
    return forks.ref_exists(root, remote_ref(branch))


def create_remote_branch(root: Path, branch: str, source_ref: str) -> None:
    ensure_ref(root, source_ref)
    source_commit = forks.commit(root, source_ref)
    forks.git(["push", "origin", f"{source_commit}:refs/heads/{branch}"], root)


def update_remote_branch(root: Path, branch: str, source_ref: str) -> None:
    ensure_ref(root, source_ref)
    source_commit = forks.commit(root, source_ref)
    forks.git(["push", "origin", f"{source_commit}:refs/heads/{branch}"], root)


def ensure_local_branch(root: Path, branch: str, source_ref: str) -> None:
    if local_branch_exists(root, branch):
        return
    forks.git(["branch", branch, source_ref], root)


def branch_status(root: Path, branch: str, base_ref: str) -> dict[str, Any]:
    local = local_branch_exists(root, branch)
    remote = remote_branch_exists(root, branch)
    ref = branch if local else remote_ref(branch) if remote else None
    if not ref:
        return {
            "branch": branch,
            "exists": False,
            "local": False,
            "remote": False,
            "state": "missing",
            "ahead": 0,
            "behind": 0,
            "head": None,
            "files": [],
        }
    ahead, behind = forks.ahead_behind(root, ref, base_ref)
    return {
        "branch": branch,
        "ref": ref,
        "exists": True,
        "local": local,
        "remote": remote,
        "state": forks.classify(ahead, behind),
        "ahead": ahead,
        "behind": behind,
        "head": forks.short_commit(root, ref),
        "tree": forks.tree_hash(root, ref),
        "files": [item["path"] for item in forks.changed_files(root, ref, base_ref)],
    }


def safe_to_sync_state(row: dict[str, Any]) -> bool:
    return row["state"] in {"missing", "even", "behind-only"}


def assert_sync_safe(root: Path, branch: str, base_ref: str) -> None:
    rows = []
    if local_branch_exists(root, branch):
        rows.append(branch_status(root, branch, base_ref))
    if remote_branch_exists(root, branch):
        rows.append(branch_status(root, branch, base_ref))
    for row in rows:
        if not safe_to_sync_state(row):
            raise RuntimeError(f"refusing to sync {branch}; {row['ref']} is {row['state']} ahead={row['ahead']} behind={row['behind']}")


def sync_branch_to_ref(root: Path, branch: str, base_ref: str) -> None:
    assert_sync_safe(root, branch, base_ref)
    if forks.current_branch(root) == branch:
        forks.git(["reset", "--hard", base_ref], root)
    elif local_branch_exists(root, branch):
        forks.git(["branch", "-f", branch, base_ref], root)
    else:
        forks.git(["branch", branch, base_ref], root)
    update_remote_branch(root, branch, base_ref)
    fetch(root)


def ensure_gadget_branch(root: Path, gizmo: str, gadget: str, base_ref: str) -> str:
    branch = integration_branch(gizmo, gadget)
    fetch(root)
    ensure_ref(root, base_ref)
    if not remote_branch_exists(root, branch):
        create_remote_branch(root, branch, base_ref)
        fetch(root)
        print(f"{branch}: created remote at {forks.short_commit(root, remote_ref(branch))}")
    sync_branch_to_ref(root, branch, base_ref)
    print(f"{branch}: local ready at {forks.short_commit(root, branch)}")
    return branch


def ensure_agent_lane(root: Path, agent: str, gizmo: str, gadget: str) -> str:
    base = target_ref(gizmo, gadget)
    branch = gadget_agent_branch(agent, gizmo, gadget)
    ensure_ref(root, base)
    if not remote_branch_exists(root, branch):
        create_remote_branch(root, branch, base)
        fetch(root)
        print(f"{branch}: created remote at {forks.short_commit(root, remote_ref(branch))}")
    sync_branch_to_ref(root, branch, base)
    print(f"{branch}: local ready at {forks.short_commit(root, branch)}")
    return branch


def cmd_init(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    ensure_gadget_branch(root, args.gizmo, args.gadget, args.base_ref)
    if not args.no_agents:
        for agent in AGENTS:
            ensure_agent_lane(root, agent, args.gizmo, args.gadget)
    return 0


def status_payload(root: Path, gizmo: str, gadget: str) -> dict[str, Any]:
    fetch(root)
    branch = integration_branch(gizmo, gadget)
    target = target_ref(gizmo, gadget)
    integration = branch_status(root, branch, forks.MAIN_REF) if remote_branch_exists(root, branch) or local_branch_exists(root, branch) else {
        "branch": branch,
        "target_ref": target,
        "exists": False,
        "state": "missing",
    }
    agents = [branch_status(root, gadget_agent_branch(agent, gizmo, gadget), target) for agent in AGENTS]
    return {
        "format": "LS_GADGET_BRANCH_STATUS_V1",
        "gizmo": clean_name("gizmo", gizmo),
        "gadget": clean_name("gadget", gadget),
        "integration_branch": branch,
        "target_ref": target,
        "integration": integration,
        "agents": agents,
    }


def print_status(data: dict[str, Any]) -> None:
    print(f"gadget {data['gizmo']}/{data['gadget']}")
    print(f"target {data['target_ref']}")
    integration = data["integration"]
    if integration.get("exists"):
        print(f"{integration['branch']}: {integration['state']} head={integration['head']}")
    else:
        print(f"{integration['branch']}: missing")
    for row in data["agents"]:
        if row.get("exists"):
            print(f"{row['branch']}: {row['state']} ahead={row['ahead']} behind={row['behind']} head={row['head']} files={len(row['files'])}")
        else:
            print(f"{row['branch']}: missing")


def cmd_status(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    data = status_payload(root, args.gizmo, args.gadget)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_status(data)
    return 0


def sync_agent_lane(root: Path, agent: str, gizmo: str, gadget: str) -> None:
    fetch(root)
    base = target_ref(gizmo, gadget)
    ensure_ref(root, base)
    branch = gadget_agent_branch(agent, gizmo, gadget)
    sync_branch_to_ref(root, branch, base)
    print(f"{branch}: synced to {forks.short_commit(root, base)}")


def cmd_sync(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    sync_agent_lane(root, args.agent, args.gizmo, args.gadget)
    return 0


def cmd_sync_all(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    forks.ensure_dirs(root)
    for agent in AGENTS:
        sync_agent_lane(root, agent, args.gizmo, args.gadget)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks gadget")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create a gadget integration branch and optional agent lanes")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("--base-ref", default=forks.MAIN_REF)
    p.add_argument("--no-agents", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status", help="show gadget integration and agent lane states")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sync", help="sync one gadget agent lane to the gadget integration branch when safe")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("agent")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("sync-all", help="sync all known gadget agent lanes to the gadget integration branch when safe")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.set_defaults(func=cmd_sync_all)

    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"forks gadget: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
