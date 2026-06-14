from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
import hashlib
import json
import re
from typing import Any, Iterable, Literal

MERLIN_VERSION = "0.2.0"
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
    suffixes: frozenset[str] | None = None

RULES: list[Rule] = [
    Rule("implementation-presence", "incomplete-marker", "warning", re.compile(r"\bTODO\b|\bFIXME\b"), "explicit incomplete implementation marker"),
    Rule("implementation-presence", "python-not-implemented", "error", re.compile(r"\braise\s+NotImplementedError\b"), "Python NotImplementedError placeholder"),
    Rule("implementation-presence", "python-pass", "error", re.compile(r"^\s*pass\s*(#.*)?$"), "bare pass statement", frozenset({".py"})),
    Rule("return-substance", "weak-return-none", "error", re.compile(r"^\s*return\s+None\s*(#.*)?$"), "unqualified None return", frozenset({".py"})),
    Rule("return-substance", "weak-return-empty", "error", re.compile(r"^\s*return\s+(\{\}|\[\]|\(\)|''|\"\")\s*(#.*)?$"), "unqualified empty return value", frozenset({".py", ".ts", ".tsx", ".js", ".jsx"})),
    Rule("implementation-presence", "typescript-throw-placeholder", "error", re.compile(r"throw\s+new\s+Error\s*\(\s*['\"](not implemented|todo|stub|mock)", re.IGNORECASE), "placeholder exception", frozenset({".ts", ".tsx", ".js", ".jsx"})),
    Rule("semantic-substance", "mock-language", "warning", re.compile(r"\b(mock|stub|dummy|fake|placeholder)\b", re.IGNORECASE), "mock or placeholder language in source"),
    Rule("test-integrity", "test-skip", "warning", re.compile(r"\b(pytest\.mark\.skip|describe\.skip|it\.skip|test\.skip|xit\s*\()"), "test skip marker"),
]

@dataclass(frozen=True)
class Suppression:
    path: str | None = None
    rule: str | None = None
    gear: str | None = None
    fingerprint: str | None = None
    reason: str = "unspecified"

@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    rule: str
    gear: str
    severity: Severity
    message: str
    text: str
    fingerprint: str

@dataclass(frozen=True)
class SuppressedIssue:
    issue: Issue
    reason: str
    source: str

@dataclass(frozen=True)
class GearResult:
    gear: str
    passed: bool
    issue_count: int
    error_count: int
    warning_count: int
    suppressed_count: int

@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str

@dataclass(frozen=True)
class ScanReport:
    format: str
    version: str
    generated_at: str
    root: str
    scanned_files: int
    gear_count: int
    passed: bool
    issue_count: int
    error_count: int
    warning_count: int
    suppressed_count: int
    files: list[FileRecord]
    gears: list[GearResult]
    issues: list[Issue]
    suppressed_issues: list[SuppressedIssue]

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def path_key(root: Path, path: Path) -> str:
    base = root if root.is_dir() else root.parent
    return path.relative_to(base).as_posix()

def issue_fingerprint(path: str, rule: str, text: str) -> str:
    normalized = " ".join(text.strip().split())
    return sha256_text(f"{path}\0{rule}\0{normalized}")[:16]

def iter_source_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix in SOURCE_SUFFIXES:
            yield root
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and ".git" not in path.parts:
            yield path

def rule_applies(rule: Rule, path: Path) -> bool:
    return rule.suffixes is None or path.suffix in rule.suffixes

def inline_suppresses(line: str, rule: Rule) -> bool:
    match = re.search(r"merlin:\s*allow(?::|\s+)?\s*([^#/]*)", line, re.IGNORECASE)
    if not match:
        return False
    raw = match.group(1).strip()
    if raw == "":
        return True
    tokens = {token.strip() for token in re.split(r"[,\s]+", raw) if token.strip()}
    return rule.name in tokens or rule.gear in tokens or "all" in tokens

def scan_file(root: Path, path: Path) -> tuple[list[Issue], list[SuppressedIssue]]:
    issues: list[Issue] = []
    suppressed: list[SuppressedIssue] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return issues, suppressed
    rel = path_key(root, path)
    for line_no, line in enumerate(lines, start=1):
        for rule in RULES:
            if not rule_applies(rule, path):
                continue
            if not rule.pattern.search(line):
                continue
            issue = Issue(
                path=rel,
                line=line_no,
                rule=rule.name,
                gear=rule.gear,
                severity=rule.severity,
                message=rule.message,
                text=line.strip(),
                fingerprint=issue_fingerprint(rel, rule.name, line),
            )
            if inline_suppresses(line, rule):
                suppressed.append(SuppressedIssue(issue=issue, reason="inline allow", source="inline"))
            else:
                issues.append(issue)
    return issues, suppressed

def load_suppressions(path: Path | None) -> list[Suppression]:
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "LS_MERLIN_SUPPRESSIONS_V1":
        raise RuntimeError("expected suppression format LS_MERLIN_SUPPRESSIONS_V1")
    rows = data.get("suppressions")
    if not isinstance(rows, list):
        raise RuntimeError("suppressions must be an array")
    suppressions: list[Suppression] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            raise RuntimeError(f"suppression {index} must be an object")
        reason = item.get("reason", "unspecified")
        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(f"suppression {index} reason must be a non-empty string")
        suppressions.append(Suppression(
            path=item.get("path") if isinstance(item.get("path"), str) else None,
            rule=item.get("rule") if isinstance(item.get("rule"), str) else None,
            gear=item.get("gear") if isinstance(item.get("gear"), str) else None,
            fingerprint=item.get("fingerprint") if isinstance(item.get("fingerprint"), str) else None,
            reason=reason,
        ))
    return suppressions

def suppression_matches(suppression: Suppression, issue: Issue) -> bool:
    if suppression.path is not None and not fnmatch(issue.path, suppression.path):
        return False
    if suppression.rule is not None and suppression.rule != issue.rule:
        return False
    if suppression.gear is not None and suppression.gear != issue.gear:
        return False
    if suppression.fingerprint is not None and suppression.fingerprint != issue.fingerprint:
        return False
    return True

def apply_suppressions(issues: list[Issue], suppressions: list[Suppression]) -> tuple[list[Issue], list[SuppressedIssue]]:
    active: list[Issue] = []
    suppressed: list[SuppressedIssue] = []
    for issue in issues:
        match = next((item for item in suppressions if suppression_matches(item, issue)), None)
        if match is None:
            active.append(issue)
        else:
            suppressed.append(SuppressedIssue(issue=issue, reason=match.reason, source="suppressions"))
    return active, suppressed

def file_record(root: Path, path: Path) -> FileRecord:
    data = path.read_bytes()
    return FileRecord(path=path_key(root, path), size=len(data), sha256=sha256_bytes(data))

def summarize_gears(issues: list[Issue], suppressed: list[SuppressedIssue]) -> list[GearResult]:
    gears: list[GearResult] = []
    for gear in sorted({rule.gear for rule in RULES}):
        gear_issues = [issue for issue in issues if issue.gear == gear]
        gear_suppressed = [item for item in suppressed if item.issue.gear == gear]
        error_count = sum(1 for issue in gear_issues if issue.severity == "error")
        warning_count = sum(1 for issue in gear_issues if issue.severity == "warning")
        gears.append(GearResult(
            gear=gear,
            passed=error_count == 0,
            issue_count=len(gear_issues),
            error_count=error_count,
            warning_count=warning_count,
            suppressed_count=len(gear_suppressed),
        ))
    return gears

def scan_path(path: Path, suppression_path: Path | None = None) -> ScanReport:
    root = path.resolve()
    if not root.exists():
        raise FileNotFoundError(str(path))
    files = list(iter_source_files(root))
    found: list[Issue] = []
    suppressed: list[SuppressedIssue] = []
    for file_path in files:
        active, inline_suppressed = scan_file(root, file_path)
        found.extend(active)
        suppressed.extend(inline_suppressed)
    suppressions = load_suppressions(suppression_path)
    issues, configured_suppressed = apply_suppressions(found, suppressions)
    suppressed.extend(configured_suppressed)
    gears = summarize_gears(issues, suppressed)
    error_count = sum(gear.error_count for gear in gears)
    warning_count = sum(gear.warning_count for gear in gears)
    return ScanReport(
        format="LS_MERLIN_SCAN_V1",
        version=MERLIN_VERSION,
        generated_at=now_iso(),
        root=str(root),
        scanned_files=len(files),
        gear_count=len(gears),
        passed=error_count == 0,
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        suppressed_count=len(suppressed),
        files=[file_record(root, file_path) for file_path in files],
        gears=gears,
        issues=issues,
        suppressed_issues=suppressed,
    )

def issue_to_payload(issue: Issue) -> dict[str, Any]:
    return {
        "path": issue.path,
        "line": issue.line,
        "rule": issue.rule,
        "gear": issue.gear,
        "severity": issue.severity,
        "message": issue.message,
        "text": issue.text,
        "fingerprint": issue.fingerprint,
    }

def report_to_payload(report: ScanReport, include_suppressed: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": report.format,
        "version": report.version,
        "generated_at": report.generated_at,
        "root": report.root,
        "scanned_files": report.scanned_files,
        "gear_count": report.gear_count,
        "passed": report.passed,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "suppressed_count": report.suppressed_count,
        "files": [record.__dict__ for record in report.files],
        "gears": [gear.__dict__ for gear in report.gears],
        "issues": [issue_to_payload(issue) for issue in report.issues],
    }
    if include_suppressed:
        payload["suppressed_issues"] = [
            {"reason": item.reason, "source": item.source, "issue": issue_to_payload(item.issue)}
            for item in report.suppressed_issues
        ]
    return payload

def report_to_json(report: ScanReport, include_suppressed: bool = True) -> str:
    return json.dumps(report_to_payload(report, include_suppressed), indent=2, sort_keys=True) + "\n"
