from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable, Literal

Severity = Literal["info", "warning", "error"]

SOURCE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".hs",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".rs",
    ".go",
}

@dataclass(frozen=True)
class Rule:
    gear: str
    name: str
    severity: Severity
    pattern: re.Pattern[str]
    message: str

RULES: list[Rule] = [
    Rule("implementation-presence", "not-implemented", "error", re.compile(r"\braise\s+NotImplementedError\b|\bTODO\b|\bFIXME\b"), "explicit incomplete implementation marker"),
    Rule("semantic-substance", "mock-language", "warning", re.compile(r"\b(mock|stub|dummy|fake|placeholder)\b", re.IGNORECASE), "mock or placeholder language in source"),
    Rule("implementation-presence", "empty-python-pass", "error", re.compile(r"^\s*pass\s*(#.*)?$"), "bare pass statement"),
    Rule("return-substance", "weak-return-none", "error", re.compile(r"^\s*return\s+None\s*(#.*)?$"), "unqualified None return"),
    Rule("return-substance", "weak-return-empty", "error", re.compile(r"^\s*return\s+(\{\}|\[\]|\(\)|''|\"\")\s*(#.*)?$"), "unqualified empty return value"),
    Rule("implementation-presence", "typescript-throw-placeholder", "error", re.compile(r"throw\s+new\s+Error\s*\(\s*['\"](not implemented|todo|stub|mock)", re.IGNORECASE), "placeholder exception"),
]

@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    rule: str
    gear: str
    severity: Severity
    message: str
    text: str

@dataclass(frozen=True)
class GearResult:
    gear: str
    passed: bool
    issue_count: int
    error_count: int
    warning_count: int

@dataclass(frozen=True)
class ScanReport:
    format: str
    root: str
    scanned_files: int
    gear_count: int
    passed: bool
    issue_count: int
    error_count: int
    warning_count: int
    gears: list[GearResult]
    issues: list[Issue]

def iter_source_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix in SOURCE_SUFFIXES:
            yield root
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and ".git" not in path.parts:
            yield path

def scan_file(root: Path, path: Path) -> list[Issue]:
    issues: list[Issue] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return issues
    for line_no, line in enumerate(lines, start=1):
        for rule in RULES:
            if rule.pattern.search(line):
                issues.append(Issue(
                    path=str(path.relative_to(root)) if path != root else path.name,
                    line=line_no,
                    rule=rule.name,
                    gear=rule.gear,
                    severity=rule.severity,
                    message=rule.message,
                    text=line.strip(),
                ))
    return issues

def summarize_gears(issues: list[Issue]) -> list[GearResult]:
    gears: list[GearResult] = []
    for gear in sorted({rule.gear for rule in RULES}):
        gear_issues = [issue for issue in issues if issue.gear == gear]
        error_count = sum(1 for issue in gear_issues if issue.severity == "error")
        warning_count = sum(1 for issue in gear_issues if issue.severity == "warning")
        gears.append(GearResult(
            gear=gear,
            passed=error_count == 0,
            issue_count=len(gear_issues),
            error_count=error_count,
            warning_count=warning_count,
        ))
    return gears

def scan_path(path: Path) -> ScanReport:
    root = path.resolve()
    if not root.exists():
        raise FileNotFoundError(str(path))
    files = list(iter_source_files(root))
    issues: list[Issue] = []
    for file_path in files:
        issues.extend(scan_file(root if root.is_dir() else root.parent, file_path))
    gears = summarize_gears(issues)
    error_count = sum(gear.error_count for gear in gears)
    warning_count = sum(gear.warning_count for gear in gears)
    return ScanReport(
        format="LS_MERLIN_SCAN_V1",
        root=str(root),
        scanned_files=len(files),
        gear_count=len(gears),
        passed=error_count == 0,
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        gears=gears,
        issues=issues,
    )

def report_to_json(report: ScanReport) -> str:
    payload = {
        "format": report.format,
        "root": report.root,
        "scanned_files": report.scanned_files,
        "gear_count": report.gear_count,
        "passed": report.passed,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "gears": [gear.__dict__ for gear in report.gears],
        "issues": [issue.__dict__ for issue in report.issues],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
