#!/usr/bin/env python3
"""Install and verify local Node/TypeScript toolchains for repository packages.

The durable compiler is package-local: package.json + node_modules. This script
does not rely on global tsc, set PATH, or setx PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_PACKAGE_DIRS = ("glc", "tools/gizmo", "tools/text_metrics")


def repo_root() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return Path(proc.stdout.strip())


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    if os.name == "nt":
        command: str | list[str] = subprocess.list2cmdline(args)
        shell = True
    else:
        command = args
        shell = False
    print(f"[toolchain] {cwd}: {' '.join(args)}")
    proc = subprocess.run(command, cwd=str(cwd), text=True, shell=shell)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(args))
    return proc


def load_package(package_dir: Path) -> dict:
    package_file = package_dir / "package.json"
    if not package_file.exists():
        raise RuntimeError(f"missing package.json: {package_file}")
    return json.loads(package_file.read_text(encoding="utf-8"))


def package_dirs(root: Path, only: list[str]) -> list[Path]:
    rels = only if only else list(DEFAULT_PACKAGE_DIRS)
    out: list[Path] = []
    for rel in rels:
        path = (root / rel).resolve()
        if (path / "package.json").exists():
            out.append(path)
        elif only:
            raise RuntimeError(f"requested package directory has no package.json: {rel}")
    return out


def has_typescript_dependency(package: dict) -> bool:
    return "typescript" in package.get("dependencies", {}) or "typescript" in package.get("devDependencies", {})


def script_mentions_tsc(package: dict) -> bool:
    return any(isinstance(cmd, str) and ("tsc" in cmd or "typescript/bin/tsc" in cmd) for cmd in package.get("scripts", {}).values())


def needs_typescript(package: dict) -> bool:
    return has_typescript_dependency(package) or script_mentions_tsc(package)


def local_tsc(package_dir: Path) -> Path:
    suffix = "tsc.cmd" if os.name == "nt" else "tsc"
    return package_dir / "node_modules" / ".bin" / suffix


def ensure_install(package_dir: Path, install: bool) -> None:
    package = load_package(package_dir)
    need_ts = needs_typescript(package)
    node_modules = package_dir / "node_modules"
    tsc = local_tsc(package_dir)

    if node_modules.exists() and (not need_ts or tsc.exists()):
        print(f"[toolchain] ok: {package_dir}")
        return

    if not install:
        if need_ts:
            raise RuntimeError(f"missing local TypeScript compiler in {package_dir}; run with --install")
        raise RuntimeError(f"missing node_modules in {package_dir}; run with --install")

    run(["npm", "install"], package_dir)

    if need_ts and not tsc.exists():
        raise RuntimeError(f"npm install completed but local TypeScript compiler is still missing: {tsc}")


def check_typescript(package_dir: Path) -> None:
    if needs_typescript(load_package(package_dir)):
        run(["npm", "exec", "--", "tsc", "--version"], package_dir)


def maybe_build(package_dir: Path, build: bool) -> None:
    if build and "build" in load_package(package_dir).get("scripts", {}):
        run(["npm", "run", "build"], package_dir)


def maybe_test(package_dir: Path, test: bool) -> None:
    if test and "test" in load_package(package_dir).get("scripts", {}):
        run(["npm", "test"], package_dir)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ensure_node_toolchains")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args(argv)

    try:
        root = repo_root()
        dirs = package_dirs(root, args.only)
        if not dirs:
            print("[toolchain] no package directories found")
            return 0
        for package_dir in dirs:
            ensure_install(package_dir, args.install)
            check_typescript(package_dir)
            maybe_build(package_dir, args.build)
            maybe_test(package_dir, args.test)
        print("[toolchain] node toolchains ready")
        return 0
    except Exception as exc:
        print(f"ensure-node-toolchains: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
