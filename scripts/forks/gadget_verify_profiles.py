#!/usr/bin/env python3
"""Manifest verification profile lookup for gizmo gadgets."""

from __future__ import annotations

import json
import re
from pathlib import Path

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def clean_name(kind: str, value: str) -> str:
    name = value.strip()
    if not NAME_RE.match(name):
        raise RuntimeError(f"invalid {kind} name: {value!r}")
    return name


def manifest_path(root: Path, gizmo: str) -> Path:
    return root / "examples" / "gizmos" / f"{clean_name('gizmo', gizmo)}.gizmo.json"


def load_manifest(root: Path, gizmo: str) -> dict:
    path = manifest_path(root, gizmo)
    if not path.exists():
        raise RuntimeError(f"missing gizmo manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def profile_commands(root: Path, gizmo: str, gadget: str, profile: str) -> list[str] | None:
    manifest = load_manifest(root, gizmo)
    gadget_name = clean_name("gadget", gadget)
    profile_name = clean_name("profile", profile)

    gadgets = manifest.get("gadgets")
    if not isinstance(gadgets, dict):
        raise RuntimeError(f"manifest for {gizmo} has no gadgets object")

    gadget_data = gadgets.get(gadget_name)
    if not isinstance(gadget_data, dict):
        raise RuntimeError(f"manifest for {gizmo} has no gadget {gadget_name}")

    profiles = gadget_data.get("verification_profiles")
    if profiles is None:
        return None
    if not isinstance(profiles, dict):
        raise RuntimeError(f"verification_profiles for {gizmo}/{gadget_name} must be an object")

    commands = profiles.get(profile_name)
    if commands is None:
        return None
    if not isinstance(commands, list) or not all(isinstance(item, str) and item.strip() for item in commands):
        raise RuntimeError(f"verification profile {profile_name} for {gizmo}/{gadget_name} must be a list of commands")

    return list(commands)
