from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .detector import report_to_json, scan_path

def cmd_scan(args: argparse.Namespace) -> int:
    suppression_path = Path(args.suppressions) if args.suppressions else None
    report = scan_path(Path(args.path), suppression_path=suppression_path)
    text = report_to_json(report, include_suppressed=not args.hide_suppressed)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.fail_on_error and not report.passed:
        return 1
    if args.fail_on_warning and report.warning_count > 0:
        return 1
    if args.fail_on_issues and report.issue_count > 0:
        return 1
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="merlin")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan a source tree for mock and stub signals")
    scan.add_argument("path")
    scan.add_argument("--out")
    scan.add_argument("--suppressions", help="optional LS_MERLIN_SUPPRESSIONS_V1 JSON file")
    scan.add_argument("--hide-suppressed", action="store_true", help="omit suppressed findings from the JSON report")
    scan.add_argument("--fail-on-error", action="store_true", help="exit nonzero when any gear has an error finding")
    scan.add_argument("--fail-on-warning", action="store_true", help="exit nonzero when any warning finding is present")
    scan.add_argument("--fail-on-issues", action="store_true", help="exit nonzero when any unsuppressed finding is present")
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
