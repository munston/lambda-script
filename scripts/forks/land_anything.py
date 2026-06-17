#!/usr/bin/env python3
"""Route and land a JSON patch using the target information inside the patch.

The patch payload is the routing authority. The agent lane is treated as a
disposable carrier: before landing the new patch, the lane is reconstructed from
the current integration target plus any durable replay entries already recorded
for that agent/target. Branch topology is not used as a hard safety condition.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import forks
import import_json_patch
import replay_ledger


def read_payload(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise RuntimeError(f"patch could not be read as JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("patch root must be a JSON object")
    return value


def scalar(value: Any, name: str) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if value is None:
        return None
    raise RuntimeError(f"{name} must be a string")


def patch_agent(payload: dict[str, Any]) -> str:
    agent = scalar(payload.get("agent"), "agent")
    if agent:
        return forks.normalize_agent(agent)
    author = payload.get("author")
    if isinstance(author, str) and author.strip():
        return forks.normalize_agent(author)
    if isinstance(author, dict):
        for key in ("agent", "name", "id"):
            item = scalar(author.get(key), f"author.{key}")
            if item:
                return forks.normalize_agent(item)
    raise RuntimeError("patch missing agent/author")


def patch_target(payload: dict[str, Any]) -> tuple[str, str, str]:
    target = payload.get("target")
    if not isinstance(target, dict):
        raise RuntimeError("patch missing target object")
    kind = scalar(target.get("kind"), "target.kind") or "gadget"
    kind = kind.lower()
    if kind in ("gadget", "gizmo-gadget"):
        gizmo = scalar(target.get("gizmo"), "target.gizmo")
        gadget = scalar(target.get("gadget"), "target.gadget")
        if not gizmo or not gadget:
            raise RuntimeError("gadget target requires target.gizmo and target.gadget")
        target_ref = scalar(target.get("target_ref"), "target.target_ref") or f"origin/gadgets/{gizmo}/{gadget}/main"
        lane_template = scalar(target.get("agent_branch_template"), "target.agent_branch_template")
        return kind, target_ref, lane_template or f"gadget-agents/{gizmo}/{gadget}/{{agent}}"
    if kind in ("repo", "repository", "main"):
        target_ref = scalar(target.get("target_ref"), "target.target_ref") or forks.MAIN_REF
        lane_template = scalar(target.get("agent_branch_template"), "target.agent_branch_template")
        return kind, target_ref, lane_template or "agents/{agent}"
    raise RuntimeError(f"unsupported target kind: {kind}")


def resolve_lane(template: str, agent: str) -> str:
    if "{agent}" in template:
        return template.replace("{agent}", agent)
    if template.endswith("/"):
        return template + agent
    return template


def tracking_ref(push_ref: str) -> str:
    if push_ref.startswith("origin/"):
        return push_ref
    return f"origin/{push_ref}"


def remote_refname(push_ref: str) -> str:
    branch = push_ref[len("origin/"):] if push_ref.startswith("origin/") else push_ref
    return branch if branch.startswith("refs/heads/") else f"refs/heads/{branch}"


def worktree_path(root: Path, push_ref: str) -> Path:
    return root / forks.FORKS_DIR / "land-anything" / replay_ledger.safe_token(push_ref)


def remove_worktree(root: Path, work: Path) -> None:
    forks.git(["worktree", "remove", "--force", str(work)], root, check=False)
    if work.exists():
        shutil.rmtree(work)
    forks.git(["worktree", "prune"], root, check=False)


def git_show_json(root: Path, ref: str, path: str) -> dict[str, Any] | None:
    if not forks.ref_exists(root, ref):
        return None
    proc = forks.git(["show", f"{ref}:{path}"], root, check=False)
    if proc.returncode != 0:
        return None
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON at {ref}:{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON at {ref}:{path} is not an object")
    return value


def ledger_path_for(agent: str, payload: dict[str, Any], target_ref: str) -> str:
    target = replay_ledger.target_descriptor(payload, target_ref)
    return replay_ledger.ledger_relpath(agent, target)


def ledger_entries(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if data is None:
        return []
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise RuntimeError("replay ledger entries field is not a list")
    out: list[dict[str, Any]] = []
    for item in entries:
        if isinstance(item, dict):
            out.append(item)
    return out


def payload_from_entry(root: Path, ref: str, entry: dict[str, Any]) -> dict[str, Any]:
    digest = entry.get("json_patch_sha256")
    if not isinstance(digest, str) or not digest:
        raise RuntimeError("ledger entry missing json_patch_sha256")
    path = entry.get("payload_path")
    if not isinstance(path, str) or not path:
        path = replay_ledger.payload_relpath(digest)
    data = git_show_json(root, ref, path)
    if data is None:
        raise RuntimeError("replay payload missing")
    replay_ledger.validate_payload_object(data, digest)
    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError("replay payload object has no patch payload")
    return payload


def pending_replay_entries(root: Path, agent: str, target_ref: str, lane_ref: str, new_payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not forks.ref_exists(root, lane_ref):
        return []
    ledger_path = ledger_path_for(agent, new_payload, target_ref)
    base_ledger = git_show_json(root, target_ref, ledger_path)
    lane_ledger = git_show_json(root, lane_ref, ledger_path)
    base_seen = {
        str(item.get("json_patch_sha256"))
        for item in ledger_entries(base_ledger)
        if item.get("json_patch_sha256")
    }
    pending: list[dict[str, Any]] = []
    for item in ledger_entries(lane_ledger):
        digest = str(item.get("json_patch_sha256", ""))
        if digest and digest not in base_seen:
            pending.append(item)
    return pending


def commit_if_changed(work: Path, message: str) -> bool:
    forks.git(["add", "-A"], work)
    if not forks.git_text(["diff", "--cached", "--name-status"], work):
        return False
    forks.git(["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", message], work)
    return True


def push_reconstructed_lane(root: Path, work: Path, push_ref: str, expected_oid: str | None) -> None:
    forks.git(["fetch", "--prune", "origin"], root)
    remote = remote_refname(push_ref)
    track = tracking_ref(push_ref)
    if expected_oid is not None:
        current = forks.commit(root, track) if forks.ref_exists(root, track) else None
        if current != expected_oid:
            raise RuntimeError("remote lane changed during landing")
        forks.git(["push", f"--force-with-lease={remote}:{expected_oid}", "origin", f"HEAD:{remote}"], work)
    else:
        forks.git(["push", "origin", f"HEAD:{remote}"], work)
    forks.git(["fetch", "--prune", "origin"], root)


def rebuild_and_land(root: Path, agent: str, target_ref: str, push_ref: str, patch: Path, payload: dict[str, Any]) -> None:
    forks.ensure_dirs(root)
    forks.git(["fetch", "--prune", "origin"], root)
    if not forks.ref_exists(root, target_ref):
        raise RuntimeError(f"target ref missing: {target_ref}")

    track = tracking_ref(push_ref)
    lane_exists = forks.ref_exists(root, track)
    expected_oid = forks.commit(root, track) if lane_exists else None
    work = worktree_path(root, push_ref)
    remove_worktree(root, work)
    forks.git(["worktree", "add", "--detach", str(work), target_ref], root)

    replayed = 0
    for entry in pending_replay_entries(root, agent, target_ref, track, payload):
        replay_payload = payload_from_entry(root, track, entry)
        import_json_patch.apply_file_ops(work, replay_payload.get("files", []))
        replay_ledger.append_entry(work, agent, replay_payload, target_ref)
        replayed += 1

    if replayed:
        commit_if_changed(work, f"Replay {replayed} pending {agent} patch(es)")

    import_json_patch.apply_file_ops(work, payload.get("files", []))
    replay_ledger.append_entry(work, agent, payload, target_ref)
    title = str(payload.get("title") or "").strip()
    commit_if_changed(work, title or f"Land {agent} patch")
    push_reconstructed_lane(root, work, push_ref, expected_oid)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: land-anything.bat <patch.json>", file=sys.stderr)
        return 2
    patch = Path(argv[0]).expanduser().resolve()
    if not patch.exists() or not patch.is_file():
        print("land-anything: patch file not found", file=sys.stderr)
        return 1
    payload = read_payload(patch)
    agent = patch_agent(payload)
    if agent not in forks.AGENTS:
        raise RuntimeError(f"unsupported agent {agent!r}; expected one of {', '.join(forks.AGENTS)}")
    _kind, target_ref, lane_template = patch_target(payload)
    push_ref = resolve_lane(lane_template, agent)
    root = forks.repo_root()
    rebuild_and_land(root, agent, target_ref, push_ref, patch, payload)
    print("land-anything: landed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"land-anything: failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
