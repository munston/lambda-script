# forks submission objects

The preferred long-term model is that pending work is stored as a submission object rather than relying on an agent branch remaining ahead of `main`.

A submission object lives under:

```text
.forks/submissions/<agent>.json
```

It records:

```text
agent
agent branch
source ref
base snapshot
source snapshot
current main snapshot at capture
changed files
patch hash
patch payload
```

The important distinction is:

```text
agents/<name> = syncable source lane
.forks/submissions/<name>.json = pending work intent
.forks/worktrees/<name>-candidate = replayed proof surface
```

This lets an agent lane return to current `main` while the captured work remains available for replay.

## Capture

```bat
forks.bat capture eddy --from-ref agents/eddy
forks.bat submission-status eddy
```

`capture` writes both the submission object and a compatible patch file under `.forks/patches/`.

## Replay

```bat
forks.bat replay eddy --rebase-stale
```

`replay` restores the saved patch into the normal candidate-staging path and applies it to current `origin/main`.

After replay, the ordinary receipt-gated path is used:

```bat
forks.bat verify eddy
forks.bat submit eddy --dry-run
```

If the saved patch no longer applies, replay fails and the submission must be reconciled deliberately.

## Current limitation

This patch adds capture and replay. It does not yet add an automatic branch-freeing command. Branch freeing remains a deliberate operator step until the guarded command can be added without weakening the safety model.
