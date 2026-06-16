#!/usr/bin/env python3
"""Land a JSON patch to a gadget integration branch without implicit lane sync.

This command records replay history and advances the gadget integration target.
It deliberately does not force-align gadget-agent lanes by default. Lane
propagation belongs to an explicit sync/amalgamation command so that operators
and agents can inspect outstanding replay evidence before destructive alignment.

Use --align-lanes only for manual repair or an explicitly requested immediate
sync.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
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


def fetch(root: Path) -> None:
    forks.git(["fetch", "--prune", "origin"], root)


def force_align_branch(root: Path, branch: str, source_ref: str) -> None:
    fetch(root)
    if not forks.ref_exists(root, source_ref):
        raise RuntimeError(f"missing source ref: {source_ref}")
    commit = forks.commit(root, source_ref)
    if forks.current_branch(root) == branch:
        forks.git(["reset", "--hard", commit], root)
    elif forks.ref_exists(root, branch):
        forks.git(["branch", "-f", branch, commit], root)
    else:
        forks.git(["branch", branch, commit], root)
    forks.git(["push", "--force-with-lease", "origin", f"{commit}:refs/heads/{branch}"], root)
    fetch(root)


def force_align_gadget_lanes(root: Path, gizmo: str, gadget: str, source_ref: str) -> None:
    print("explicitly syncing gadget integration and agent lanes")
    force_align_branch(root, gadget_branches.integration_branch(gizmo, gadget), source_ref)
    for agent in gadget_branches.AGENTS:
        force_align_branch(root, gadget_branches.gadget_agent_branch(agent, gizmo, gadget), source_ref)


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

    root = forks.repo_root()
    fetch(root)
    if args.align_lanes:
        force_align_gadget_lanes(root, args.gizmo, args.gadget, target)
    else:
        print("skipped gadget-agent lane alignment")
        print("run amalgamate-all --gadget ... --apply, gadget-sync-all, or pass --align-lanes explicitly")

    print("gadget status")
    status_args = SimpleNamespace(gizmo=args.gizmo, gadget=args.gadget, json=False)
    gadget_branches.cmd_status(status_args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks gadget-land-json")
    parser.add_argument("--require-file", action="store_true")
    parser.add_argument("--full", action="store_true", help="use the full manifest verification profile, or verify.bat fallback")
    parser.add_argument("--profile", help="manifest verification profile to run before submit; defaults to quick")
    parser.add_argument(
        "--align-lanes",
        action="store_true",
        dest="align_lanes",
        help="explicitly force-align gadget-agent lanes after a successful landing",
    )
    parser.add_argument(
        "--no-align-lanes",
        action="store_false",
        dest="align_lanes",
        help="compatibility option; this is now the default",
    )
    parser.set_defaults(align_lanes=False)
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
