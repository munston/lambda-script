#!/usr/bin/env python3
"""Guarded sequential amalgamation for repository and gadget agent lanes.

Repository mode works over:

  agents/<agent> -> origin/main

Gadget mode works over:

  gadget-agents/<gizmo>/<gadget>/<agent> -> origin/gadgets/<gizmo>/<gadget>/main

Use gadget mode for patches landed through gadget JSON targets:

  forks.bat amalgamate-all --gadget lambdascript core --apply

Gadget mode now performs a replay-materialisation audit before any direct lane
rewind. The audit reads each selected agent's gadget replay ledger from the
gadget integration branch, checks payload presence, and verifies that each
recorded file fingerprint is present on the integration branch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import forks
import gadget_branches
import replay_plan
import replay_sync
import submission_object

DEFAULT_AGENTS = ("ed", "edd", "eddy")
WORK_ROOT = "amalgamate-all"
GADGET_SUBMISSION_FORMAT = "LS_FORK_GADGET_DIRECT_SUBMISSION_V1"


def run_submission(root: Path, argv: list[str]) -> None:
    code = submission_object.main(argv)
    if code != 0:
        raise RuntimeError(f"submission command failed: {' '.join(argv)}")


def run_replay_sync(argv: list[str]) -> None:
    code = replay_sync.main(argv)
    if code != 0:
        raise RuntimeError(f"replay-sync failed: {' '.join(argv)}")


def short(value: str | None) -> str:
    if not value:
        return "<missing>"
    return value[:8]


def remote_ref(branch: str) -> str:
    return branch if branch.startswith("origin/") else f"origin/{branch}"


def full_remote_ref(branch: str) -> str:
    return branch if branch.startswith("refs/heads/") else f"refs/heads/{branch}"


def ref_for_branch(root: Path, branch: str) -> str | None:
    if forks.ref_exists(root, branch):
        return branch
    r = remote_ref(branch)
    if forks.ref_exists(root, r):
        return r
    return None


def commit_of(root: Path, ref: str) -> str:
    return forks.commit(root, ref)


def worktree_path(root: Path, token: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "._-" else "-" for c in token)
    return root / forks.FORKS_DIR / WORK_ROOT / safe


def remove_worktree(root: Path, work: Path) -> None:
    if work.exists():
        forks.git(["worktree", "remove", "--force", str(work)], root, check=False)
    if work.exists():
        shutil.rmtree(work)
    forks.git(["worktree", "prune"], root, check=False)


def run_shell(command: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=str(cwd), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: " + command)
    return proc


def read_text_at_ref(root: Path, ref: str, path: str) -> str | None:
    proc = forks.git(["show", f"{ref}:{path}"], root, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout


# -------------------------
# Repository-agent mode
# -------------------------

def repo_best_ref_or_none(root: Path, agent: str) -> str | None:
    branch = forks.agent_branch(agent)
    return ref_for_branch(root, branch)


def replay_row_for_ref(root: Path, ref: str) -> dict[str, Any] | None:
    plan = replay_plan.build_plan(root, [ref], include_empty=True)
    rows = [row for row in plan.get("refs", []) if row.get("exists", True)]
    return rows[0] if rows else None


def apply_replay_ledger_for_ref(root: Path, ref: str, args: argparse.Namespace) -> None:
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
    run_replay_sync([ref, "--apply", "--only-replay-needed", "--verify-command", args.verify_command, "--fail-failed"])
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


def repo_capture_if_needed(root: Path, agent: str, ref: str, args: argparse.Namespace) -> None:
    source_commit = commit_of(root, ref)
    if existing_submission_matches(root, agent, source_commit):
        print(f"{agent}: replay history already adequate for {short(source_commit)}")
        return
    print(f"{agent}: creating replay history from {ref} at {short(source_commit)}")
    cmd = ["capture", agent, "--from-ref", ref]
    if args.allow_forbidden:
        cmd.append("--allow-forbidden")
    run_submission(root, cmd)


def repo_sync_captured_lane(root: Path, agent: str) -> None:
    run_submission(root, ["sync-lane", agent, "--yes"])


def repo_replay_verify_submit(root: Path, agent: str, args: argparse.Namespace) -> None:
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


def repo_plan_agent(root: Path, agent: str, ref: str, state: str, ahead: int, behind: int, args: argparse.Namespace) -> None:
    print(f"{agent}: {state} ahead={ahead} behind={behind} source={ref}")
    row = replay_row_for_ref(root, ref)
    if row and int(row.get("total_replay_count", 0)) > 0:
        print(f"  will first apply {row.get('total_replay_count')} replay-ledger entr{'y' if row.get('total_replay_count') == 1 else 'ies'} for {ref}")
        print(f"  forks.bat replay-sync {ref} --apply --only-replay-needed --verify-command {args.verify_command} --fail-failed")
    if state not in {"ahead-only", "diverged"}:
        print("  no direct lane delta; final sync will align this lane to main")
        return
    source_commit = commit_of(root, ref)
    if existing_submission_matches(root, agent, source_commit):
        print(f"  direct-diff replay history adequate: .forks/submissions/{agent}.json matches {short(source_commit)}")
    else:
        print(f"  will capture remaining direct lane delta from {ref} at {short(source_commit)}")
        print(f"  forks.bat capture {agent} --from-ref {ref}")
    print(f"  forks.bat sync-captured-lane {agent} --yes")
    print(f"  forks.bat replay {agent} --rebase-stale")
    print(f"  forks.bat verify-submission {agent} --command {args.verify_command}")
    print(f"  forks.bat submit-submission {agent} --backend {args.backend} --dry-run")
    print(f"  forks.bat submit-submission {agent} --backend {args.backend}")


def repo_apply_agent(root: Path, agent: str, args: argparse.Namespace) -> None:
    forks.fetch_main(root)
    ref = repo_best_ref_or_none(root, agent)
    if not ref:
        print(f"{agent}: missing lane; skipped")
        return
    apply_replay_ledger_for_ref(root, ref, args)
    forks.fetch_main(root)
    ref = repo_best_ref_or_none(root, agent)
    if not ref:
        print(f"{agent}: missing lane after replay; skipped")
        return
    ahead, behind = forks.ahead_behind(root, ref)
    state = forks.classify(ahead, behind)
    print(f"{agent}: post-ledger {state} ahead={ahead} behind={behind} source={ref}")
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no direct lane delta after ledger replay")
        return
    repo_capture_if_needed(root, agent, ref, args)
    repo_sync_captured_lane(root, agent)
    forks.fetch_main(root)
    repo_replay_verify_submit(root, agent, args)
    forks.fetch_main(root)


def repo_force_sync_lane_to_main(root: Path, agent: str) -> None:
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


def repo_assert_no_outstanding_replay(root: Path, agents: list[str]) -> None:
    refs = [forks.agent_branch(agent) for agent in agents]
    plan = replay_plan.build_plan(root, refs, include_empty=True)
    bad = []
    for row in plan["refs"]:
        state = row.get("state_against_main")
        classification = row.get("classification")
        if state != "even" or classification not in {"no-ledger", "no-replay-needed", "main-has-unseen-ledger-entries"}:
            bad.append(row)
    if bad:
        raise RuntimeError("outstanding repository agent lane replay remains after amalgamation")
    print("ok no outstanding repository agent lane replay remains")


def repo_run(args: argparse.Namespace, root: Path, agents: list[str]) -> int:
    forks.fetch_main(root)
    if not args.apply:
        print("amalgamate-all repository plan only; pass --apply to mutate")
        for agent in agents:
            ref = repo_best_ref_or_none(root, agent)
            if not ref:
                print(f"{agent}: missing lane; skipped")
                continue
            ahead, behind = forks.ahead_behind(root, ref)
            repo_plan_agent(root, agent, ref, forks.classify(ahead, behind), ahead, behind, args)
        print("final apply will sync target repository agent lanes to final main and assert no outstanding replay remains")
        return 0
    for agent in agents:
        repo_apply_agent(root, agent, args)
    if not args.skip_final_sync:
        print("final repository lane sync to amalgamated main")
        for agent in agents:
            repo_force_sync_lane_to_main(root, agent)
        forks.fetch_main(root)
    if not args.skip_final_assert:
        repo_assert_no_outstanding_replay(root, agents)
    print("amalgamate-all complete")
    return 0


# -------------------------
# Gadget-agent mode
# -------------------------

def gadget_base_ref(gizmo: str, gadget: str) -> str:
    return gadget_branches.target_ref(gizmo, gadget)


def gadget_lane_branch(agent: str, gizmo: str, gadget: str) -> str:
    return gadget_branches.gadget_agent_branch(agent, gizmo, gadget)


def gadget_integration_branch(gizmo: str, gadget: str) -> str:
    return gadget_branches.integration_branch(gizmo, gadget)


def gadget_ledger_path(gizmo: str, gadget: str, agent: str) -> str:
    return f"forks/replay-ledger/gadgets/{gizmo}/{gadget}/{forks.normalize_agent(agent)}.json"


def replay_entry_sort_key(agent: str, entry: dict[str, Any], fallback_order: int) -> tuple[str, str, int, int]:
    """Return a cross-agent ordering key for replay-ledger entries.

    Ledgers are per-agent, but the materialised integration branch is shared.
    The final file content should be compared against the latest replay entry
    touching that path across all selected agents. Agent iteration order is not
    meaningful, so use replay timestamps first and sequence only as a stable
    intra-agent tie-breaker.
    """
    created = entry.get("created_at")
    if not isinstance(created, str):
        created = ""
    try:
        sequence = int(entry.get("sequence", 0))
    except Exception:
        sequence = 0
    return (created, agent, sequence, fallback_order)


def should_replace_latest(current: dict[str, Any] | None, candidate: dict[str, Any]) -> bool:
    if current is None:
        return True
    return tuple(candidate.get("sort_key", ("", "", 0, 0))) > tuple(current.get("sort_key", ("", "", 0, 0)))


def is_advisory_agent_doc_path(path: str) -> bool:
    """Return true for per-agent notes that should warn rather than block sync.

    Agent notes are useful coordination artefacts, but they can be superseded by
    later lane discussion or manual note correction. A mismatch here should be
    visible, because replay evidence is imperfect, but it should not block
    propagation of verified compiler/tooling state. Core docs, forks docs, code,
    tests, examples, scripts, ledgers, and accelerator state remain strict.
    """
    normal = path.replace("\\", "/")
    return normal.startswith("docs/agents/")


def audit_gadget_replay_materialisation(
    root: Path,
    gizmo: str,
    gadget: str,
    agents: list[str],
    *,
    require_ledgers: bool,
    strict_agent_docs: bool,
) -> None:
    """Audit replay materialisation without treating superseded history as failure.

    Replay ledgers are historical. A file may be updated by later replay entries,
    possibly by another agent. Older hashes therefore should not be compared with
    the final branch content. The audit checks two invariants:

    1. Every replay entry still has its payload object.
    2. For each replay-touched file path, final branch content matches the latest
       non-delete replay fingerprint touching that path across the selected
       agents' ledgers, ordered by replay entry timestamp plus sequence.

    Per-agent planning notes under docs/agents/ are advisory. Hash drift in those
    files is reported as a warning by default. Pass --strict-agent-docs to make
    such drift fatal.
    """
    base_ref = gadget_base_ref(gizmo, gadget)
    errors: list[str] = []
    warnings: list[str] = []
    latest_by_path: dict[str, dict[str, Any]] = {}
    fallback_order = 0

    print(f"gadget replay materialisation audit for {gizmo}/{gadget} at {forks.short_commit(root, base_ref)}")
    for agent in agents:
        ledger_path = gadget_ledger_path(gizmo, gadget, agent)
        raw = read_text_at_ref(root, base_ref, ledger_path)
        if raw is None:
            msg = f"{agent}: no gadget replay ledger at {ledger_path}"
            print(msg)
            if require_ledgers:
                errors.append(msg)
            continue
        try:
            ledger = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{agent}: invalid ledger JSON: {exc}")
            continue

        entries = list(ledger.get("entries", []))
        print(f"{agent}: ledger entries={len(entries)} path={ledger_path}")
        for entry in entries:
            fallback_order += 1
            seq = entry.get("sequence")
            title = entry.get("title", "")
            sort_key = replay_entry_sort_key(agent, entry, fallback_order)
            payload_path = entry.get("payload_path")
            if not isinstance(payload_path, str) or not payload_path:
                errors.append(f"{agent}#{seq}: missing payload_path")
            elif read_text_at_ref(root, base_ref, payload_path) is None:
                errors.append(f"{agent}#{seq}: payload missing at {payload_path}")

            file_count = 0
            for fp in entry.get("file_fingerprints", []):
                file_count += 1
                path = fp.get("path")
                if not isinstance(path, str) or not path:
                    errors.append(f"{agent}#{seq}: malformed file fingerprint path")
                    continue
                candidate = {
                    "sort_key": sort_key,
                    "agent": agent,
                    "sequence": seq,
                    "title": title,
                    "created_at": entry.get("created_at", ""),
                    "path": path,
                    "op": fp.get("op", "upsert"),
                    "content_sha256": fp.get("content_sha256"),
                    "content_length": fp.get("content_length"),
                }
                if should_replace_latest(latest_by_path.get(path), candidate):
                    latest_by_path[path] = candidate
            print(f"  #{seq}: files={file_count} title={title}")

    if errors:
        raise RuntimeError("gadget replay materialisation audit failed\n" + "\n".join(errors))

    print(f"checking final materialisation for {len(latest_by_path)} replay-touched path(s)")
    for path, info in sorted(latest_by_path.items()):
        op = info.get("op", "upsert")
        content = read_text_at_ref(root, base_ref, path)
        label = f"{info.get('agent')}#{info.get('sequence')}: {path}"
        advisory = is_advisory_agent_doc_path(path)
        if op in {"delete", "remove"}:
            if content is not None:
                msg = f"{label}: expected latest operation to delete file, but it exists"
                if advisory and not strict_agent_docs:
                    warnings.append(msg)
                    print(f"  warning {msg}")
                else:
                    errors.append(msg)
            else:
                print(f"  ok deleted {label}")
            continue
        if content is None:
            msg = f"{label}: latest replay-touched file missing"
            if advisory and not strict_agent_docs:
                warnings.append(msg)
                print(f"  warning {msg}")
            else:
                errors.append(msg)
            continue
        expected = info.get("content_sha256")
        if expected:
            actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if actual != expected:
                msg = f"{label}: final file hash mismatch expected={expected} actual={actual}"
                if advisory and not strict_agent_docs:
                    warnings.append(msg)
                    print(f"  warning {msg}")
                    continue
                errors.append(msg)
                continue
        created = info.get("created_at", "")
        print(f"  ok {label} created_at={created}")

    if warnings:
        print("gadget replay materialisation audit warnings")
        for warning in warnings:
            print(f"  {warning}")

    if errors:
        raise RuntimeError("gadget replay materialisation audit failed\n" + "\n".join(errors))
    print("ok gadget replay materialisation audit passed")

def gadget_submission_dir(root: Path) -> Path:
    path = root / forks.FORKS_DIR / "gadget-submissions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def gadget_submission_path(root: Path, gizmo: str, gadget: str, agent: str) -> Path:
    safe = f"{gizmo}_{gadget}_{forks.normalize_agent(agent)}".replace("/", "_")
    return gadget_submission_dir(root) / f"{safe}.json"


def write_gadget_submission(root: Path, gizmo: str, gadget: str, agent: str, data: dict[str, Any]) -> None:
    path = gadget_submission_path(root, gizmo, gadget, agent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    patch_path = path.with_suffix(".patch")
    patch_path.write_text(data["patch"], encoding="utf-8")
    print(f"wrote {path}")


def make_gadget_submission(root: Path, gizmo: str, gadget: str, agent: str, lane_ref: str, base_ref: str) -> dict[str, Any]:
    base = forks.merge_base(root, base_ref, lane_ref)
    if not base:
        raise RuntimeError(f"cannot find merge-base between {base_ref} and {lane_ref}")
    patch = forks.git(["diff", "--binary", base, lane_ref], root).stdout
    files = forks.changed_files(root, lane_ref, base)
    if not patch.strip() or not files:
        raise RuntimeError(f"source ref has no captured gadget work: {lane_ref}")
    return {
        "format": GADGET_SUBMISSION_FORMAT,
        "agent": forks.normalize_agent(agent),
        "gizmo": gizmo,
        "gadget": gadget,
        "lane_branch": gadget_lane_branch(agent, gizmo, gadget),
        "lane_ref": lane_ref,
        "base_ref": base_ref,
        "base_commit": forks.commit(root, base_ref),
        "merge_base": base,
        "source_commit": forks.commit(root, lane_ref),
        "patch_sha256": forks.sha256_text(patch),
        "changed_files": files,
        "patch": patch,
        "created_at": forks.now_iso(),
    }


def destructive_sync_gadget_lane_to_base(root: Path, branch: str, base_ref: str, expected_oid: str) -> None:
    remote = remote_ref(branch)
    full = full_remote_ref(branch)
    forks.git(["fetch", "--prune", "origin"], root)
    current = forks.commit(root, remote) if forks.ref_exists(root, remote) else None
    if current != expected_oid:
        raise RuntimeError(f"refusing to sync {branch}; remote changed since capture expected={short(expected_oid)} current={short(current)}")
    if forks.current_branch(root) == branch:
        forks.git(["reset", "--hard", base_ref], root)
    elif forks.ref_exists(root, branch):
        forks.git(["branch", "-f", branch, base_ref], root)
    else:
        forks.git(["branch", branch, base_ref], root)
    forks.git(["push", f"--force-with-lease={full}:{expected_oid}", "origin", f"{base_ref}:{full}"], root)
    print(f"{branch}: rewound to {forks.short_commit(root, base_ref)} after capture")


def apply_gadget_patch_to_integration(root: Path, gizmo: str, gadget: str, agent: str, submission: dict[str, Any], args: argparse.Namespace) -> None:
    base_ref = gadget_base_ref(gizmo, gadget)
    integration = gadget_integration_branch(gizmo, gadget)
    expected = forks.commit(root, base_ref)
    work = worktree_path(root, f"gadget-{gizmo}-{gadget}-{agent}")
    remove_worktree(root, work)
    forks.git(["worktree", "add", "--detach", str(work), base_ref], root)
    try:
        proc = subprocess.run(["git", "apply", "--binary", "-"], cwd=str(work), input=submission["patch"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
        if proc.returncode != 0:
            raise RuntimeError("git apply failed for captured gadget lane patch")
        forks.git(["add", "-A"], work)
        if not forks.git_text(["diff", "--cached", "--name-status"], work):
            print(f"{agent}: captured gadget patch produced no changes")
            return
        msg = f"Amalgamate {agent} gadget lane for {gizmo}/{gadget}"
        forks.git(["-c", "user.name=Forks", "-c", "user.email=forks@local", "commit", "-m", msg], work)
        if args.verify_command:
            proc = run_shell(args.verify_command, work, check=False)
            if proc.returncode != 0:
                raise RuntimeError("verification failed for captured gadget lane patch")
        full = full_remote_ref(integration)
        forks.git(["fetch", "--prune", "origin"], root)
        current = forks.commit(root, base_ref)
        if current != expected:
            raise RuntimeError(f"gadget integration changed before push expected={short(expected)} current={short(current)}")
        forks.git(["push", f"--force-with-lease={full}:{expected}", "origin", f"HEAD:{full}"], work)
        print(f"{integration}: advanced with {agent} direct lane patch")
    finally:
        remove_worktree(root, work)


def gadget_plan_agent(root: Path, gizmo: str, gadget: str, agent: str, args: argparse.Namespace) -> None:
    base_ref = gadget_base_ref(gizmo, gadget)
    branch = gadget_lane_branch(agent, gizmo, gadget)
    ref = ref_for_branch(root, branch)
    if not ref:
        print(f"{agent}: missing gadget lane {branch}; final sync will create it")
        return
    ahead, behind = forks.ahead_behind(root, ref, base_ref)
    state = forks.classify(ahead, behind)
    print(f"{agent}: gadget {state} ahead={ahead} behind={behind} source={ref} base={base_ref}")
    if state in {"ahead-only", "diverged"}:
        print(f"  will capture direct gadget lane delta from {ref}")
        print(f"  will rewind {branch} to {base_ref} after capture")
        print(f"  will apply captured delta to {gadget_integration_branch(gizmo, gadget)} and verify with {args.verify_command}")
    else:
        print("  no direct gadget lane delta; final sync will align this lane to gadget integration")


def gadget_apply_agent(root: Path, gizmo: str, gadget: str, agent: str, args: argparse.Namespace) -> None:
    forks.git(["fetch", "--prune", "origin"], root)
    base_ref = gadget_base_ref(gizmo, gadget)
    forks.ref_exists(root, base_ref) or (_ for _ in ()).throw(RuntimeError(f"missing gadget integration ref: {base_ref}"))
    branch = gadget_lane_branch(agent, gizmo, gadget)
    ref = ref_for_branch(root, branch)
    if not ref:
        print(f"{agent}: missing gadget lane {branch}; final sync will create it")
        return
    ahead, behind = forks.ahead_behind(root, ref, base_ref)
    state = forks.classify(ahead, behind)
    print(f"{agent}: gadget {state} ahead={ahead} behind={behind} source={ref} base={base_ref}")
    if state not in {"ahead-only", "diverged"}:
        print(f"{agent}: no direct gadget lane delta")
        return
    submission = make_gadget_submission(root, gizmo, gadget, agent, ref, base_ref)
    write_gadget_submission(root, gizmo, gadget, agent, submission)
    destructive_sync_gadget_lane_to_base(root, branch, base_ref, submission["source_commit"])
    forks.git(["fetch", "--prune", "origin"], root)
    apply_gadget_patch_to_integration(root, gizmo, gadget, agent, submission, args)
    forks.git(["fetch", "--prune", "origin"], root)


def gadget_final_sync(root: Path, gizmo: str, gadget: str, agents: list[str]) -> None:
    base_ref = gadget_base_ref(gizmo, gadget)
    forks.git(["fetch", "--prune", "origin"], root)
    print(f"final gadget lane sync to {base_ref}")
    for agent in agents:
        gadget_branches.sync_agent_lane(root, agent, gizmo, gadget)
    forks.git(["fetch", "--prune", "origin"], root)


def gadget_assert_clean(root: Path, gizmo: str, gadget: str, agents: list[str]) -> None:
    base_ref = gadget_base_ref(gizmo, gadget)
    bad = []
    for agent in agents:
        branch = gadget_lane_branch(agent, gizmo, gadget)
        ref = ref_for_branch(root, branch)
        if not ref:
            bad.append(f"{branch}: missing")
            continue
        ahead, behind = forks.ahead_behind(root, ref, base_ref)
        state = forks.classify(ahead, behind)
        if state != "even":
            bad.append(f"{branch}: {state} ahead={ahead} behind={behind}")
    if bad:
        raise RuntimeError("outstanding gadget agent lane work remains after amalgamation\n" + "\n".join(bad))
    print("ok no outstanding gadget agent lane work remains")


def gadget_run(args: argparse.Namespace, root: Path, agents: list[str]) -> int:
    gizmo, gadget = args.gadget
    forks.git(["fetch", "--prune", "origin"], root)
    if not args.skip_replay_audit:
        audit_gadget_replay_materialisation(root, gizmo, gadget, agents, require_ledgers=args.require_ledgers, strict_agent_docs=getattr(args, "strict_agent_docs", False))
    if not args.apply:
        print(f"amalgamate-all gadget plan only for {gizmo}/{gadget}; pass --apply to mutate")
        for agent in agents:
            gadget_plan_agent(root, gizmo, gadget, agent, args)
        print("final apply will sync target gadget-agent lanes to the gadget integration branch and assert they are clean")
        return 0
    for agent in agents:
        gadget_apply_agent(root, gizmo, gadget, agent, args)
    if not args.skip_final_sync:
        gadget_final_sync(root, gizmo, gadget, agents)
    if not args.skip_final_assert:
        gadget_assert_clean(root, gizmo, gadget, agents)
    if not args.skip_replay_audit:
        audit_gadget_replay_materialisation(root, gizmo, gadget, agents, require_ledgers=args.require_ledgers, strict_agent_docs=getattr(args, "strict_agent_docs", False))
    print("amalgamate-all complete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forks amalgamate-all",
        description="Amalgamate repository agent lanes or gadget-agent lanes sequentially.",
    )
    parser.add_argument("--agents", nargs="+", default=list(DEFAULT_AGENTS), help="agent lanes to inspect; default: ed edd eddy")
    parser.add_argument("--gadget", nargs=2, metavar=("GIZMO", "GADGET"), help="operate on gadget-agent lanes for the given gizmo/gadget")
    parser.add_argument("--verify-command", default="verify.bat", help="verification command run in replayed candidates")
    parser.add_argument("--backend", choices=("ref", "contents"), default="ref", help="repository submission backend")
    parser.add_argument("--allow-forbidden", action="store_true", help="allow guarded paths during repository capture/replay/verify")
    parser.add_argument("--apply", action="store_true", help="mutate: capture/replay/verify/submit/final-sync")
    parser.add_argument("--skip-final-sync", action="store_true", help="advanced: do not sync target agent lanes to final base")
    parser.add_argument("--skip-final-assert", action="store_true", help="advanced: do not assert that target lanes are clean after amalgamation")
    parser.add_argument("--skip-replay-audit", action="store_true", help="advanced: skip gadget replay materialisation audit")
    parser.add_argument("--require-ledgers", action="store_true", help="fail gadget replay audit when a selected agent has no gadget ledger")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    root = forks.repo_root()
    forks.ensure_dirs(root)
    agents = [forks.normalize_agent(a) for a in args.agents]
    try:
        if args.gadget:
            return gadget_run(args, root, agents)
        return repo_run(args, root, agents)
    except Exception as exc:
        print(f"forks amalgamate-all: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
