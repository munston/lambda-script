#!/usr/bin/env python3
"""Route a JSON patch by the target information inside the patch itself.

This is the canonical patch landing entry point for model-facing use. Targeted
land buttons may exist as labels, but they are only conveniences: the patch
payload decides where it belongs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import forks
import process_result


def script(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        raise RuntimeError(f"missing required tool: {rel}")
    return str(path)


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
    code = process_result.run_step_quiet(
        "land-anything",
        [
            sys.executable,
            script(root, "scripts/forks/land_json_patch.py"),
            "--require-file",
            "--target-ref",
            target_ref,
            "--push-ref",
            push_ref,
            "--no-sync",
            agent,
            str(patch),
        ],
        root,
    )
    if code == 0:
        print("land-anything: landed.")
    else:
        print("land-anything: failed.")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"land-anything: {exc}", file=sys.stderr)
        raise SystemExit(1)
