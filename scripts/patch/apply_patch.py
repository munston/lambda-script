#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

START = "LS_PATCH_V1"
DIFF_START = "--- DIFF ---"
DIFF_END = "--- END DIFF ---"

MESSAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,_:;()/+\-]{0,119}$")


class PatchError(Exception):
    pass


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise PatchError("not inside a git repository")
    return Path(proc.stdout.strip())


def read_patch(path: Path) -> str:
    if not path.exists():
        raise PatchError(f"patch file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def parse_patch(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != START:
        raise PatchError(f"first line must be {START}")

    message = None
    diff_start = None
    diff_end = None

    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")
        if line.startswith("COMMIT_MESSAGE:"):
            message = line.split(":", 1)[1].strip()
        elif line.strip() == DIFF_START:
            diff_start = i + 1
        elif line.strip() == DIFF_END:
            diff_end = i
            break

    if not message:
        raise PatchError("missing COMMIT_MESSAGE")
    if not MESSAGE_RE.match(message):
        raise PatchError("COMMIT_MESSAGE contains unsupported characters or is too long")
    if diff_start is None:
        raise PatchError(f"missing {DIFF_START}")
    if diff_end is None:
        raise PatchError(f"missing {DIFF_END}")
    if diff_end <= diff_start:
        raise PatchError("empty diff")

    diff = "\n".join(lines[diff_start:diff_end]) + "\n"
    if "diff --git " not in diff:
        raise PatchError("diff must contain at least one git-style unified diff beginning with diff --git")
    return message, diff


def run_git_apply(diff: str, check: bool) -> None:
    args = ["git", "apply", "--whitespace=nowarn"]
    if check:
        args.append("--check")
    proc = subprocess.run(
        args,
        input=diff,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.returncode != 0:
        mode = "check" if check else "apply"
        raise PatchError(f"git apply {mode} failed")


def ensure_no_tracked_dirty_changes() -> None:
    checks = [
        ["git", "diff", "--quiet"],
        ["git", "diff", "--cached", "--quiet"],
    ]
    for args in checks:
        proc = subprocess.run(args)
        if proc.returncode != 0:
            raise PatchError("tracked changes already exist; commit/stash/revert them before applying a received patch")


def self_test() -> None:
    sample = """LS_PATCH_V1
COMMIT_MESSAGE: Add sample file
--- DIFF ---
diff --git a/sample.txt b/sample.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/sample.txt
@@ -0,0 +1 @@
+sample
--- END DIFF ---
"""
    message, diff = parse_patch(sample)
    assert message == "Add sample file"
    assert "sample.txt" in diff
    print("OK patch parser self-test")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply LambdaScript patch-envelope files.")
    parser.add_argument("patch_file", nargs="?", help="Patch envelope file")
    parser.add_argument("--message", action="store_true", help="Print COMMIT_MESSAGE only")
    parser.add_argument("--check", action="store_true", help="Check patch with git apply --check, do not apply")
    parser.add_argument("--self-test", action="store_true", help="Run parser self-test")
    args = parser.parse_args()

    try:
        if args.self_test:
            self_test()
            return

        if not args.patch_file:
            raise PatchError("missing patch file")

        _root = repo_root()
        text = read_patch(Path(args.patch_file))
        message, diff = parse_patch(text)

        if args.message:
            print(message)
            return

        ensure_no_tracked_dirty_changes()
        run_git_apply(diff, check=True)

        if args.check:
            print("OK patch check")
            return

        run_git_apply(diff, check=False)
        print("OK patch applied")
        print(f"COMMIT_MESSAGE: {message}")

    except PatchError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
