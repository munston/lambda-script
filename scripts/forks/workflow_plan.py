#!/usr/bin/env python3
"""Print a forks workflow after parameter binding, without executing operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import workflow_runner as runner


def bind_steps(workflow: dict[str, Any], env: dict[str, str]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for raw in workflow.get("steps", []):
        step = runner.subst(raw, env)
        op = step.get("op")
        if op not in runner.OPS:
            raise RuntimeError(f"unknown workflow op: {op}")
        steps.append(step)
    return steps


def describe_step(index: int, step: dict[str, Any]) -> str:
    op = step.get("op")
    rest = {k: v for k, v in step.items() if k != "op"}
    if rest:
        return f"{index}. {op} {json.dumps(rest, sort_keys=True)}"
    return f"{index}. {op}"


def run_plan(name: str, argv: list[str]) -> int:
    root = runner.repo_root()
    workflow = runner.load_workflow(root, name)
    env = runner.bind_workflow(workflow, argv)
    steps = bind_steps(workflow, env)
    print(f"workflow {name} plan")
    if env:
        print("parameters " + json.dumps(env, sort_keys=True))
    for index, step in enumerate(steps, start=1):
        print(describe_step(index, step))
    print("plan only: no workflow operations executed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forks plan", description="Print a forks workflow without executing it")
    parser.add_argument("workflow")
    parser.add_argument("args", nargs="*")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_plan(args.workflow, args.args)
    except Exception as exc:
        print(f"forks plan: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
