#!/usr/bin/env python3
"""Land a JSON patch to a gadget integration branch and sync gadget agent lanes."""

from __future__ import annotations

import argparse
import sys
from types import SimpleNamespace

import forks
import gadget_branches
import gadget_verify_profiles
import land_json_patch


def resolve_profile_commands(args: argparse.Namespace) -> tuple[str | None, list[str] | None, bool]:
    profile = args.profile
    if args.full and profile is None:
        profile = "full"
    if profile is None:
        profile = "quick"

    root = forks.repo_root()
    commands = gadget_verify_profiles.profile_commands(root, args.gizmo, args.gadget, profile)
    if commands is not None:
        return profile, commands, False

    if args.profile:
        raise RuntimeError(f"missing verification profile {profile} for {args.gizmo}/{args.gadget}")

    return None, None, args.full


def cmd_land(args: argparse.Namespace) -> int:
    target = gadget_branches.target_ref(args.gizmo, args.gadget)
    profile, commands, full_fallback = resolve_profile_commands(args)
    print(f"gadget target: {target}")
    if commands is not None:
        print(f"verification profile: {profile}")

    land_args = SimpleNamespace(
        require_file=args.require_file,
        full=full_fallback,
        target_ref=target,
        push_ref=None,
        no_sync=True,
        agent=args.agent,
        file=args.file,
        verify_commands=commands,
        verify_profile=profile,
    )

    rc = land_json_patch.cmd_land(land_args)
    if rc != 0:
        return rc

    print("syncing gadget agent lanes")
    sync_args = SimpleNamespace(gizmo=args.gizmo, gadget=args.gadget)
    gadget_branches.cmd_sync_all(sync_args)

    print("gadget status")
    status_args = SimpleNamespace(gizmo=args.gizmo, gadget=args.gadget, json=False)
    gadget_branches.cmd_status(status_args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks gadget-land-json")
    parser.add_argument("--require-file", action="store_true")
    parser.add_argument("--full", action="store_true", help="use the full manifest verification profile, or verify.bat fallback")
    parser.add_argument("--profile", help="manifest verification profile to run before submit; defaults to quick")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("agent")
    parser.add_argument("file", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.require_file and not args.file:
            raise RuntimeError("gadget-land-json-file requires a JSON patch file path")
        return cmd_land(args)
    except Exception as exc:
        print(f"forks gadget-land-json: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
