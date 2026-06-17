#!/usr/bin/env python3
"""Compact hierarchical process output for agent-facing tooling.

Successful child tools normally produce a single ``<label>: ok.`` line. Failed
tools keep only the diagnostic core so model readers are not charged for
irrelevant build, fetch, or wrapper noise.
"""

from __future__ import annotations

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


def diagnostic_lines(text: str) -> list[str]:
    raw = [line.rstrip() for line in text.splitlines()]
    indexed = [(i, line) for i, line in enumerate(raw) if line.strip()]
    hits: set[int] = set()
    lowered = [(i, line, line.lower()) for i, line in indexed]
    for i, line, lower in lowered:
        if any(marker in lower for marker in ERROR_MARKERS):
            for j in range(max(0, i - 2), min(len(raw), i + 7)):
                if raw[j].strip():
                    hits.add(j)
    if not hits:
        kept: list[int] = []
        for i, line in indexed[-30:]:
            lower = line.lower()
            if any(line.startswith(p) for p in NOISE_PREFIXES) and "error" not in lower and "failed" not in lower:
                continue
            kept.append(i)
        hits.update(kept)
    return [raw[i] for i in sorted(hits)]


def prune_process_text(text: str, *, max_lines: int = 80, max_chars: int = 12000) -> str:
    lines = diagnostic_lines(text)
    if len(lines) > max_lines:
        head = lines[: max_lines // 2]
        tail = lines[-(max_lines // 2):]
        lines = head + [f"... {len(lines) - len(head) - len(tail)} diagnostic lines omitted ..."] + tail
    out = "\n".join(lines).strip()
    if len(out) > max_chars:
        out = out[:max_chars].rstrip() + "\n... diagnostic text truncated ..."
    return out


def print_process_result(result: ProcessResult) -> None:
    if result.ok:
        print(f"{result.label}: ok.")
        return
    print(f"{result.label}: failed (exit {result.returncode}).")
    pruned = prune_process_text(result.combined)
    if pruned:
        for line in pruned.splitlines():
            print(f"  {line}")


def run_step(label: str, args: list[str], cwd: Path) -> int:
    result = run_captured(label, args, cwd)
    print_process_result(result)
    return result.returncode
