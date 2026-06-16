#!/usr/bin/env python3
"""Accelerator templates for staged parallel forks workflows.

An accelerator is a tracked planning state for multi-agent development. It is
non-destructive: it never lands patches, rewinds lanes, promotes branches, or
syncs agent lanes. It records the intended sequence around those operations so
operators can keep agent responsibilities distinct while normal forks/gadget
commands perform the actual work.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import forks

FORMAT = "LS_FORK_ACCELERATOR_V1"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DEFAULT_AGENTS = ("ed", "edd", "eddy")


def clean_name(kind: str, value: str) -> str:
    name = value.strip()
    if not NAME_RE.match(name):
        raise RuntimeError(f"invalid {kind} name: {value!r}")
    return name


def root_dir(root: Path, gizmo: str, gadget: str) -> Path:
    return root / "forks" / "accelerators" / clean_name("gizmo", gizmo) / clean_name("gadget", gadget)


def state_path(root: Path, gizmo: str, gadget: str, name: str) -> Path:
    return root_dir(root, gizmo, gadget) / f"{clean_name('accelerator', name)}.json"


def now() -> str:
    return forks.now_iso()


def load_state(root: Path, gizmo: str, gadget: str, name: str) -> dict[str, Any]:
    path = state_path(root, gizmo, gadget, name)
    if not path.exists():
        raise RuntimeError(f"missing accelerator state: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != FORMAT:
        raise RuntimeError(f"{path} is not an {FORMAT} file")
    return data


def save_state(root: Path, state: dict[str, Any]) -> Path:
    path = state_path(root, state["gizmo"], state["gadget"], state["name"])
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_text_arg(value: str | None, file_value: str | None) -> str:
    if value is not None:
        return value
    if file_value is not None:
        return Path(file_value).read_text(encoding="utf-8").strip()
    return ""


def parse_paths(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for item in raw.split(","):
        path = item.strip().replace("\\", "/")
        if path:
            out.append(path)
    return sorted(dict.fromkeys(out))


def agent_template() -> dict[str, Any]:
    return {
        "responsibility": "",
        "owned_paths": [],
        "lookahead": "",
        "plan": "",
        "patch_goal": "",
        "attempts": [],
        "accepted": None,
        "notes": "",
    }


def make_slot(index: int, agents: list[str]) -> dict[str, Any]:
    return {
        "index": index,
        "objective": "",
        "status": "open",
        "agents": {agent: agent_template() for agent in agents},
    }


def make_state(gizmo: str, gadget: str, name: str, agents: list[str], slots: int, objective: str) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "name": clean_name("accelerator", name),
        "gizmo": clean_name("gizmo", gizmo),
        "gadget": clean_name("gadget", gadget),
        "created_at": now(),
        "updated_at": now(),
        "cursor": {"slot": 1},
        "agents": agents,
        "global_objective": objective,
        "rules": [
            "Each agent keeps a distinct responsibility track.",
            "For every turn, each agent maintains current implementation, next-slot complete plan, and plus-two lookahead.",
            "Compile or verification failures enter an attempt loop for the same slot.",
            "A slot advances only after every active agent has an accepted patch or is explicitly marked skipped.",
            "JSON landing records replay history; lane propagation belongs to audited amalgamation.",
        ],
        "slots": [make_slot(i, agents) for i in range(1, slots + 1)],
    }


def slot_by_index(state: dict[str, Any], index: int) -> dict[str, Any]:
    for slot in state["slots"]:
        if int(slot["index"]) == index:
            return slot
    raise RuntimeError(f"slot {index} does not exist")


def agent_cell(state: dict[str, Any], agent: str, slot_index: int) -> dict[str, Any]:
    slot = slot_by_index(state, slot_index)
    agents = slot.setdefault("agents", {})
    agent = forks.normalize_agent(agent)
    if agent not in agents:
        agents[agent] = agent_template()
        if agent not in state["agents"]:
            state["agents"].append(agent)
    return agents[agent]


def current_slot(state: dict[str, Any]) -> int:
    return int(state.get("cursor", {}).get("slot", 1))


def accepted_or_skipped(cell: dict[str, Any]) -> bool:
    accepted = cell.get("accepted")
    if isinstance(accepted, dict) and accepted.get("status") in {"accepted", "skipped"}:
        return True
    return False


def latest_attempt_status(cell: dict[str, Any]) -> str:
    attempts = cell.get("attempts") or []
    if not attempts:
        return "none"
    return str(attempts[-1].get("status", "unknown"))


def detect_path_collisions(slot: dict[str, Any]) -> list[tuple[str, list[str]]]:
    owners: dict[str, list[str]] = {}
    for agent, cell in slot.get("agents", {}).items():
        for path in cell.get("owned_paths", []) or []:
            owners.setdefault(path, []).append(agent)
    return sorted((path, agents) for path, agents in owners.items() if len(agents) > 1)


def cmd_init(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    agents = [forks.normalize_agent(a) for a in args.agents]
    path = state_path(root, args.gizmo, args.gadget, args.name)
    if path.exists() and not args.force:
        raise RuntimeError(f"accelerator already exists: {path}")
    objective = read_text_arg(args.objective, args.objective_file)
    state = make_state(args.gizmo, args.gadget, args.name, agents, args.slots, objective)
    save_state(root, state)
    print(f"wrote {path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    state = load_state(root, args.gizmo, args.gadget, args.name)
    cur = current_slot(state)
    print(f"accelerator {state['gizmo']}/{state['gadget']}/{state['name']}")
    print(f"cursor slot={cur}")
    if state.get("global_objective"):
        print(f"objective: {state['global_objective']}")
    for slot in state["slots"]:
        index = int(slot["index"])
        if args.all or cur <= index <= cur + 2:
            label = "current" if index == cur else ("next" if index == cur + 1 else ("lookahead" if index == cur + 2 else ""))
            suffix = f" ({label})" if label else ""
            print(f"slot {index}{suffix}: {slot.get('objective', '')}")
            collisions = detect_path_collisions(slot)
            if collisions:
                for path, owners in collisions:
                    print(f"  collision: {path} -> {', '.join(owners)}")
            for agent in state["agents"]:
                cell = slot.get("agents", {}).get(agent, agent_template())
                accepted = cell.get("accepted") or {}
                marker = accepted.get("status", "open") if isinstance(accepted, dict) else "open"
                attempts = len(cell.get("attempts") or [])
                print(f"  {agent}: {marker}; attempts={attempts}; latest={latest_attempt_status(cell)}; responsibility={cell.get('responsibility', '')}")
    return 0


def cmd_set_slot(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    state = load_state(root, args.gizmo, args.gadget, args.name)
    slot = slot_by_index(state, args.slot)
    objective = read_text_arg(args.objective, args.objective_file)
    if objective:
        slot["objective"] = objective
    if args.status:
        slot["status"] = args.status
    path = save_state(root, state)
    print(f"updated {path}")
    return 0


def cmd_set_agent(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    state = load_state(root, args.gizmo, args.gadget, args.name)
    cell = agent_cell(state, args.agent, args.slot)
    responsibility = read_text_arg(args.responsibility, args.responsibility_file)
    lookahead = read_text_arg(args.lookahead, args.lookahead_file)
    plan = read_text_arg(args.plan, args.plan_file)
    patch_goal = read_text_arg(args.patch_goal, args.patch_goal_file)
    notes = read_text_arg(args.notes, args.notes_file)
    if responsibility:
        cell["responsibility"] = responsibility
    if lookahead:
        cell["lookahead"] = lookahead
    if plan:
        cell["plan"] = plan
    if patch_goal:
        cell["patch_goal"] = patch_goal
    if notes:
        cell["notes"] = notes
    paths = parse_paths(args.paths)
    if paths:
        cell["owned_paths"] = paths
    path = save_state(root, state)
    print(f"updated {path}")
    return 0


def cmd_attempt(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    state = load_state(root, args.gizmo, args.gadget, args.name)
    cell = agent_cell(state, args.agent, args.slot)
    error = read_text_arg(args.error, args.error_file)
    note = read_text_arg(args.note, args.note_file)
    attempt = {
        "created_at": now(),
        "status": args.status,
        "patch": args.patch or "",
        "json_patch_sha256": args.json_patch_sha256 or "",
        "verification": args.verification or "",
        "error": error,
        "note": note,
    }
    cell.setdefault("attempts", []).append(attempt)
    path = save_state(root, state)
    print(f"recorded attempt {len(cell['attempts'])} in {path}")
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    state = load_state(root, args.gizmo, args.gadget, args.name)
    cell = agent_cell(state, args.agent, args.slot)
    status = "skipped" if args.skip else "accepted"
    cell["accepted"] = {
        "status": status,
        "created_at": now(),
        "patch": args.patch or "",
        "json_patch_sha256": args.json_patch_sha256 or "",
        "ledger_path": args.ledger_path or "",
        "sequence": args.sequence,
        "note": read_text_arg(args.note, args.note_file),
    }
    path = save_state(root, state)
    print(f"{args.agent} slot {args.slot}: {status}")
    print(f"updated {path}")
    return 0


def cmd_packet(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    state = load_state(root, args.gizmo, args.gadget, args.name)
    cur = args.slot or current_slot(state)
    agent = forks.normalize_agent(args.agent)
    print(f"ACCELERATOR PACKET {state['gizmo']}/{state['gadget']}/{state['name']} agent={agent} slot={cur}")
    print()
    for offset, label in [(0, "IMPLEMENTATION SLOT"), (1, "NEXT COMPLETE PLAN SLOT"), (2, "PLUS-TWO LOOKAHEAD SLOT")]:
        index = cur + offset
        try:
            slot = slot_by_index(state, index)
        except RuntimeError:
            print(f"{label} {index}: <missing>")
            print()
            continue
        cell = slot.get("agents", {}).get(agent, agent_template())
        print(f"{label} {index}")
        print(f"objective: {slot.get('objective', '')}")
        print(f"responsibility: {cell.get('responsibility', '')}")
        print(f"owned paths: {', '.join(cell.get('owned_paths', []) or [])}")
        if offset == 0:
            print(f"patch goal: {cell.get('patch_goal', '')}")
            print(f"plan: {cell.get('plan', '')}")
            print(f"attempt loop status: {latest_attempt_status(cell)}")
        elif offset == 1:
            print(f"plan: {cell.get('plan', '')}")
            print(f"remaining elaboration: turn this into the next implementation patch after current acceptance")
        else:
            print(f"lookahead: {cell.get('lookahead', '')}")
            print(f"remaining elaboration: preserve novelty/non-overlap while anticipating the slot after next")
        print()
    print("Workflow rule: if the current patch fails verification, stay on this slot and submit a corrected attempt before advancing.")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    root = forks.repo_root()
    state = load_state(root, args.gizmo, args.gadget, args.name)
    cur = current_slot(state)
    slot = slot_by_index(state, cur)
    missing = []
    for agent in state["agents"]:
        cell = slot.get("agents", {}).get(agent, agent_template())
        if not accepted_or_skipped(cell):
            missing.append(agent)
    if missing and not args.force:
        raise RuntimeError("cannot advance; missing accepted/skipped agents: " + ", ".join(missing))
    state.setdefault("cursor", {})["slot"] = cur + 1
    slot["status"] = "complete" if not missing else "forced"
    path = save_state(root, state)
    print(f"advanced {state['name']} from slot {cur} to {cur + 1}")
    print(f"updated {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks accelerator")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("--agents", nargs="+", default=list(DEFAULT_AGENTS))
    p.add_argument("--slots", type=int, default=7)
    p.add_argument("--objective")
    p.add_argument("--objective-file")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("set-slot")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("slot", type=int)
    p.add_argument("--objective")
    p.add_argument("--objective-file")
    p.add_argument("--status")
    p.set_defaults(func=cmd_set_slot)

    p = sub.add_parser("set-agent")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("agent")
    p.add_argument("slot", type=int)
    p.add_argument("--responsibility")
    p.add_argument("--responsibility-file")
    p.add_argument("--paths", help="comma-separated owned path prefixes/files for collision checks")
    p.add_argument("--lookahead")
    p.add_argument("--lookahead-file")
    p.add_argument("--plan")
    p.add_argument("--plan-file")
    p.add_argument("--patch-goal")
    p.add_argument("--patch-goal-file")
    p.add_argument("--notes")
    p.add_argument("--notes-file")
    p.set_defaults(func=cmd_set_agent)

    p = sub.add_parser("attempt")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("agent")
    p.add_argument("slot", type=int)
    p.add_argument("--status", choices=["draft", "failed", "passed", "rejected"], default="draft")
    p.add_argument("--patch")
    p.add_argument("--json-patch-sha256")
    p.add_argument("--verification")
    p.add_argument("--error")
    p.add_argument("--error-file")
    p.add_argument("--note")
    p.add_argument("--note-file")
    p.set_defaults(func=cmd_attempt)

    p = sub.add_parser("accept")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("agent")
    p.add_argument("slot", type=int)
    p.add_argument("--patch")
    p.add_argument("--json-patch-sha256")
    p.add_argument("--ledger-path")
    p.add_argument("--sequence", type=int)
    p.add_argument("--note")
    p.add_argument("--note-file")
    p.add_argument("--skip", action="store_true")
    p.set_defaults(func=cmd_accept)

    p = sub.add_parser("packet")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("agent")
    p.add_argument("--slot", type=int)
    p.set_defaults(func=cmd_packet)

    p = sub.add_parser("advance")
    p.add_argument("gizmo")
    p.add_argument("gadget")
    p.add_argument("name")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_advance)

    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"forks accelerator: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
