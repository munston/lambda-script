#!/usr/bin/env python3

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import subprocess

def get_repo_root():
    try:
        root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
        # MSYS2 path conversion (safer)
        try:
            converted = subprocess.check_output(['cygpath', '-w', root], text=True).strip()
            root = converted
        except Exception:
            pass  # Not on MSYS2 or cygpath failed
        return root
    except Exception:
        print("Error: Not in a git repository.")
        sys.exit(1)

def main():
    root = get_repo_root()
    os.chdir(root)

    print("\n=== Lambda-Script Diff Spring REPL (Grok) ===")
    print("Paste full LS_JSON_PATCH_V1 JSON, then type LS_JSON_END on a new line.")
    print("Type 'exit' or Ctrl+C to quit.\n")

    drop_dir = Path('spring/diff/drop')
    drop_dir.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            print("Waiting for JSON patch...")
            lines = []
            while True:
                line = input()
                if line.strip() == 'LS_JSON_END':
                    break
                if line.strip().lower() in ('exit', 'quit'):
                    print("Goodbye.")
                    return
                lines.append(line)

            json_text = '\n'.join(lines)
            patch = json.loads(json_text)

            if patch.get('format') != 'LS_JSON_PATCH_V1':
                print("Error: Not a valid LS_JSON_PATCH_V1")
                continue

            if any(drop_dir.glob('*.json')):
                print("Error: spring/diff/drop already contains a .json file. Absorb or clear first.")
                continue

            timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
            filename = f"grok-patch-{timestamp}.json"
            filepath = drop_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json.dumps(patch, indent=2))

            print(f"✅ Saved: {filepath}")

            print("Running absorb-and-ship...")
            result = subprocess.run(['bash', 'scripts/diff_spring/absorb-and-ship.sh'], check=False)
            
            if result.returncode == 0:
                print("✅ Successfully absorbed and pushed.")
            else:
                print(f"❌ Absorption failed (code {result.returncode}). JSON left in drop folder.")

        except KeyboardInterrupt:
            print("\nExiting REPL.")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
