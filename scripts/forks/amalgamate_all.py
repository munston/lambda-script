#!/usr/bin/env python3
"""Guarded sequential amalgamation for agent lanes.

Each agent visit first applies replay-ledger-backed JSON work for that lane, then
captures any remaining direct lane delta as a submission, then replays/verifies/
submits that delta onto the moving main. After all agents are processed, target
lanes are synced to the final main and asserted clean.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import forks
import replay_plan
import replay_sync
import submission_object

DEFAULT_AGENTS = ("ed", "edd", "eddy")


def run_submission(root: Path, argv: list[str]) -> None:
    code = submission_object.main(argv)
    if code != 0:
        raise RuntimeError(f"submission command failed: {' '.join(argv)}")


def run_replay_sync(argv: list[str]) -> None:
    code = replay_sync.main(argv)
    if code != 0:
        raise RuntimeError(f"replay-sync failed: {' '.join(argv)}")


def best_ref_or_none(root: Path, agent: str) -> str | None:
    branch = forks.agent_branch(agent)
    if forks.ref_exists(root, branch):
        return branch
    remote = f"origin/{branch}"
    if forks.ref_exists(root, remote):
        return remote
    return None


def short(value: str | None) -> str:
    if not value:
        return "<missing>"
    return value[:8]


def commit_of(root: Path, ref: str) -> str:
    return forks.commit(root, ref)


def replay_row_for_ref(root: Path, ref: str) -> dict[str, Any] | None:
    plan = replay_plan.build_plan(root, [ref], include_empty=True)
    rows = [row for row in plan.get("refs", []) if row.get("exists", True)]
    if not rows:
        return None
    return rows[0]


def apply_replay_ledger_for_ref(root: Path, ref: str, args: argparse.Namespace) -> None:
    """Apply ledger-backed JSON work for this ref before direct-diff capture."""
    row = replay_row_for_ref(root, ref)
    if row is None:
        print(f"{ref}: no replay row")
        return
    classification = row.get("classification")
    replay_count = int(row.get("total_replay_count", 0))
    missing = int(row.get("total_missing_or_invalid_payload_count", 0))
    if classification in {"fingerprint-divergence", "missing-replay-payload"} or missing:
        raise RuntimeError(f"{ref}: unsafe replay ledger state classification={classification} missing-payloads={missing}")
    if replay_count <= 0:
        print(f"{ref}: no ledger replay entries to apply")
        return

    print(f"{ref}: applying {replay_count} replay-ledger entr{'y' if replay_count == 1 else 'ies'} before lane capture")
    cmd = [ref, "--apply", "--only-replay-needed", "--verify-command", args.verify_command, "--fail-failed"]
    run_replay_sync(cmd)
    forks.fetch_main(root)


def existing_submission_matches(root: Path, agent: str, source_commit: str) -> bool:
    path = submission_object.submission_path(root, agent)
    if not path.exists():
        return False
    try:
        data = submission_object.load_submission(root, agent)
    except Exception as exc:
        print(f"{agent}: existing submission is invalid and will be recaptured: {exc}")
        return False
    captured = data.get("source_commit") or data.get("source_snapshot", {}).get("commit")
    if captured == source_commit:
        return True
    print(f"{agent}: existing submission source {short(captured)} does not match lane head {short(source_commit)}; recapturing")
    return False


def capture_if_needed(root: Path, agent: str, ref: str, args: argparse.Namespace) -> None:
    source_commit = commit_of(root, ref)
    if existing_submission_matches(root, agent, source_commit):
        print(f"{agent}: replay history already adequate for {short(source_commit)}")
        return

    print(f"{agent}: creating replay history from {ref} at {short(source_commit)}")
    cmd = ["capture", agent, "--from-ref", ref]
    if args.allow_forbidden:
        cmd.append("--allow-forbidden")
    run_submission(root, cmd)


def sync_captured_lane(root: Path, agent: str) -> None:
    run_submission(root, ["sync-lane", agent, "--yes"])


def replay_verify_submit(root: Path, agent: str, args: argparse.Namespace) -> None:
    replay = ["replay", agent, "--rebase-stale"]
    if args.allow_forbidden:
        replay.append("--allow-forbidden")
    run_submission(root, replay)

    verify = ["verify", agent, "--command", args.verify_command]
    if args.allow_forbidden:
        verify.append("--allow-forbidden")
    run_submission(root, verify)

    run_submission(root, ["submit", agent, "--backend", args.backend, "--dry-run"])
    run_submission(root, ["submit", agent, "--backend", args.backend])


def plan_agent(root: Path, agent: str, ref: str, state: str, ahead: int, behind: int, args: argparse.Namespace) -> None:
    print(f"{agent}: {state} ahead={ahead} behind={behind} source={ref}")
    row = replay_row_for_ref(root, ref)
    if row and int(row.get("total_replay_count", 0)) > 0:
        print(f"  will first apply {row.get('total_replay_count')} replay-ledger entr{'y' if row.get('total_replay_count') == 1 else 'ies'} for {ref}")
        print(f"  forks.bat replay-sync {ref} --apply --only-replay-needed --verify-command {args.verify_command} --fail-failed")
    if state not in {"ahead-only", "diverged"}:
        print(f"  no direct lane delta; final sync will align this lane to main")
        return

    source_commit = commit_of(root, ref)
    if existing_submission_matches(root, agent, source_commit):
        print(f"  direct-diff replay history adequate: .forks/submissions/{agent}.json matches {short(source_commit)}")
    else:
        print(f"  will capture remaining direct lane delta from {ref} at {short(source_commit)}")
        cmd = ["forks.bat", "capture", agent, "--from-ref", ref]
        if args.allow_forbidden:
            cmd.append("--allow-forbidden")
        print("  " + " ".join(cmd))

    print(f"  forks.bat sync-captured-lane {agent} --yes")
    print(f"  forks.bat replay {agent} --rebase-stale")
    print(f"  forks.bat verify-submission {agent} --command {args.verify_command}")
    print(f"  forks.bat submit-submission {agent} --backend {args.backend} --dry-run")
    print(f"  forks.bat submit-submission {agent} --backend {args.backend}")


def apply_agent(root: Path, agent: str, args: argparse.Namespace) -> None:
    forks.fetch_main(root)
    ref = best_ref_or_none(root, agent)
    if not ref:
        print(f"{agent}: missing lane; skipped")
        return

    apply_replay_ledger_for_ref(root, ref, args)

    # Re-resolve after ledger replay because the ref may have been force-with-lease updated.
    forks.fetch_main(root)
    ref = best_ref_or_none(root, agent)
    if not ref:
        print(f"{agent}: missing lane after replay; skipped")
        return

    ahead, behind = forks.ahead_behind(root, ref)
    state = forks.classify(ahead, behind)
    print(f"{agent}: post-ledger {state} ahead={ahead} behind={behind} source={ref}")
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no direct lane delta after ledger replay")
        return

    capture_if_needed(root, agent, ref, args)
    sync_captured_lane(root, agent)
    forks.fetch_main(root)
    replay_verify_submit(root, agent, args)
    forks.fetch_main(root)


def force_sync_lane_to_main(root: Path, agent: str) -> None:
    branch = forks.ensure_local_agent_branch(root, agent)
    ahead, behind = forks.ahead_behind(root, branch)
    state = forks.classify(ahead, behind)
    if state in {"ahead-only", "diverged"}:
        raise RuntimeError(f"{branch} still has unique work after amalgamation; refusing final sync state={state} ahead={ahead} behind={behind}")

    if forks.current_branch(root) == branch:
        forks.git(["reset", "--hard", forks.MAIN_REF], root)
    else:
        forks.git(["branch", "-f", branch, forks.MAIN_REF], root)

    forks.git(["push", "--force-with-lease", "origin", f"{branch}:{branch}"], root)
    print(f"{branch}: synced to final main {forks.short_commit(root, forks.MAIN_REF)}")


def final_sync_all_lanes(root: Path, agents: list[str]) -> None:
    forks.fetch_main(root)
    print("final lane sync to amalgamated main")
    for agent in agents:
        force_sync_lane_to_main(root, agent)
    forks.fetch_main(root)


def replay_clean_for_agent_row(row: dict[str, Any]) -> bool:
    if not row.get("exists", True):
        return True
    state = row.get("state_against_main")
    classification = row.get("classification")
    if state != "even":
        return False
    return classification in {"no-ledger", "no-replay-needed", "main-has-unseen-ledger-entries"}


def assert_no_outstanding_replay(root: Path, agents: list[str]) -> None:
    refs = [forks.agent_branch(agent) for agent in agents]
    plan = replay_plan.build_plan(root, refs, include_empty=True)
    bad = [row for row in plan["refs"] if not replay_clean_for_agent_row(row)]
    if bad:
        details = []
        for row in bad:
            details.append(
                f"{row.get('ref')}: state={row.get('state_against_main')} "
                f"classification={row.get('classification')} "
                f"replay={row.get('total_replay_count')} "
                f"main-extra={row.get('total_main_extra_count')} "
                f"missing-payloads={row.get('total_missing_or_invalid_payload_count')}"
            )
        raise RuntimeError("outstanding agent lane replay remains after amalgamation\n" + "\n".join(details))
    print("ok no outstanding agent lane replay remains")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forks amalgamate-all",
        description="Apply per-agent replay ledgers, capture direct deltas, submit sequentially, then sync all lanes to final main.",
    )
    parser.add_argument("--agents", nargs="+", default=list(DEFAULT_AGENTS), help="agent lanes to inspect; default: ed edd eddy")
    parser.add_argument("--verify-command", default="verify.bat", help="verification command run in replayed candidates")
    parser.add_argument("--backend", choices=("ref", "contents"), default="ref", help="submission backend")
    parser.add_argument("--allow-forbidden", action="store_true", help="allow guarded paths during capture/replay/verify")
    parser.add_argument("--apply", action="store_true", help="mutate: ledger replay, capture/prove, rewind, replay, verify, submit, final-sync")
    parser.add_argument("--skip-final-sync", action="store_true", help="advanced: do not sync target agent lanes to final main")
    parser.add_argument("--skip-final-assert", action="store_true", help="advanced: do not assert that target lanes are clean after amalgamation")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = forks.repo_root()
    forks.ensure_dirs(root)
    agents = [forks.normalize_agent(a) for a in args.agents]

    try:
        forks.fetch_main(root)

        if not args.apply:
            print("amalgamate-all plan only; pass --apply to mutate")
            for agent in agents:
                forks.fetch_main(root)
                ref = best_ref_or_none(root, agent)
                if not ref:
                    print(f"{agent}: missing lane; skipped")
                    continue
                ahead, behind = forks.ahead_behind(root, ref)
                state = forks.classify(ahead, behind)
                plan_agent(root, agent, ref, state, ahead, behind, args)
            print("final apply will sync target agent lanes to final main and assert no outstanding replay remains")
            return 0

        for agent in agents:
            apply_agent(root, agent, args)

        if not args.skip_final_sync:
            final_sync_all_lanes(root, agents)
        if not args.skip_final_assert:
            assert_no_outstanding_replay(root, agents)
        print("amalgamate-all complete")
        return 0
    except Exception as exc:
        print(f"forks amalgamate-all: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
