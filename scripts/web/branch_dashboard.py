#!/usr/bin/env python3
"""
Local branch race dashboard for LambdaScript.

Uses only the Python standard library. It reads the local Git repository and
shows the visible agent branches against origin/main.

Launch from the repository root with:
    python scripts/web/branch_dashboard.py

Then open:
    http://localhost:8766
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterable

PORT = 8766
PRIMARY_BRANCH = "origin/main"
BRANCH_PREFIXES = ("agent/", "agents/", "guy", "user/")
PINNED_BRANCHES = ("agent/ed", "agent/edd", "agent/eddy", "agents/eddy", "guy", "agent/guy")


def run_git(args: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def get_repo_root() -> Path:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("Error: not inside a git repository.", file=sys.stderr)
        raise SystemExit(1)
    return Path(proc.stdout.strip())


def git_text(args: list[str], root: Path, default: str = "") -> str:
    proc = run_git(args, root, check=False)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip()


def ref_exists(ref: str, root: Path) -> bool:
    proc = run_git(["rev-parse", "--verify", "--quiet", ref], root, check=False)
    return proc.returncode == 0


def short_sha(ref: str, root: Path) -> str:
    return git_text(["rev-parse", "--short", ref], root, default="")


def full_sha(ref: str, root: Path) -> str:
    return git_text(["rev-parse", ref], root, default="")


def tree_hash(ref: str, root: Path) -> str:
    return git_text(["rev-parse", f"{ref}^{{tree}}"], root, default="")


def list_remote_branches(root: Path) -> list[str]:
    text = git_text(["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"], root)
    names: set[str] = set()
    for raw in text.splitlines():
        if not raw or raw == "origin/HEAD" or raw == "origin/main":
            continue
        if raw.startswith("origin/"):
            name = raw[len("origin/"):]
        else:
            name = raw
        if name in PINNED_BRANCHES or name.startswith(BRANCH_PREFIXES):
            names.add(name)
    for name in PINNED_BRANCHES:
        if ref_exists(f"origin/{name}", root) or ref_exists(name, root):
            names.add(name)
    return sorted(names)


def ahead_behind(ref: str, root: Path) -> tuple[int, int]:
    text = git_text(["rev-list", "--left-right", "--count", f"{PRIMARY_BRANCH}...{ref}"], root)
    parts = text.split()
    if len(parts) != 2:
        return (0, 0)
    behind = int(parts[0])
    ahead = int(parts[1])
    return ahead, behind


def changed_files(ref: str, root: Path) -> list[dict[str, str]]:
    text = git_text(["diff", "--name-status", f"{PRIMARY_BRANCH}...{ref}"], root)
    files: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append({"status": parts[0], "path": parts[-1]})
    return files


def working_tree_state(root: Path) -> dict[str, object]:
    text = git_text(["status", "--porcelain=v1"], root)
    return {
        "clean": text == "",
        "entries": text.splitlines(),
    }


def classify_branch(ahead: int, behind: int) -> str:
    if ahead == 0 and behind == 0:
        return "even"
    if ahead > 0 and behind == 0:
        return "ready-base"
    if behind > 0:
        return "stale"
    return "unknown"


def collect_status(root: Path) -> dict[str, object]:
    branches = []
    touched: dict[str, list[str]] = {}
    main_ref_exists = ref_exists(PRIMARY_BRANCH, root)
    for name in list_remote_branches(root):
        remote_ref = f"origin/{name}"
        local_ref = name
        ref = remote_ref if ref_exists(remote_ref, root) else local_ref
        if not ref_exists(ref, root):
            continue
        ahead, behind = ahead_behind(ref, root)
        files = changed_files(ref, root)
        for item in files:
            touched.setdefault(item["path"], []).append(name)
        branches.append({
            "name": name,
            "ref": ref,
            "ahead": ahead,
            "behind": behind,
            "state": classify_branch(ahead, behind),
            "head": short_sha(ref, root),
            "head_full": full_sha(ref, root),
            "merge_base": short_sha(f"$(git merge-base {PRIMARY_BRANCH} {ref})", root),
            "tree": tree_hash(ref, root),
            "files": files,
        })
    collisions = [
        {"path": path, "branches": sorted(names)}
        for path, names in touched.items()
        if len(set(names)) > 1
    ]
    collisions.sort(key=lambda item: item["path"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "main": {
            "ref": PRIMARY_BRANCH,
            "exists": main_ref_exists,
            "head": short_sha(PRIMARY_BRANCH, root) if main_ref_exists else "",
            "head_full": full_sha(PRIMARY_BRANCH, root) if main_ref_exists else "",
            "tree": tree_hash(PRIMARY_BRANCH, root) if main_ref_exists else "",
        },
        "working_tree": working_tree_state(root),
        "branches": branches,
        "collisions": collisions,
    }


HTML_PAGE = r'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>LambdaScript Branch Race Dashboard</title>
<style>
body { font-family: system-ui, sans-serif; margin: 32px; background: #f7f7f8; color: #202124; }
h1 { margin-bottom: 4px; }
button { padding: 9px 14px; border: 1px solid #bbb; border-radius: 6px; background: white; cursor: pointer; }
button:hover { background: #eee; }
code { background: #eee; padding: 1px 4px; border-radius: 4px; }
table { width: 100%; border-collapse: collapse; background: white; margin-top: 16px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
th { background: #eee; }
.state { font-weight: 700; }
.ready-base { color: #126b25; }
.stale { color: #a33a00; }
.even { color: #555; }
.badge { display: inline-block; padding: 2px 6px; margin: 1px; border-radius: 999px; background: #eee; font-size: 12px; }
.panel { background: white; border: 1px solid #ddd; padding: 12px; margin-top: 16px; }
.small { color: #555; font-size: 13px; }
pre { white-space: pre-wrap; background: #fff; border: 1px solid #ddd; padding: 12px; }
</style>
</head>
<body>
<h1>LambdaScript Branch Race Dashboard</h1>
<p class="small">Read-only dashboard for agent branches against <code>origin/main</code>. Use Refresh to reread local Git state; use Fetch to update remote refs first.</p>
<button onclick="loadStatus(false)">Refresh</button>
<button onclick="loadStatus(true)">Fetch origin then refresh</button>
<div id="summary" class="panel">Loading...</div>
<div id="branches"></div>
<div id="collisions"></div>
<script>
async function loadStatus(doFetch) {
  const summary = document.getElementById('summary');
  summary.textContent = doFetch ? 'Fetching origin...' : 'Refreshing...';
  if (doFetch) {
    const fetched = await fetch('/api/fetch', {method: 'POST'});
    const fetchResult = await fetched.json();
    if (!fetchResult.ok) {
      summary.textContent = fetchResult.error || 'Fetch failed';
      return;
    }
  }
  const response = await fetch('/api/status');
  const data = await response.json();
  render(data);
}
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function render(data) {
  const stale = data.branches.filter(b => b.behind > 0).length;
  const ready = data.branches.filter(b => b.ahead > 0 && b.behind === 0).length;
  const clean = data.working_tree.clean ? 'clean' : 'dirty';
  document.getElementById('summary').innerHTML = `
    <div><b>origin/main:</b> <code>${esc(data.main.head)}</code></div>
    <div><b>main tree:</b> <code>${esc(data.main.tree)}</code></div>
    <div><b>branches:</b> ${data.branches.length}; <b>ready-base:</b> ${ready}; <b>stale:</b> ${stale}; <b>working tree:</b> ${clean}</div>
    <div class="small">Generated: ${esc(data.generated_at)}</div>`;
  let rows = data.branches.map(b => {
    const files = b.files.slice(0, 12).map(f => `<span class="badge">${esc(f.status)} ${esc(f.path)}</span>`).join(' ');
    const more = b.files.length > 12 ? `<span class="badge">+${b.files.length - 12} more</span>` : '';
    return `<tr>
      <td><code>${esc(b.name)}</code></td>
      <td class="state ${esc(b.state)}">${esc(b.state)}</td>
      <td>${b.ahead}</td>
      <td>${b.behind}</td>
      <td><code>${esc(b.head)}</code></td>
      <td><code>${esc(b.tree)}</code></td>
      <td>${files} ${more}</td>
    </tr>`;
  }).join('');
  document.getElementById('branches').innerHTML = `<table>
    <thead><tr><th>Branch</th><th>State</th><th>Ahead</th><th>Behind</th><th>Head</th><th>Tree</th><th>Files changed versus main</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="7">No agent branches found.</td></tr>'}</tbody>
  </table>`;
  let collisionRows = data.collisions.map(c => `<tr><td><code>${esc(c.path)}</code></td><td>${c.branches.map(b => `<span class="badge">${esc(b)}</span>`).join(' ')}</td></tr>`).join('');
  document.getElementById('collisions').innerHTML = `<div class="panel"><h3>Potential file collisions</h3><table>
    <thead><tr><th>Path</th><th>Branches</th></tr></thead>
    <tbody>${collisionRows || '<tr><td colspan="2">No overlapping changed paths among visible branches.</td></tr>'}</tbody>
  </table></div>`;
}
loadStatus(false);
</script>
</body>
</html>
'''


class BranchDashboardHandler(BaseHTTPRequestHandler):
    root: Path = Path.cwd()

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        if self.path == "/api/status":
            self._send_json(collect_status(self.root))
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/fetch":
            self.send_error(404)
            return
        proc = run_git(["fetch", "--prune", "origin"], self.root, check=False)
        if proc.returncode == 0:
            self._send_json({"ok": True, "output": proc.stdout + proc.stderr})
        else:
            self._send_json({"ok": False, "error": proc.stdout + proc.stderr})

    def _send_json(self, data: object) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))


def main() -> int:
    root = get_repo_root()
    os.chdir(root)
    BranchDashboardHandler.root = root
    print(f"Starting LambdaScript Branch Race Dashboard on http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    server = HTTPServer(("", PORT), BranchDashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
