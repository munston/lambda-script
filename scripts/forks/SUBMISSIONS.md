# forks submission objects

Submission objects are the canonical way to preserve agent work while keeping `agents/<name>` lanes syncable with `main`.

The intended invariant is:

```text
main = accepted source of truth
agents/<name> = clean lane that can track main
.forks/submissions/<name>.json = pending patch intent
.forks/worktrees/<name>-candidate = replayed proof surface
.forks/receipts/<name>.json = verification authority
```

A lane may temporarily contain work during bootstrapping. The first step is to capture that work into a submission object. After capture, the lane can be returned to current `main` only when the tool proves the lane still points at the captured source commit. This prevents uncaptured work from being discarded.

The submission object records the agent, source ref, source commit, base snapshot, current-main snapshot at capture time, changed files, patch text, and patch hash. It also writes a compatibility patch for the existing replay and verification machinery.

Replay applies the saved patch to current `origin/main` inside a disposable candidate worktree. If main has moved since capture, replay requires an explicit stale-base replay option. The lane itself does not need to remain ahead while this happens.

Verification runs inside the candidate worktree and writes a receipt. The receipt is the authority for the candidate identity. A candidate whose commit or tree changed after verification must be replayed and verified again.

The final accepted path is:

```text
capture work as submission
optionally return the agent lane to current main
replay submission onto current main
verify candidate
advance main from the verified candidate or emit a contents ship plan
```

This model replaces branch trust with submission trust. Branches remain lanes; submissions carry pending intent; candidates provide the proof surface.
