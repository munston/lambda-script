from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .detector import report_to_json, scan_path

def cmd_scan(args: argparse.Namespace) -> int:
    report = scan_path(Path(args.path))
    text = report_to_json(report)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.fail_on_issues and report.issue_count > 0:
        return 1
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="merlin")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan a source tree for mock and stub signals")
    scan.add_argument("path")
    scan.add_argument("--out")
    scan.add_argument("--fail-on-issues", action="store_true")
    scan.set_defaults(func=cmd_scan)
    return parser

def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"merlin: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
