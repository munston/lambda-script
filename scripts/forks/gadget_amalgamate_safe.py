#!/usr/bin/env python3
"""Safe gadget-agent amalgamation.

This wrapper preserves the existing direct-lane capture semantics while changing
the dangerous ordering in the old gadget path. It captures the gadget-agent lane,
applies the captured patch to the gadget integration branch, runs the declared
verifier, pushes the integration branch, and only then rewinds/syncs the source
lane.

This prevents a failed verifier from erasing the visible agent lane.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import amalgamate_all
import forks

DEFAULT_AGENTS = ("ed", "edd", "eddy", "guy")


def describe_verify(command: str) -> None:
    print(f"VERIFY COMMAND: {command}")
    if command.strip().lower() == "verify.bat":
        print("warning: using default verify.bat; pass --verify-command for gadget-local verification", file=sys.stderr)


def safe_plan_agent(root: Path, gizmo: str, gadget: str, agent: str, args: argparse.Namespace) -> None:
    base_ref = amalgamate_all.gadget_base_ref(gizmo, gadget)
    branch = amalgamate_all.gadget_lane_branch(agent, gizmo, gadget)
    ref = amalgamate_all.gadget_lane_ref(root, agent, gizmo, gadget)
    if not ref:
        print(f"{agent}: missing gadget lane {branch}; final sync will create it")
        return
    ahead, behind = forks.ahead_behind(root, ref, base_ref)
    state = forks.classify(ahead, behind)
    print(f"{agent}: gadget {state} ahead={ahead} behind={behind} source={ref} base={base_ref}")
    if state in {"ahead-only", "diverged"}:
        print(f"  will capture direct gadget lane delta from {ref}")
        print(f"  will apply captured delta to {amalgamate_all.gadget_integration_branch(gizmo, gadget)}")
        print(f"  will verify with: {args.verify_command}")
        print("  will sync source lane only after the integration push succeeds")
    else:
        print("  no direct gadget lane delta; final sync will align this lane to gadget integration")


def safe_apply_agent(root: Path, gizmo: str, gadget: str, agent: str, args: argparse.Namespace) -> None:
    forks.git(["fetch", "--prune", "origin"], root)
    base_ref = amalgamate_all.gadget_base_ref(gizmo, gadget)
    if not forks.ref_exists(root, base_ref):
        raise RuntimeError(f"missing gadget integration ref: {base_ref}")

    branch = amalgamate_all.gadget_lane_branch(agent, gizmo, gadget)
    ref = amalgamate_all.gadget_lane_ref(root, agent, gizmo, gadget)
    if not ref:
        print(f"{agent}: missing gadget lane {branch}; final sync will create it")
        return

    ahead, behind = forks.ahead_behind(root, ref, base_ref)
    state = forks.classify(ahead, behind)
    print(f"{agent}: gadget {state} ahead={ahead} behind={behind} source={ref} base={base_ref}")
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no direct gadget lane delta")
        return

    submission = amalgamate_all.make_gadget_submission(root, gizmo, gadget, agent, ref, base_ref)
    amalgamate_all.write_gadget_submission(root, gizmo, gadget, agent, submission)
    describe_verify(args.verify_command)
    print("safe order: integration apply/verify/push before source lane sync")

    amalgamate_all.apply_gadget_patch_to_integration(root, gizmo, gadget, agent, submission, args)

    forks.git(["fetch", "--prune", "origin"], root)
    refreshed_base_ref = amalgamate_all.gadget_base_ref(gizmo, gadget)
    amalgamate_all.destructive_sync_gadget_lane_to_base(
        root,
        branch,
        refreshed_base_ref,
        submission["source_commit"],
    )
    forks.git(["fetch", "--prune", "origin"], root)


def run_gadget(args: argparse.Namespace, root: Path, agents: list[str]) -> int:
    gizmo, gadget = args.gadget
    forks.git(["fetch", "--prune", "origin"], root)
    if not args.skip_replay_audit:
        amalgamate_all.audit_gadget_replay_materialisation(
            root,
            gizmo,
            gadget,
            agents,
            require_ledgers=args.require_ledgers,
            strict_agent_docs=getattr(args, "strict_agent_docs", False),
        )
    if not args.apply:
        print(f"safe gadget amalgamation plan only for {gizmo}/{gadget}; pass --apply to mutate")
        for agent in agents:
            safe_plan_agent(root, gizmo, gadget, agent, args)
        return 0

    for agent in agents:
        safe_apply_agent(root, gizmo, gadget, agent, args)

    if not args.skip_final_sync:
        amalgamate_all.gadget_final_sync(root, gizmo, gadget, agents)
    if not args.skip_final_assert:
        amalgamate_all.gadget_assert_clean(root, gizmo, gadget, agents)
    if not args.skip_replay_audit:
        amalgamate_all.audit_gadget_replay_materialisation(
            root,
            gizmo,
            gadget,
            agents,
            require_ledgers=args.require_ledgers,
            strict_agent_docs=getattr(args, "strict_agent_docs", False),
        )
    print("safe gadget amalgamation complete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gadget-amalgamate-safe",
        description="Safely amalgamate gadget-agent lanes without rewinding the source lane before verification succeeds.",
    )
    parser.add_argument("--gadget", nargs=2, required=True, metavar=("GIZMO", "GADGET"))
    parser.add_argument("--agents", nargs="+", default=list(DEFAULT_AGENTS), help="agent lanes to inspect; default: ed edd eddy guy")
    parser.add_argument("--verify-command", default="verify.bat", help="verification command run in the replayed gadget candidate")
    parser.add_argument("--apply", action="store_true", help="mutate: capture/apply/verify/push/sync")
    parser.add_argument("--skip-final-sync", action="store_true")
    parser.add_argument("--skip-final-assert", action="store_true")
    parser.add_argument("--skip-replay-audit", action="store_true")
    parser.add_argument("--require-ledgers", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = forks.repo_root()
    forks.ensure_dirs(root)
    agents = [forks.normalize_agent(a) for a in args.agents]
    try:
        return run_gadget(args, root, agents)
    except Exception as exc:
        print(f"gadget-amalgamate-safe: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
