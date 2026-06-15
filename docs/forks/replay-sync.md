# Replay sync dry run

`forks replay-sync --dry-run` builds candidate replay worktrees without pushing or force-updating any branch.

It consumes the `replay-plan` result, then for each safe ref:

```text
create a disposable worktree at origin/main
load each pending JSON payload from the branch replay ledger
apply payload file operations
append/recreate the replay-ledger entry and payload object
commit each replay step locally
optionally run a verification command
report the candidate commit, changed files, and push ref
```

Basic use:

```bat
forks.bat replay-sync --dry-run --only-replay-needed
```

Write JSON:

```bat
forks.bat replay-sync --dry-run --only-replay-needed --json --output .forks/replay-sync-dry-run.json
```

Inspect one ref:

```bat
forks.bat replay-sync --dry-run origin/gadgets/lambdascript/core/main
```

Optional verification command:

```bat
forks.bat replay-sync --dry-run origin/gadgets/lambdascript/core/main --verify-command "python -m py_compile scripts/forks/forks.py scripts/forks/replay_sync.py"
```

This command is intentionally non-destructive. It creates worktrees under:

```text
.forks/replay-sync/
```

and does not push. The later `--apply` mode should reuse the same construction path, require successful verification, and push with `--force-with-lease`.
