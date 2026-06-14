#!/usr/bin/env python3
"""Land a targeted JSON patch using a hardcoded agent lane.

The public button shape is intentionally one argument:

    guy-land-json.bat path\to\patch.json

The patch itself carries its target:

    {
      "format": "LS_FORK_JSON_PATCH_V1",
      "agent": "guy",
      "target": {
        "kind": "gadget",
        "gizmo": "lambdascript",
        "gadget": "core",
        "profile": "quick"
      },
      "title": "...",
      "files": [...]
    }
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import gadget_land_json
import import_json_patch


VALID_AGENTS = {"ed", "edd", "eddy", "guy"}


def resolve_target(payload: dict) -> tuple[str, str, str | None, bool]:
    target = payload.get("target")
    if not isinstance(target, dict):
        raise RuntimeError("JSON patch is missing target object")

    kind = target.get("kind", "gadget")
    if kind != "gadget":
        raise RuntimeError(f"unsupported target kind: {kind!r}; expected 'gadget'")

    gizmo = target.get("gizmo")
    gadget = target.get("gadget") or target.get("lane")
    if not isinstance(gizmo, str) or not gizmo:
        raise RuntimeError("target.gizmo must be a non-empty string")
    if not isinstance(gadget, str) or not gadget:
        raise RuntimeError("target.gadget must be a non-empty string")

    profile = target.get("profile")
    if profile is not None and (not isinstance(profile, str) or not profile):
        raise RuntimeError("target.profile must be a non-empty string when present")

    full = bool(target.get("full", False))
    return gizmo, gadget, profile, full


def validate_agent(hardcoded_agent: str, payload: dict, strict_agent: bool) -> None:
    if hardcoded_agent not in VALID_AGENTS:
        raise RuntimeError(f"unknown hardcoded agent: {hardcoded_agent}")

    declared = payload.get("agent")
    if declared is None:
        return
    if not isinstance(declared, str) or not declared:
        raise RuntimeError("patch agent field must be a non-empty string when present")
    if strict_agent and declared != hardcoded_agent:
        raise RuntimeError(f"patch declares agent {declared!r}, but this button is for {hardcoded_agent!r}")


def cmd_land(args: argparse.Namespace) -> int:
    patch_path = Path(args.file)
    if not patch_path.exists():
        raise RuntimeError(f"missing JSON patch file: {patch_path}")

    payload = import_json_patch.load_payload(str(patch_path))
    validate_agent(args.agent, payload, args.strict_agent)
    gizmo, gadget, profile, full = resolve_target(payload)

    print(f"agent={args.agent}")
    print(f"target={gizmo}/{gadget}")
    if profile:
        print(f"profile={profile}")
    elif full:
        print("profile=full")

    land_args = SimpleNamespace(
        require_file=True,
        full=full,
        profile=profile,
        gizmo=gizmo,
        gadget=gadget,
        agent=args.agent,
        file=str(patch_path),
    )
    return gadget_land_json.cmd_land(land_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-land-json")
    parser.add_argument("agent")
    parser.add_argument("file")
    parser.add_argument("--strict-agent", action="store_true", default=True)
    parser.add_argument("--no-strict-agent", action="store_false", dest="strict_agent")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return cmd_land(args)
    except Exception as exc:
        print(f"agent-land-json: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
