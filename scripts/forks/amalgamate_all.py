#!/usr/bin/env python3
"""Guarded sequential amalgamation for agent lanes.

This command implements the operator workflow:

1. Agent lanes may contain direct commits or prior replayable submissions.
2. Before any lane is rewound, its unique work must be represented as a
   replayable submission object.
3. If a valid submission already exists for the current lane head, reuse it.
4. If no valid submission exists, capture the current lane diff as a submission.
5. After replay history is adequate, destructively sync the captured lane to
   current main.
6. Replay, verify, and submit that agent's captured diff onto the latest main.
7. Fetch the advanced main, then continue with the next agent.

Main is never rewound by this tool. Agent lanes may be rewound only after their
work is captured and the captured source commit matches the lane head.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import forks
import submission_object

DEFAULT_AGENTS = ("ed", "edd", "eddy")


def run_submission(root: Path, argv: list[str]) -> None:
    code = submission_object.main(argv)
    if code != 0:
        raise RuntimeError(f"submission command failed: {' '.join(argv)}")


def tracked_status(root: Path) -> str:
    return forks.git_text(["status", "--porcelain=v1", "--untracked-files=no"], root)


def require_clean_tracked(root: Path) -> None:
    """Protect operator-local tracked edits.

    This command captures committed lane state. It does not silently convert
    arbitrary uncommitted operator-local edits into agent submissions.
    """
    status = tracked_status(root)
    if status.strip():
        raise RuntimeError(
            "working tree has tracked changes; commit them to the intended agent lane "
            "or restore them before amalgamate-all\n" + status
        )


def best_ref_or_none(root: Path, agent: str) -> str | None:
    branch = forks.agent_branch(agent)
    if forks.ref_exists(root, branch):
        return branch
    remote = f"origin/{branch}"
    if forks.ref_exists(root, remote):
        return remote
    return None


def commit_of(root: Path, ref: str) -> str:
    return forks.commit(root, ref)


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


def short(value: str | None) -> str:
    if not value:
        return "<missing>"
    return value[:8]


def capture_if_needed(root: Path, agent: str, ref: str, args: argparse.Namespace) -> bool:
    source_commit = commit_of(root, ref)
    if existing_submission_matches(root, agent, source_commit):
        print(f"{agent}: replay history already adequate for {short(source_commit)}")
        return False

    print(f"{agent}: creating replay history from {ref} at {short(source_commit)}")
    cmd = ["capture", agent, "--from-ref", ref]
    if args.allow_forbidden:
        cmd.append("--allow-forbidden")
    run_submission(root, cmd)
    return True


def sync_captured_lane(root: Path, agent: str) -> None:
    """Destructively sync the lane only after submission_object proves safety."""
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
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no unique lane work; ordinary sync can handle this lane")
        return

    source_commit = commit_of(root, ref)
    if existing_submission_matches(root, agent, source_commit):
        print(f"  replay history adequate: .forks/submissions/{agent}.json matches {short(source_commit)}")
    else:
        print(f"  will create replay history from {ref} at {short(source_commit)}")
        cmd = ["forks.bat", "capture", agent, "--from-ref", ref]
        if args.allow_forbidden:
            cmd.append("--allow-forbidden")
        print("  " + " ".join(cmd))

    print(f"  forks.bat sync-captured-lane {agent} --yes")
    print(f"  forks.bat replay {agent} --rebase-stale")
    print(f"  forks.bat verify-submission {agent} --command {args.verify_command}")
    print(f"  forks.bat submit-submission {agent} --backend {args.backend} --dry-run")
    print(f"  forks.bat submit-submission {agent} --backend {args.backend}")
    print("  git fetch origin --prune")


def apply_agent(root: Path, agent: str, ref: str, state: str, ahead: int, behind: int, args: argparse.Namespace) -> None:
    print(f"{agent}: {state} ahead={ahead} behind={behind} source={ref}")
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no unique lane work")
        return

    capture_if_needed(root, agent, ref, args)
    sync_captured_lane(root, agent)
    forks.fetch_main(root)
    replay_verify_submit(root, agent, args)
    forks.fetch_main(root)


def sync_clean_lane(root: Path, agent: str) -> None:
    branch = forks.ensure_local_agent_branch(root, agent)
    ahead, behind = forks.ahead_behind(root, branch)
    state = forks.classify(ahead, behind)
    if state in {"even", "behind-only"}:
        print(f"{agent}: syncing clean lane through workflow sync")
        # Use the existing safe branch reset behaviour by delegating to workflow runner.
        import workflow_runner
        workflow_runner.carry_agent(root, agent)
    else:
        print(f"{agent}: unique work remains; not clean-syncing state={state}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forks amalgamate-all",
        description="Ensure replay history, rewind agent lanes, then replay/verify/submit each agent sequentially.",
    )
    parser.add_argument("--agents", nargs="+", default=list(DEFAULT_AGENTS), help="agent lanes to inspect; default: ed edd eddy")
    parser.add_argument("--verify-command", default="verify.bat", help="verification command run in the replayed candidate")
    parser.add_argument("--backend", choices=("ref", "contents"), default="ref", help="submission backend")
    parser.add_argument("--allow-forbidden", action="store_true", help="allow guarded paths during capture/replay/verify")
    parser.add_argument("--apply", action="store_true", help="mutate: capture/prove, rewind, replay, verify, submit")
    parser.add_argument("--sync-clean", action="store_true", help="also sync even/behind-only lanes after inspection")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = forks.repo_root()
    forks.ensure_dirs(root)
    agents = [forks.normalize_agent(a) for a in args.agents]

    try:
        require_clean_tracked(root)
        forks.fetch_main(root)

        if not args.apply:
            print("amalgamate-all plan only; pass --apply to mutate")

        for agent in agents:
            # Re-fetch and re-resolve before each agent because previous agents may
            # have advanced main.
            forks.fetch_main(root)
            ref = best_ref_or_none(root, agent)
            if not ref:
                print(f"{agent}: missing lane; skipped")
                continue
            ahead, behind = forks.ahead_behind(root, ref)
            state = forks.classify(ahead, behind)

            if args.apply:
                apply_agent(root, agent, ref, state, ahead, behind, args)
                if args.sync_clean:
                    sync_clean_lane(root, agent)
            else:
                plan_agent(root, agent, ref, state, ahead, behind, args)

        if args.apply:
            print("amalgamate-all complete")
        return 0
    except Exception as exc:
        print(f"forks amalgamate-all: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
