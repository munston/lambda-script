#!/usr/bin/env python3
"""Python dispatcher behind forks.bat.

The batch wrapper should not parse or shift long command lines. Windows batch
argument forwarding is fragile once a command has more than nine arguments or
contains quoted strings. This dispatcher receives the original argv from
`forks.bat %*` and routes subcommands using Python's argv list.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable


def run(script: str, args: list[str]) -> int:
    path = ROOT / script
    if not path.exists():
        print(f"forks dispatch: missing {script}", file=sys.stderr)
        return 1
    proc = subprocess.run([PY, str(path), *args], cwd=str(ROOT), text=True)
    return int(proc.returncode)


def dispatch(argv: list[str]) -> int:
    if not argv:
        return run("scripts/forks/forks.py", [])

    command = argv[0]
    rest = argv[1:]
    key = command.lower()

    table: dict[str, tuple[str, list[str]]] = {
        "import-json": ("scripts/forks/import_json_patch.py", []),
        "land-json": ("scripts/forks/land_json_patch.py", []),
        "land-json-file": ("scripts/forks/land_json_patch.py", ["--require-file"]),
        "replay-plan": ("scripts/forks/replay_plan.py", []),
        "replay-sync": ("scripts/forks/replay_sync.py", []),
        "ensure-node-toolchains": ("scripts/forks/ensure_node_toolchains.py", []),
        "gadget-init": ("scripts/forks/gadget_branches.py", ["init"]),
        "gadget-status": ("scripts/forks/gadget_branches.py", ["status"]),
        "gadget-sync": ("scripts/forks/gadget_branches.py", ["sync"]),
        "gadget-sync-all": ("scripts/forks/gadget_branches.py", ["sync-all"]),
        "gadget-land-json": ("scripts/forks/gadget_land_json.py", []),
        "gadget-land-json-file": ("scripts/forks/gadget_land_json.py", ["--require-file"]),
        "gadget-promote": ("scripts/forks/gadget_promote.py", []),
        "accelerator": ("scripts/forks/accelerator.py", []),
        "capture": ("scripts/forks/submission_object.py", ["capture"]),
        "submission-status": ("scripts/forks/submission_object.py", ["status"]),
        "replay": ("scripts/forks/submission_object.py", ["replay"]),
        "verify-submission": ("scripts/forks/submission_object.py", ["verify"]),
        "submit-submission": ("scripts/forks/submission_object.py", ["submit"]),
        "submission-ship-plan": ("scripts/forks/submission_object.py", ["ship-plan"]),
        "sync-captured-lane": ("scripts/forks/submission_object.py", ["sync-lane"]),
        "amalgamate-all": ("scripts/forks/amalgamate_all.py", []),
        "plan": ("scripts/forks/workflow_plan.py", []),
        "run": ("scripts/forks/workflow_runner.py", []),
        "land": ("scripts/forks/workflow_runner.py", ["land"]),
        "sync-all": ("scripts/forks/workflow_runner.py", ["sync-all"]),
        "verify-agent": ("scripts/forks/workflow_runner.py", ["verify-agent"]),
    }

    routed = table.get(key)
    if routed is None:
        return run("scripts/forks/forks.py", [command, *rest])

    script, prefix = routed
    return run(script, [*prefix, *rest])


def main(argv: list[str]) -> int:
    return dispatch(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
