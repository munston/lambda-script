#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
import re

def is_key_like(path: str) -> bool:
    lower = path.lower()
    if any(x in lower for x in ['.pem', '.ppk', '.key', 'id_ed25519', 'id_rsa', 'private']):
        return True
    return False

def file_exists_in_head(path: str) -> bool:
    try:
        result = subprocess.run(['git', 'cat-file', '-e', f'HEAD:{path}'], 
                              capture_output=True, check=False)
        return result.returncode == 0
    except:
        return False

def get_changed_files():
    files = []
    # Tracked modified/staged files
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], capture_output=True, text=True)
    for f in result.stdout.strip().splitlines():
        f = f.strip()
        if not f or f.startswith(('spring/diff/', 'spring/tarball/', '.git/')) or is_key_like(f):
            continue
        action = "replace" if file_exists_in_head(f) else "create"
        files.append({"path": f, "action": action})

    # Untracked new files
    result = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], capture_output=True, text=True)
    for f in result.stdout.strip().splitlines():
        f = f.strip()
        if not f or f.startswith(('spring/diff/', 'spring/tarball/', '.git/')) or is_key_like(f):
            continue
        files.append({"path": f, "action": "create"})

    return files

def validate_message(msg: str) -> str:
    if not msg or len(msg.strip()) == 0:
        return "Local changes"
    msg = msg.strip()
    # Enforce absorber regex: ^[A-Za-z0-9][A-Za-z0-9 .,_:;()/+\-]{0,119}$
    if re.match(r'^[A-Za-z0-9][A-Za-z0-9 .,_:;()/+\-]{0,119}$', msg):
        return msg
    # Sanitize if needed
    sanitized = re.sub(r'[^A-Za-z0-9 .,_:;()/+\-]', '_', msg)
    sanitized = sanitized[:110]
    if not sanitized[0].isalnum():
        sanitized = 'X' + sanitized[1:]
    return sanitized

def generate_patch(message: str):
    drop_path = Path('spring/diff/drop')
    drop_path.mkdir(parents=True, exist_ok=True)
    if any(drop_path.glob('*.json')):
        print("Error: spring/diff/drop already contains .json files. Absorb or clear first.", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    clean_msg = validate_message(message)
    patch = {
        "format": "LS_JSON_PATCH_V1",
        "commit_message": clean_msg,
        "files": []
    }

    for item in get_changed_files():
        path = item["path"]
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                content = fh.read()
            patch["files"].append({
                "path": path,
                "action": item["action"],
                "content": content
            })
        except Exception as e:
            print(f"Warning: Could not read {path}: {e}", file=sys.stderr)

    if not patch["files"]:
        print("No changes detected.", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(patch, indent=2))
    return patch

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else f"Local changes {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    generate_patch(msg)
