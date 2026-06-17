#!/usr/bin/env python3
"""Target-backed JSON landing button implementation.

The generated land button hardcodes agent, gizmo, and gadget. Runtime use is:

    land-<target>.bat <patch.json>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import forks
import process_result


def script(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        raise RuntimeError(f"missing required tool: {rel}")
    return str(path)


def target_ref(gizmo: str, gadget: str) -> str:
    return f"origin/gadgets/{gizmo}/{gadget}/main"


def lane_ref(gizmo: str, gadget: str, agent: str) -> str:
    return f"gadget-agents/{gizmo}/{gadget}/{agent}"


def target_name(agent: str, gizmo: str, gadget: str) -> str:
    if gizmo == gadget:
        return f"{gadget}-{agent}"
    return f"{gizmo}-{gadget}-{agent}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="land-targeted",
        description="Land one JSON patch to the hardcoded target agent lane.",
    )
    parser.add_argument("agent")
    parser.add_argument("gizmo")
    parser.add_argument("gadget")
    parser.add_argument("patch")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    args.agent = forks.normalize_agent(args.agent)
    if args.agent not in forks.AGENTS:
        raise RuntimeError(f"unsupported agent {args.agent!r}; expected one of {', '.join(forks.AGENTS)}")
    patch = Path(args.patch).expanduser().resolve()
    if not patch.exists() or not patch.is_file():
        raise RuntimeError(f"patch file does not exist: {patch}")
    root = forks.repo_root()
    name = target_name(args.agent, args.gizmo, args.gadget)

    code = process_result.run_step(
        "json landing",
        [
            sys.executable,
            script(root, "scripts/forks/land_json_patch.py"),
            "--require-file",
            "--target-ref",
            target_ref(args.gizmo, args.gadget),
            "--push-ref",
            lane_ref(args.gizmo, args.gadget, args.agent),
            "--no-sync",
            args.agent,
            str(patch),
        ],
        root,
        failure_label=f"land-{name}: failed",
    )
    if code == 0:
        print(f"land-{name}: landed.")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"land: {exc}", file=sys.stderr)
        raise SystemExit(1)
