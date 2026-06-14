from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable

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

RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("not-implemented", re.compile(r"\braise\s+NotImplementedError\b|\bTODO\b|\bFIXME\b"), "explicit incomplete implementation marker"),
    ("mock-language", re.compile(r"\b(mock|stub|dummy|fake|placeholder)\b", re.IGNORECASE), "mock or placeholder language in source"),
    ("empty-python-pass", re.compile(r"^\s*pass\s*(#.*)?$"), "bare pass statement"),
    ("weak-return-none", re.compile(r"^\s*return\s+None\s*(#.*)?$"), "unqualified None return"),
    ("weak-return-empty", re.compile(r"^\s*return\s+(\{\}|\[\]|\(\)|''|\"\")\s*(#.*)?$"), "unqualified empty return value"),
    ("typescript-throw-placeholder", re.compile(r"throw\s+new\s+Error\s*\(\s*['\"](not implemented|todo|stub|mock)", re.IGNORECASE), "placeholder exception"),
]

@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    rule: str
    message: str
    text: str

@dataclass(frozen=True)
class ScanReport:
    format: str
    root: str
    scanned_files: int
    issue_count: int
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
        for rule, pattern, message in RULES:
            if pattern.search(line):
                issues.append(Issue(
                    path=str(path.relative_to(root)) if path != root else path.name,
                    line=line_no,
                    rule=rule,
                    message=message,
                    text=line.strip(),
                ))
    return issues

def scan_path(path: Path) -> ScanReport:
    root = path.resolve()
    if not root.exists():
        raise FileNotFoundError(str(path))
    files = list(iter_source_files(root))
    issues: list[Issue] = []
    for file_path in files:
        issues.extend(scan_file(root if root.is_dir() else root.parent, file_path))
    return ScanReport(
        format="LS_MERLIN_SCAN_V1",
        root=str(root),
        scanned_files=len(files),
        issue_count=len(issues),
        issues=issues,
    )

def report_to_json(report: ScanReport) -> str:
    payload = {
        "format": report.format,
        "root": report.root,
        "scanned_files": report.scanned_files,
        "issue_count": report.issue_count,
        "issues": [issue.__dict__ for issue in report.issues],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
