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

Payload path:

```text
forks/replay-ledger/payloads/<first-two-sha-chars>/<json_patch_sha256>.json
```

Ledger entry fields include:

```text
sequence
agent
target
title
json_patch_sha256
payload_path
file_count
file_fingerprints
target_ref_at_capture
created_at
```

The payload object has format:

```text
LS_FORK_REPLAY_PAYLOAD_V1
```

and contains the original JSON patch payload. The payload file is content-addressed by `json_patch_sha256`, so a replay executor can retrieve the exact submitted JSON diff after the branch has been rewound.

This gives the synchronizer two distinct checks:

```text
json_patch_sha256
  Detects whether the requested JSON diff payload changed and locates the durable payload object.

patch_sha256
  Detects whether the resulting committed Git diff changed.

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
verify that every pending entry has a valid payload object
rewind branch to current origin/main
replay entries after the matching prefix from forks/replay-ledger/payloads/
verify the rebuilt branch
push refreshed branch with --force-with-lease
```
