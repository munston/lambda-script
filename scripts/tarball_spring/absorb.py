#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

TARBALL_EXTENSIONS = (
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".tbz2",
    ".tar.xz",
    ".txz",
)

DEFAULT_MESSAGE = "Absorb tarball spring"

KEYLIKE_RE = re.compile(
    r"(^|/)(id_ed25519|id_ed25519\.pub|id_rsa|id_rsa\.pub|.*\.pem|.*\.ppk|.*\.keyfile|.*\.keyfile\.pub|key\.keyfile|key\.keyfile\.pub)$",
    re.IGNORECASE,
)


class SpringError(Exception):
    pass


def git_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise SpringError("not inside a git repository")
    return Path(proc.stdout.strip())


def is_tarball(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(ext) for ext in TARBALL_EXTENSIONS)


def normalise_member_name(raw_name: str) -> str:
    name = raw_name.replace("\\", "/")
    if name.startswith("/") or re.match(r"^[A-Za-z]:/", name):
        raise SpringError(f"absolute path rejected: {raw_name}")
    pure = PurePosixPath(name)
    parts = pure.parts
    if not parts or parts == (".",):
        raise SpringError(f"empty path rejected: {raw_name}")
    if any(part in ("", ".", "..") for part in parts):
        raise SpringError(f"path escape rejected: {raw_name}")
    clean = "/".join(parts)
    if clean.startswith(".git/") or clean == ".git":
        raise SpringError(f".git path rejected: {raw_name}")
    if clean.startswith("spring/tarball/") or clean == "spring/tarball":
        raise SpringError(f"tarball spring self-write rejected: {raw_name}")
    if KEYLIKE_RE.search(clean):
        raise SpringError(f"key-like path rejected: {raw_name}")
    return clean


def safe_target(root: Path, relative_name: str) -> Path:
    target = (root / relative_name).resolve()
    root_resolved = root.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise SpringError(f"path escapes repository: {relative_name}") from exc
    return target


def spring_dirs(root: Path) -> tuple[Path, Path, Path]:
    spring = root / "spring" / "tarball"
    return spring / "drop", spring / "archive", spring / "work"


def find_single_tarball(drop: Path) -> Path:
    drop.mkdir(parents=True, exist_ok=True)
    entries = [p for p in drop.iterdir() if p.name != ".gitignore"]
    if not entries:
        raise SpringError("no tarball in spring/tarball/drop")
    bad = [p.name for p in entries if not p.is_file() or not is_tarball(p)]
    if bad:
        raise SpringError(f"non-tarball entries in drop: {', '.join(bad)}")
    if len(entries) > 1:
        raise SpringError("more than one tarball in spring/tarball/drop")
    return entries[0]


def load_manifest(tar: tarfile.TarFile) -> dict[str, object]:
    try:
        member = tar.getmember("LS_TARBALL_MANIFEST.json")
    except KeyError:
        return {}
    if not member.isfile():
        raise SpringError("LS_TARBALL_MANIFEST.json is not a regular file")
    extracted = tar.extractfile(member)
    if extracted is None:
        raise SpringError("cannot read LS_TARBALL_MANIFEST.json")
    try:
        data = json.loads(extracted.read().decode("utf-8"))
    except Exception as exc:
        raise SpringError("invalid LS_TARBALL_MANIFEST.json") from exc
    if data.get("format") != "LS_TARBALL_SPRING_V1":
        raise SpringError("manifest format must be LS_TARBALL_SPRING_V1")
    return data


def message_from_manifest(manifest: dict[str, object], tarball: Path) -> str:
    raw = manifest.get("commit_message")
    if isinstance(raw, str) and raw.strip():
        msg = raw.strip()
    else:
        msg = f"{DEFAULT_MESSAGE}: {tarball.name}"
    if len(msg) > 120:
        raise SpringError("commit message is too long")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9 .,_:;()/+\-]{0,119}$", msg):
        raise SpringError("commit message contains unsupported characters")
    return msg


def inspect_tarball(tarball: Path) -> tuple[dict[str, object], list[tarfile.TarInfo], list[str]]:
    with tarfile.open(tarball, "r:*") as tar:
        manifest = load_manifest(tar)
        members = []
        names = []
        for member in tar.getmembers():
            if member.name == "LS_TARBALL_MANIFEST.json":
                continue
            if member.isdir():
                continue
            if not member.isfile():
                raise SpringError(f"non-regular tar member rejected: {member.name}")
            clean = normalise_member_name(member.name)
            members.append(member)
            names.append(clean)
        if not names:
            raise SpringError("tarball contains no regular files to absorb")
        if len(names) != len(set(names)):
            raise SpringError("tarball contains duplicate target paths")
        return manifest, members, names


def absorb(root: Path, tarball: Path, work: Path, archive: Path) -> str:
    manifest, members, names = inspect_tarball(tarball)
    message = message_from_manifest(manifest, tarball)

    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tarball, "r:*") as tar:
        for member, clean in zip(members, names):
            target = safe_target(root, clean)
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tar.extractfile(member)
            if src is None:
                raise SpringError(f"cannot read tar member: {member.name}")
            with target.open("wb") as out:
                shutil.copyfileobj(src, out)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived = archive / f"{timestamp}-{tarball.name}"
    shutil.move(str(tarball), str(archived))

    print(f"OK absorbed {len(names)} file(s)")
    print(f"ARCHIVED: {archived}")
    print(f"COMMIT_MESSAGE: {message}")
    return message


def main() -> None:
    parser = argparse.ArgumentParser(description="Absorb exactly one tarball from the LambdaScript tarball spring.")
    parser.add_argument("--message-only", action="store_true", help="Print the commit message for the pending tarball and exit")
    parser.add_argument("--list", action="store_true", help="List files in the pending tarball and exit")
    args = parser.parse_args()

    try:
        root = git_root()
        drop, archive, work = spring_dirs(root)
        tarball = find_single_tarball(drop)
        manifest, _members, names = inspect_tarball(tarball)
        message = message_from_manifest(manifest, tarball)

        if args.message_only:
            print(message)
            return
        if args.list:
            for name in names:
                print(name)
            return

        absorb(root, tarball, work, archive)
    except SpringError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
