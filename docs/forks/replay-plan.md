# Replay plan

`forks replay-plan` is a non-destructive planner for future full synchronization.

It reads committed replay ledgers from `origin/main` and from agent, gadget, and gadget-agent refs. It then computes the longest matching prefix between the two ledgers by:

```text
sequence
json_patch_sha256
```

The output reports which branch entries would need to be replayed after a destructive reset to `origin/main`.

Basic use:

```bat
forks.bat replay-plan
```

Inspect one ref:

```bat
forks.bat replay-plan origin/gadgets/lambdascript/core/main
forks.bat replay-plan agents/edd
```

Write a JSON plan:

```bat
forks.bat replay-plan --json --output .forks/replay-plan.json
```

Safety classifications:

```text
no-ledger
  The ref has no committed replay ledger.

no-replay-needed
  The branch ledger matches main's ledger for its known entries.

replay-needed
  The branch ledger has entries after the matching prefix. A future destructive sync would rewind to main and replay those entries.

main-has-unseen-ledger-entries
  Main has ledger entries missing from the branch after the matching prefix. This needs review before destructive replay.

fingerprint-divergence
  A sequence number is shared but json_patch_sha256 differs. This indicates changed or conflicting patch identity and must block destructive replay.
```

The planner performs no reset, no rebase, no apply, and no push. It only reads refs and prints a replay plan.

The next layer can use this plan to implement:

```text
fetch origin
find matching ledger prefix
rewind branch to origin/main
replay branch entries after the prefix
verify
push with --force-with-lease
```
