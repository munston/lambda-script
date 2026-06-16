#!/usr/bin/env python3
r"""Land a targeted JSON patch using a hardcoded agent lane.

The public button shape is intentionally one argument:

    guy-land-json.bat path\to\patch.json

The patch itself carries its target and transaction policy:

    {
      "format": "LS_FORK_JSON_PATCH_V1",
      "agent": "guy",
      "target": {
        "kind": "gadget",
        "gizmo": "metrics",
        "gadget": "image-metrics",
        "profile": "quick",
        "promote": true,
        "sync": false,
        "history": true,
        "repository_sync": true,
        "refresh": true
      },
      "title": "...",
      "files": [...]
    }

Gadget lane sync is intentionally opt-in. Normal parallel-agent operation should
land replay-backed JSON patches first, then use audited amalgamation to align
lanes.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import forks
import gadget_branches
import gadget_land_json
import gadget_promote
import gadget_verify_profiles
import import_json_patch

VALID_AGENTS = {"ed", "edd", "eddy", "guy"}


class Target:
    def __init__(
        self,
        gizmo: str,
        gadget: str,
        profile: str | None,
        full: bool,
        promote: bool,
        sync: bool,
        history: bool,
        promote_profile: str | None,
        repository_sync: bool,
        refresh: bool,
    ) -> None:
        self.gizmo = gizmo
        self.gadget = gadget
        self.profile = profile
        self.full = full
        self.promote = promote
        self.sync = sync
        self.history = history
        self.promote_profile = promote_profile
        self.repository_sync = repository_sync
        self.refresh = refresh


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

    promote_profile = target.get("promote_profile")
    if promote_profile is not None and (not isinstance(promote_profile, str) or not promote_profile):
        raise RuntimeError("target.promote_profile must be a non-empty string when present")

    return Target(
        gizmo=gizmo,
        gadget=gadget,
        profile=profile,
        full=_bool(target, "full", False),
        promote=_bool(target, "promote", False),
        sync=_bool(target, "sync", False),
        history=_bool(target, "history", True),
        promote_profile=promote_profile,
        repository_sync=_bool(target, "repository_sync", True),
        refresh=_bool(target, "refresh", True),
    )


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


def force_align_gadget(root: Path, gizmo: str, gadget: str, source_ref: str) -> None:
    print(f"normalizing {gizmo}/{gadget} lanes to {source_ref}")
    force_align_branch(root, gadget_branches.integration_branch(gizmo, gadget), source_ref)
    for agent in gadget_branches.AGENTS:
        force_align_branch(root, gadget_branches.gadget_agent_branch(agent, gizmo, gadget), source_ref)


def run_status(root: Path, gizmo: str, gadget: str) -> None:
    subprocess.run(["cmd", "/c", "forks.bat", "status", "--fetch"], cwd=str(root), text=True, check=False)
    subprocess.run(["cmd", "/c", "forks.bat", "gadget-status", gizmo, gadget], cwd=str(root), text=True, check=False)


def run_shell(command: str, cwd: Path) -> None:
    print(f"> {command}")
    proc = subprocess.run(command, cwd=str(cwd), shell=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {command}")


def verification_profile(target: Target) -> str:
    return target.promote_profile or target.profile or ("full" if target.full else "quick")


def verify_rebased_gadget(root: Path, work: Path, target: Target) -> None:
    profile = verification_profile(target)
    commands = gadget_verify_profiles.profile_commands(root, target.gizmo, target.gadget, profile)
    if commands is None:
        raise RuntimeError(f"missing verification profile {profile} for {target.gizmo}/{target.gadget}")
    print(f"verification profile after rebase: {profile}")
    for command in commands:
        run_shell(command, work)


def rebase_gadget_onto_main(root: Path, target: Target, *, require_unique: bool, align_lanes: bool) -> None:
    target_ref = gadget_branches.target_ref(target.gizmo, target.gadget)
    fetch(root)
    if not forks.ref_exists(root, target_ref):
        raise RuntimeError(f"missing gadget target ref: {target_ref}")

    ahead, behind = forks.ahead_behind(root, target_ref, forks.MAIN_REF)
    state = forks.classify(ahead, behind)
    print(f"gadget rebase preflight: {target_ref} state={state} ahead={ahead} behind={behind}")

    if state == "ahead-only":
        return
    if state == "even":
        if require_unique:
            raise RuntimeError(f"{target_ref} has no unique gadget work to promote")
        return
    if state != "diverged":
        raise RuntimeError(f"{target_ref} is not rebaseable: state={state} ahead={ahead} behind={behind}")

    print(f"rebasing {target.gizmo}/{target.gadget} onto {forks.MAIN_REF}")
    with TemporaryDirectory(prefix=f"gadget-rebase-{target.gizmo}-{target.gadget}-") as raw:
        work = Path(raw)
        forks.git(["worktree", "add", "--detach", str(work), target_ref], root)
        try:
            forks.git(["rebase", "-X", "theirs", forks.MAIN_REF], work)
            verify_rebased_gadget(root, work, target)
            forks.git(["push", "--force-with-lease", "origin", f"HEAD:refs/heads/{gadget_branches.integration_branch(target.gizmo, target.gadget)}"], work)
        finally:
            forks.git(["worktree", "remove", "--force", str(work)], root, check=False)
            if work.exists():
                shutil.rmtree(work, ignore_errors=True)
            forks.git(["worktree", "prune"], root, check=False)

    fetch(root)
    if align_lanes:
        force_align_gadget(root, target.gizmo, target.gadget, target_ref)
    else:
        print("skipped gadget lane sync after pre-land rebase")


def refresh_gadget_before_land(root: Path, target: Target) -> None:
    target_ref = gadget_branches.target_ref(target.gizmo, target.gadget)
    fetch(root)
    if not forks.ref_exists(root, target_ref):
        raise RuntimeError(f"missing gadget target ref: {target_ref}")

    ahead, behind = forks.ahead_behind(root, target_ref, forks.MAIN_REF)
    state = forks.classify(ahead, behind)
    print(f"pre-land refresh: {target_ref} state={state} ahead={ahead} behind={behind}")

    if state == "even" or state == "ahead-only":
        return
    if state == "behind-only":
        print(f"refreshing {target.gizmo}/{target.gadget} integration branch to {forks.MAIN_REF}")
        force_align_branch(root, gadget_branches.integration_branch(target.gizmo, target.gadget), forks.MAIN_REF)
        return
    if state == "diverged":
        rebase_gadget_onto_main(root, target, require_unique=False, align_lanes=False)
        return
    raise RuntimeError(f"{target_ref} cannot be refreshed: state={state} ahead={ahead} behind={behind}")


def cmd_land(args: argparse.Namespace) -> int:
    patch_path = Path(args.file)
    if not patch_path.exists():
        raise RuntimeError(f"missing JSON patch file: {patch_path}")

    payload = import_json_patch.load_payload(str(patch_path))
    validate_agent(args.agent, payload, args.strict_agent)
    target = resolve_target(payload)

    print(f"agent={args.agent}")
    print(f"target={target.gizmo}/{target.gadget}")
    print(f"profile={target.profile or ('full' if target.full else 'quick')}")
    print(f"promote={target.promote} sync={target.sync} history={target.history} repository_sync={target.repository_sync} refresh={target.refresh}")

    root = forks.repo_root()
    if target.refresh:
        refresh_gadget_before_land(root, target)

    land_args = SimpleNamespace(
        require_file=True,
        full=target.full,
        profile=target.profile,
        gizmo=target.gizmo,
        gadget=target.gadget,
        agent=args.agent,
        file=str(patch_path),
        align_lanes=target.sync,
    )
    rc = gadget_land_json.cmd_land(land_args)
    if rc != 0:
        return rc

    if target.promote:
        rebase_gadget_onto_main(root, target, require_unique=True, align_lanes=True)
        promote_args = SimpleNamespace(
            gizmo=target.gizmo,
            gadget=target.gadget,
            dry_run=False,
            profile=target.promote_profile or target.profile,
            full=target.full and target.promote_profile is None,
            no_verify=False,
            no_history=not target.history,
            no_repository_agent_sync=not target.repository_sync,
        )
        rc = gadget_promote.cmd_promote(promote_args)
        if rc != 0:
            return rc
        if target.sync:
            force_align_gadget(root, target.gizmo, target.gadget, forks.MAIN_REF)
            run_status(root, target.gizmo, target.gadget)

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
