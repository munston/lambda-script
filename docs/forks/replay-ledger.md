# Replay ledger

The replay ledger is the committed index that makes destructive branch refresh safe.

Fast gadget landing saves time by skipping lane fan-out. That means a branch can be rewound to `main` and rebuilt from recent diffs. To do that automatically, the system needs a durable sequence of accepted diffs inside the branch tree itself.

Every future JSON submission appends one ledger entry before its candidate commit is created.

Ledger path:

```text
forks/replay-ledger/gadgets/<gizmo>/<gadget>/<agent>.json
```

Fallback path for non-gadget refs:

```text
forks/replay-ledger/refs/<target-ref>/<agent>.json
```

Entry fields include:

```text
sequence
agent
target
title
json_patch_sha256
file_count
file_fingerprints
target_ref_at_capture
created_at
```

The `json_patch_sha256` fingerprints the submitted JSON payload before the replay ledger is appended. The final `patch_sha256` in the submission object fingerprints the resulting Git diff, including the committed ledger update.

This gives the synchronizer two distinct checks:

```text
json_patch_sha256
  Detects whether the requested diff payload changed.

patch_sha256
  Detects whether the resulting committed diff changed.

sequence
  Gives the rewind/replay position for a given agent and target.
```

When a branch is destructively refreshed to `main`, a future replay command can compare the ledger already present in `main` with the ledger on the agent or gadget branch and apply only entries after the last matching sequence/fingerprint pair.

The intended full synchronization algorithm is:

```text
fetch origin
read main ledger for each target/agent
read branch ledger for each target/agent
find the longest matching prefix by sequence and json_patch_sha256
rewind branch to current origin/main
replay entries after the matching prefix
verify the rebuilt branch
push refreshed branch with --force-with-lease
```

The current patch installs the ledger and fingerprint machinery. The destructive multi-branch replay command should be built on top of these committed ledger files.
