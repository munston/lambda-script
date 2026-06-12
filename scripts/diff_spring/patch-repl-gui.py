#!/usr/bin/env python3
"""
GUI Wrapper for Lambda-Script Diff Spring

This is a frontend that makes it easier to paste JSON patches.
It still uses the existing absorb-and-ship.sh for safety and logic.
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

def get_repo_root():
    try:
        root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
        try:
            converted = subprocess.check_output(['cygpath', '-w', root], text=True).strip()
            root = converted
        except Exception:
            pass
        return root
    except Exception:
        messagebox.showerror("Error", "Not inside a git repository.")
        sys.exit(1)

class PatchReplGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Grok Patch Repl (GUI Wrapper)")
        self.root.geometry("850x650")

        self.repo_root = get_repo_root()
        os.chdir(self.repo_root)

        self.drop_dir = Path("spring/diff/drop")
        self.drop_dir.mkdir(parents=True, exist_ok=True)

        # Header
        tk.Label(root, text="Grok Patch Repl - GUI Wrapper", font=("Segoe UI", 16, "bold")).pack(pady=10)
        tk.Label(root, text="This GUI uses your existing absorb-and-ship.sh for safety", 
                font=("Segoe UI", 9), fg="gray").pack()

        # JSON Input
        tk.Label(root, text="Paste LS_JSON_PATCH_V1 JSON here:", font=("Segoe UI", 10)).pack(anchor="w", padx=15, pady=(15, 5))

        self.json_input = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=22, font=("Consolas", 10))
        self.json_input.pack(padx=15, pady=5, fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Submit Patch", command=self.submit_patch, width=18).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Clear", command=lambda: self.json_input.delete("1.0", tk.END), width=12).pack(side=tk.LEFT, padx=8)

        # Log
        tk.Label(root, text="Log:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15)
        self.log = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=10, font=("Consolas", 9), state="disabled")
        self.log.pack(padx=15, pady=5, fill=tk.X)

        self.log_message("GUI ready. Paste a JSON patch and click Submit.")

    def log_message(self, msg):
        self.log.config(state="normal")
        self.log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    def submit_patch(self):
        content = self.json_input.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "Please paste JSON first.")
            return

        try:
            patch = json.loads(content)
        except Exception as e:
            messagebox.showerror("JSON Error", str(e))
            return

        if not isinstance(patch, dict) or patch.get("format") != "LS_JSON_PATCH_V1":
            messagebox.showerror("Validation Error", "Not a valid LS_JSON_PATCH_V1 patch.")
            return

        if any(self.drop_dir.glob("*.json")):
            messagebox.showerror("Error", "spring/diff/drop already contains a JSON file.\nPlease absorb or clear it first.")
            return

        # Save the patch
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"grok-gui-{ts}.json"
        filepath = self.drop_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(patch, indent=2))

        self.log_message(f"Saved patch: {filename}")

        # Run existing absorber
        self.log_message("Running absorb-and-ship.sh...")
        try:
            result = subprocess.run(
                ["bash", "scripts/diff_spring/absorb-and-ship.sh"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                self.log_message("✅ Successfully absorbed and pushed!")
                messagebox.showinfo("Success", "Patch absorbed and pushed successfully!")
                self.json_input.delete("1.0", tk.END)
            else:
                self.log_message("❌ Absorption failed.")
                self.log_message(result.stdout + result.stderr)
                messagebox.showerror("Failed", result.stdout + result.stderr)
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = PatchReplGUI(root)
    root.mainloop()
