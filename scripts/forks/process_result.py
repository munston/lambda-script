#!/usr/bin/env python3
"""Minimal hierarchical process output for agent-facing buttons.

Successful inner tools are normally silent. Failed inner tools report only the
failed stage plus a short root-cause summary. Full child output is captured for
parsing, then discarded from the interactive transcript.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ERROR_MARKERS = (
    "error:",
    "fatal:",
    "traceback",
    "assertionerror",
    "exception",
    "cabal-",
    "ghc-",
    "not in scope",
    "parse error",
    "type error",
    "npm err",
    "cannot find",
    "not found",
    "failed",
)

NOISE_PREFIXES = (
    "> ",
    "running ",
    "checking ",
    "warning: squelched ",
    "warning: ",
    "submitted to ",
    "final ",
    "gadget ",
)


@dataclass
class ProcessResult:
    label: str
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def combined(self) -> str:
        if self.stdout and self.stderr:
            return self.stdout + "\n" + self.stderr
        return self.stdout or self.stderr


def run_captured(label: str, args: list[str], cwd: Path) -> ProcessResult:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return ProcessResult(label, args, int(proc.returncode), proc.stdout or "", proc.stderr or "")


def replay_audit_summary(text: str) -> str | None:
    lower = text.lower()
    if "replay materialisation audit failed" not in lower:
        return None
    mismatch = len(re.findall(r"final file hash mismatch", lower))
    missing = len(re.findall(r"latest replay-touched file missing", lower))
    touched = mismatch + missing
    if touched:
        return f"replay audit failed; {touched} replay-touched file(s) differ or are missing"
    return "replay audit failed"


def first_error_summary(text: str) -> str | None:
    raw = [line.strip() for line in text.splitlines() if line.strip()]
    for line in raw:
        lower = line.lower()
        if any(marker in lower for marker in ERROR_MARKERS):
            return scrub_line(line)
    return None


def scrub_line(line: str) -> str:
    line = re.sub(r"\bexpected=[0-9a-fA-F]{16,}\b", "expected=<hash>", line)
    line = re.sub(r"\bactual=[0-9a-fA-F]{16,}\b", "actual=<hash>", line)
    line = re.sub(r"[A-Za-z]:\\[^:\n\r]*", "<path>", line)
    line = re.sub(r"/[^:\n\r ]{20,}", "<path>", line)
    return line.strip()


def diagnostic_lines(text: str) -> list[str]:
    raw = [line.rstrip() for line in text.splitlines()]
    indexed = [(i, line) for i, line in enumerate(raw) if line.strip()]
    hits: set[int] = set()
    lowered = [(i, line, line.lower()) for i, line in indexed]
    for i, line, lower in lowered:
        if any(marker in lower for marker in ERROR_MARKERS):
            for j in range(max(0, i - 1), min(len(raw), i + 3)):
                if raw[j].strip():
                    hits.add(j)
    if not hits:
        kept: list[int] = []
        for i, line in indexed[-8:]:
            lower = line.lower()
            if any(line.lower().startswith(p) for p in NOISE_PREFIXES) and "error" not in lower and "failed" not in lower:
                continue
            kept.append(i)
        hits.update(kept)
    return [scrub_line(raw[i]) for i in sorted(hits)]


def prune_process_text(text: str, *, max_lines: int = 8, max_chars: int = 1200) -> str:
    audit = replay_audit_summary(text)
    if audit:
        return audit
    first = first_error_summary(text)
    if first:
        return first
    lines = diagnostic_lines(text)
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... {len(lines) - max_lines} more diagnostic line(s) omitted"]
    out = "\n".join(lines).strip()
    if len(out) > max_chars:
        out = out[:max_chars].rstrip() + "\n... diagnostic text truncated ..."
    return out


def print_process_result(
    result: ProcessResult,
    *,
    print_ok: bool = False,
    failure_label: str | None = None,
) -> None:
    if result.ok:
        if print_ok:
            print(f"{result.label}: ok.")
        return
    label = failure_label or f"{result.label}: failed"
    print(label + ".")
    pruned = prune_process_text(result.combined)
    if pruned:
        for line in pruned.splitlines():
            print(f"  {line}")


def run_step(
    label: str,
    args: list[str],
    cwd: Path,
    *,
    print_ok: bool = False,
    failure_label: str | None = None,
) -> int:
    result = run_captured(label, args, cwd)
    print_process_result(result, print_ok=print_ok, failure_label=failure_label)
    return result.returncode


def run_step_quiet(label: str, args: list[str], cwd: Path) -> int:
    """Compatibility helper for target-facing buttons.

    Success produces no child-tool output. Failure prints the stage name and a
    pruned root-cause summary.
    """
    return run_step(label, args, cwd, print_ok=False)
