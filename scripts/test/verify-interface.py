from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

DISALLOWED_GIT_WORDS = [
    " reset ",
    " reset\t",
    " clean ",
    " clean\t",
    " rebase",
    " merge",
    " checkout",
    " restore",
    " switch",
    " push --force",
    " push -f",
    " commit --amend",
]

ALLOWED_GIT_PATTERNS = [
    "git -c",
    "git status --short --branch",
    "git fetch",
    "git pull --ff-only",
    "git add -a",
    "git diff --cached --quiet",
    "git commit -m",
    "git push",
]

EXPECTED_ROOT_BATS = ["pull.bat", "push.bat"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def config_path(root: Path, path_text: str) -> Path:
    parts = [p for p in re.split(r"[\\/]+", path_text) if p and p != "."]
    return root.joinpath(*parts) if parts else root


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def verify_root_bats() -> None:
    bats = sorted(p.name for p in ROOT.glob("*.bat"))
    if bats != EXPECTED_ROOT_BATS:
        fail(f"top-level .bat files are {bats}, expected {EXPECTED_ROOT_BATS}")
    pull = read(ROOT / "pull.bat")
    push = read(ROOT / "push.bat")
    if r"scripts\git\pull-all.bat" not in pull:
        fail("pull.bat does not delegate to scripts\\git\\pull-all.bat")
    if r"scripts\git\push-all.bat" not in push:
        fail("push.bat does not delegate to scripts\\git\\push-all.bat")


def parse_config() -> list[tuple[str, str, str, str, str]]:
    config = read(ROOT / "git.config")
    targets: list[tuple[str, str, str, str, str]] = []
    for line_number, raw in enumerate(config.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 5:
            fail(f"git.config line {line_number} has {len(parts)} fields, expected 5")
        name, path_part, remote, branch, test_script = parts
        if not name:
            fail(f"git.config line {line_number} has empty name")
        if not path_part:
            fail(f"git.config line {line_number} has empty path")
        if not remote:
            fail(f"git.config line {line_number} has empty remote")
        if not branch:
            fail(f"git.config line {line_number} has empty branch")
        if not test_script:
            fail(f"git.config line {line_number} has empty test script")
        targets.append((name, path_part, remote, branch, test_script))
    if not targets:
        fail("git.config has no active targets")
    return targets


def verify_target_scripts(targets: list[tuple[str, str, str, str, str]]) -> None:
    for name, path_part, _remote, _branch, test_script in targets:
        target_root = config_path(ROOT, path_part).resolve()
        try:
            target_root.relative_to(ROOT.parent)
        except ValueError:
            fail(f"{name} path escapes expected workspace area: {path_part}")
        if test_script != "-":
            path = config_path(target_root, test_script)
            if not path.exists():
                fail(f"{name} test script missing: {test_script}")


def verify_git_safety() -> None:
    batch_files = sorted((ROOT / "scripts").rglob("*.bat")) + [ROOT / "pull.bat", ROOT / "push.bat"]
    for path in batch_files:
        text = read(path)
        lowered = f" {text.lower()} "
        for word in DISALLOWED_GIT_WORDS:
            if word in lowered:
                fail(f"disallowed git operation {word.strip()} in {path.relative_to(ROOT)}")
        for raw in text.splitlines():
            line = raw.strip()
            lower = line.lower()
            if lower.startswith("git "):
                if not any(pattern in lower for pattern in ALLOWED_GIT_PATTERNS):
                    fail(f"unapproved git command in {path.relative_to(ROOT)}: {line}")


def verify_push_order() -> None:
    text = read(ROOT / "scripts" / "git" / "push-target.bat").lower()
    positions = {
        "status": text.find("status before push"),
        "fetch": text.find("git -c \"%dir%\" fetch"),
        "test": text.find("call \"%dir%\\%test%\""),
        "add": text.find("git -c \"%dir%\" add -a"),
        "commit": text.find("git -c \"%dir%\" commit -m"),
        "push": text.find("git -c \"%dir%\" push"),
    }
    missing = [name for name, pos in positions.items() if pos < 0]
    if missing:
        fail(f"push-target.bat missing expected stages: {missing}")
    if not (positions["status"] < positions["fetch"] < positions["test"] < positions["add"] < positions["commit"] < positions["push"]):
        fail(f"push-target.bat stage order is wrong: {positions}")


def main() -> None:
    verify_root_bats()
    targets = parse_config()
    verify_target_scripts(targets)
    verify_git_safety()
    verify_push_order()
    print("OK two-bat interface verified")
    print("root bat files:", ", ".join(EXPECTED_ROOT_BATS))
    print("targets:", ", ".join(name for name, *_ in targets))
    print("safe git subset: status, fetch, pull --ff-only, add -A, diff --cached --quiet, commit -m, push HEAD:branch")


if __name__ == "__main__":
    main()
