#!/usr/bin/env python3
"""Hierarchical subprocess result capture and output pruning.

This module is deliberately small and dependency-free. It gives the forks tools
one shared rule: successful inner commands collapse to a short "ok" line, while
failed commands surface only the diagnostic core needed by a model or operator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess


ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
ERROR_PATTERNS = (
    " error:",
    "error ",
    "error[",
    "fatal:",
    "exception",
    "traceback",
    "assertionerror",
    "syntaxerror",
    "typeerror",
    "valueerror",
    "runtimeerror",
    "unicodedecodeerror",
    "cabal-",
    "ghc-",
    "failed",
    "cannot ",
    "can't ",
    "missing ",
    "not found",
    "no such file",
    "npm err",
    "module not found",
)


@dataclass
class ProcessResult:
    label: str
    args: list[str]
    cwd: str
    returncode: int
    stdout: str = ""
    stderr: str = ""
    children: list["ProcessResult"] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and all(child.ok for child in self.children)


def quote_arg(value: str) -> str:
    if any(ch.isspace() for ch in value) or '"' in value:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def command_text(args: list[str]) -> str:
    return " ".join(quote_arg(str(arg)) for arg in args)


def run_process(label: str, args: list[str], cwd: Path) -> ProcessResult:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return ProcessResult(
        label=label,
        args=[str(arg) for arg in args],
        cwd=str(cwd),
        returncode=int(proc.returncode),
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def clean_text(text: str) -> list[str]:
    text = ANSI_RE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    return [line.rstrip() for line in text.split("\n")]


def interesting(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return False
    return any(pattern in lowered for pattern in ERROR_PATTERNS)


def dedupe_preserve(lines: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.strip()
        if not key:
            if out and out[-1] != "":
                out.append("")
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out


def prune_failure_text(stdout: str, stderr: str, *, max_lines: int = 28, context: int = 2, max_chars: int = 5000) -> str:
    combined = []
    if stderr:
        combined.extend(clean_text(stderr))
    if stdout:
        if combined:
            combined.append("")
        combined.extend(clean_text(stdout))

    if not combined:
        return ""

    wanted: set[int] = set()
    for idx, line in enumerate(combined):
        if interesting(line):
            for j in range(max(0, idx - 1), min(len(combined), idx + context + 1)):
                wanted.add(j)

    if wanted:
        lines = [combined[i] for i in sorted(wanted)]
    else:
        lines = combined[-max_lines:]

    lines = dedupe_preserve(lines)
    if len(lines) > max_lines:
        head = lines[: max_lines // 2]
        tail = lines[-(max_lines - len(head)) :]
        lines = head + ["... pruned ..."] + tail

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n... pruned ..."
    return text


def indent_text(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line else prefix.rstrip() for line in text.splitlines())


def summarize(result: ProcessResult, *, indent: int = 0) -> str:
    pad = "  " * indent
    lines: list[str] = []

    if result.returncode == 0:
        lines.append(f"{pad}{result.label}: ok.")
    else:
        lines.append(f"{pad}{result.label}: failed (exit {result.returncode}).")
        diagnostic = prune_failure_text(result.stdout, result.stderr)
        if diagnostic:
            lines.append(indent_text(diagnostic, pad + "  "))
        else:
            lines.append(f"{pad}  no diagnostic output captured.")

    for child in result.children:
        lines.append(summarize(child, indent=indent + 1))
    return "\n".join(lines)


def require_ok(result: ProcessResult) -> None:
    if not result.ok:
        raise RuntimeError(summarize(result))
