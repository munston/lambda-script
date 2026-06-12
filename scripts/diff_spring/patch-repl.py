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
        # MSYS2 path conversion
        try:
            converted = subprocess.check_output(['cygpath', '-w', root], text=True).strip()
            root = converted
        except Exception:
            pass
        return root
    except Exception:
        print("Error: Not in a git repository.")
        sys.exit(1)

def main():
    root = get_repo_root()
    os.chdir(root)

    print("\n=== Lambda-Script Diff Spring REPL (Grok) ===")
    print("Paste full LS_JSON_PATCH_V1 JSON, then press Enter once.")
    print("The REPL will auto-detect when the JSON object is complete.")
    print("Type 'exit' or 'quit' on a new empty line to quit.\n")

    drop_dir = Path('spring/diff/drop')
    drop_dir.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            print("Waiting for JSON patch...")
            lines = []
            valid_patch = None

            while True:
                line = input()
                stripped = line.strip()

                if stripped.lower() in ('exit', 'quit') and not lines:
                    print("Goodbye.")
                    return

                lines.append(line)

                json_text = '\n'.join(lines)
                try:
                    parsed = json.loads(json_text)
                    if isinstance(parsed, dict) and parsed.get('format') == 'LS_JSON_PATCH_V1':
                        valid_patch = parsed
                        break
                    else:
                        print("Error: JSON parsed but is not a valid LS_JSON_PATCH_V1 object")
                        lines = []
                        break
                except json.JSONDecodeError:
                    continue  # incomplete JSON

            # Valid patch received
            if valid_patch is None:
                continue

            if any(drop_dir.glob('*.json')):
                print("Error: spring/diff/drop already contains a .json file. Absorb or clear first.")
                continue

            timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
            filename = f"grok-patch-{timestamp}.json"
            filepath = drop_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json.dumps(valid_patch, indent=2))

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
            lines = []

if __name__ == "__main__":
    main()
