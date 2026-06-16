#!/usr/bin/env python3
r"""Land a targeted JSON patch to the hardcoded agent's own gadget lane.

The public button shape is intentionally one argument:

    edd-land-json.bat path\to\patch.json

The patch carries the gadget identity and verification profile, but the hardcoded
agent button deliberately ignores patch requests to promote, synchronize, or
align other lanes. Those operations belong to audited amalgamation.

Default contract:

    ed-land-json.bat   -> gadget-agents/<gizmo>/<gadget>/ed
    edd-land-json.bat  -> gadget-agents/<gizmo>/<gadget>/edd
    eddy-land-json.bat -> gadget-agents/<gizmo>/<gadget>/eddy
    guy-land-json.bat  -> gadget-agents/<gizmo>/<gadget>/guy

This command appends/reuses replay history inside the agent lane, verifies the
candidate, and pushes only that agent lane. It does not advance the gadget
integration branch and does not sync/amalgamate any lanes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import forks
import gadget_branches
import gadget_verify_profiles
import import_json_patch

VALID_AGENTS = {"ed", "edd", "eddy", "guy"}


class Target:
    def __init__(self, gizmo: str, gadget: str, profile: str | None, full: bool) -> None:
        self.gizmo = gizmo
        self.gadget = gadget
        self.profile = profile
        self.full = full


def _bool(target: dict, name: str, default: bool) -> bool:
    value = target.get(name, default)
    if not isinstance(value, bool):
        raise RuntimeError(f"target.{name} must be a boolean")
    return value


def resolve_target(payload: dict) -> Target:
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

    return Target(
        gizmo=gizmo,
        gadget=gadget,
        profile=profile,
        full=_bool(target, "full", False),
    )


def validate_agent(hardcoded_agent: str, payload: dict, strict_agent: bool) -> None:
    if hardcoded_agent not in VALID_AGENTS:
        raise RuntimeError(f"unknown hardcoded agent: {hardcoded_agent}")

    declared = payload.get("agent")
    if declared is None:
        return
    if not isinstance(declared, str) or not declared:
        raise RuntimeError("patch agent field must be a non-empty string when present")
    if strict_agent and forks.normalize_agent(declared) != hardcoded_agent:
        raise RuntimeError(f"patch declares agent {declared!r}, but this button is for {hardcoded_agent!r}")


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(cwd), text=True)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(args))
    return proc


def run_shell(command: str, cwd: Path) -> None:
    print(f"> {command}")
    proc = subprocess.run(command, cwd=str(cwd), shell=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {command}")


def remote_ref(branch: str) -> str:
    return branch if branch.startswith("origin/") else f"origin/{branch}"


def push_ref_for_branch(branch: str) -> str:
    if branch.startswith("origin/"):
        return branch[len("origin/"):]
    return branch


def ensure_agent_lane(root: Path, agent: str, gizmo: str, gadget: str) -> str:
    branch = gadget_branches.gadget_agent_branch(agent, gizmo, gadget)
    ref = remote_ref(branch)
    forks.git(["fetch", "--prune", "origin"], root)
    if forks.ref_exists(root, ref):
        return ref

    base = gadget_branches.target_ref(gizmo, gadget)
    if not forks.ref_exists(root, base):
        raise RuntimeError(f"missing gadget integration base for lane creation: {base}")

    print(f"{branch}: creating missing gadget-agent lane at {forks.short_commit(root, base)}")
    forks.git(["push", "origin", f"{base}:refs/heads/{branch}"], root)
    forks.git(["fetch", "--prune", "origin"], root)
    if not forks.ref_exists(root, ref):
        raise RuntimeError(f"failed to create gadget-agent lane: {ref}")
    return ref


def verification_commands(root: Path, target: Target) -> tuple[str | None, list[str] | None, bool]:
    profile = target.profile or ("full" if target.full else "quick")
    commands = gadget_verify_profiles.profile_commands(root, target.gizmo, target.gadget, profile)
    if commands is not None:
        return profile, commands, False
    if target.profile:
        raise RuntimeError(f"missing verification profile {profile} for {target.gizmo}/{target.gadget}")
    return None, None, target.full


def verify_candidate(root: Path, target: Target, work: Path) -> None:
    profile, commands, full_fallback = verification_commands(root, target)
    if commands is not None:
        print(f"verification profile: {profile}")
        for command in commands:
            run_shell(command, work)
        return
    if full_fallback:
        run(["cmd", "/c", "verify.bat"], work)
        return
    run([
        sys.executable,
        "-m",
        "py_compile",
        "scripts/forks/forks.py",
        "scripts/forks/forks_dispatch.py",
        "scripts/forks/submission_object.py",
        "scripts/forks/import_json_patch.py",
        "scripts/forks/land_json_patch.py",
        "scripts/forks/gadget_branches.py",
        "scripts/forks/gadget_land_json.py",
        "scripts/forks/gadget_verify_profiles.py",
        "scripts/forks/gadget_promote.py",
        "scripts/forks/ensure_node_toolchains.py",
        "scripts/forks/agent_land_json.py",
        "scripts/forks/main_history.py",
        "scripts/forks/replay_plan.py",
        "scripts/forks/replay_sync.py",
        "scripts/forks/accelerator.py",
        "scripts/forks/amalgamate_all.py",
    ], work)


def require_candidate_fresh(work: Path, target_ref: str) -> None:
    forks.git(["fetch", "--prune", "origin"], work)
    ancestor = forks.git(["merge-base", "--is-ancestor", target_ref, "HEAD"], work, check=False)
    if ancestor.returncode != 0:
        raise RuntimeError(f"{target_ref} is not an ancestor of imported candidate")
    ahead, behind = forks.ahead_behind(work, "HEAD", target_ref)
    if ahead <= 0 or behind != 0:
        raise RuntimeError(f"imported candidate is not fresh ahead-only against {target_ref}: ahead={ahead} behind={behind}")


def cmd_land(args: argparse.Namespace) -> int:
    patch_path = Path(args.file)
    if not patch_path.exists():
        raise RuntimeError(f"missing JSON patch file: {patch_path}")

    payload = import_json_patch.load_payload(str(patch_path))
    validate_agent(args.agent, payload, args.strict_agent)
    target = resolve_target(payload)

    root = forks.repo_root()
    forks.ensure_dirs(root)
    agent = forks.normalize_agent(args.agent)
    lane_ref = ensure_agent_lane(root, agent, target.gizmo, target.gadget)

    print(f"agent={agent}")
    print(f"target={target.gizmo}/{target.gadget}")
    print(f"lane={lane_ref}")
    print(f"profile={target.profile or ('full' if target.full else 'quick')}")
    print("scope=agent-lane-only")
    print("sync=False promote=False amalgamate=False")

    submission = import_json_patch.make_submission(root, agent, payload, lane_ref)
    import_json_patch.submission_object.write_submission(root, agent, submission)
    work = import_json_patch.import_worktree(root, agent)

    print(f"imported JSON candidate for {agent}: {work}")
    print(f"target={lane_ref}")
    print(f"files={len(submission['changed_files'])} ahead={submission['ahead']} behind={submission['behind']}")

    require_candidate_fresh(work, lane_ref)
    print("verifying imported candidate")
    verify_candidate(root, target, work)
    require_candidate_fresh(work, lane_ref)

    push_ref = push_ref_for_branch(lane_ref)
    print("dry-run lane submit")
    run(["git", "push", "--dry-run", "origin", f"HEAD:{push_ref}"], work)

    print("lane submit")
    run(["git", "push", "origin", f"HEAD:{push_ref}"], work)

    forks.git(["fetch", "--prune", "origin"], root)
    print(f"submitted to {push_ref}; skipped gadget integration, amalgamation, promotion, and lane sync")
    print("gadget status")
    status_args = argparse.Namespace(gizmo=target.gizmo, gadget=target.gadget, json=False)
    gadget_branches.cmd_status(status_args)
    return 0


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
