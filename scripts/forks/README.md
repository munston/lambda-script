# forks

Repository tooling for coordinating side-lane agent branches.

`forks` keeps `main` as the source of truth while agents work in separate lanes:

```text
agents/ed
agents/edd
agents/eddy
agents/guy
```

The basic safety rule is that an agent lane can be worked independently, but a candidate should be staged, verified, and checked against current `origin/main` before it is allowed to advance `main`.

For the replayable submission-object model, see `SUBMISSIONS.md`.

## Existing patch workflow

The original patch-oriented workflow remains available through `forks.bat`:

```bat
forks.bat status
forks.bat diff eddy
forks.bat stage eddy
forks.bat verify eddy
forks.bat submit eddy --dry-run
forks.bat submit eddy
```

This path exports a patch, stages it in `.forks/worktrees/<agent>-candidate/`, writes candidate metadata, writes a verification receipt, and refuses stale or unverified submissions.

## Submission-object amalgamation

The guarded amalgamation workflow applies all known replay history and direct lane work for each agent, one agent at a time, onto the moving main.

Plan first:

```bat
forks.bat amalgamate-all
```

Apply after inspecting the plan:

```bat
forks.bat amalgamate-all --apply
```

For each target agent, `amalgamate-all --apply` now performs two recovery passes:

```text
1. Replay-ledger pass:
   - inspect the agent lane replay ledger against current main;
   - if the lane has replay-ledger entries missing from main, apply those JSON payloads first with replay-sync;
   - this happens even when main has newer entries from other agents, provided there is no fingerprint divergence or missing payload.

2. Direct-lane pass:
   - re-resolve the lane after ledger replay;
   - if unique lane work remains, check whether a submission object already captures the lane head;
   - if not, capture the current lane diff into .forks/submissions/<agent>.json;
   - destructively sync the captured lane only after sync-captured-lane proves the lane head still equals the captured source commit;
   - replay, verify, dry-run submit, and submit that direct diff.
```

After each agent submit, `origin/main` is fetched and the next agent is replayed against the newly advanced main.

After all target agents have been processed, `amalgamate-all --apply` is terminal:

```text
sync every target agent lane to the final advanced main
assert that each target lane is even with main
assert that replay-plan shows no outstanding replay-needed entries for those lanes
```

This supports both allowed agent behaviours:

```text
agent updates their lane directly
agent records JSON/diff patches while updating their lane
```

`main` is never rewound by this command. Agent lanes may be rewound after their work is captured or replayed. Main advances only through replay, verification, and submit.

Useful options:

```bat
forks.bat amalgamate-all --agents ed edd eddy
forks.bat amalgamate-all --verify-command verify.bat
forks.bat amalgamate-all --apply
forks.bat amalgamate-all --apply --backend contents
forks.bat amalgamate-all --apply --skip-final-sync
forks.bat amalgamate-all --apply --skip-final-assert
```

The ordinary operator command is just:

```bat
forks.bat amalgamate-all --apply
```

No additional sync command is expected afterward for the target agent lanes.

## Workflow runner layer

The workflow runner adds named operator workflows over the same agent model. It is intended to reduce repeated command sequences, not to weaken the safety model.

The current workflow commands are:

```bat
forks.bat plan verify-agent eddy
forks.bat verify-agent eddy
forks.bat plan land-agent eddy
forks.bat land eddy
forks.bat sync-all
```

`plan` is non-mutating. It prints the bound workflow steps and exits without fetching, staging, verifying, syncing, or pushing.

`verify-agent` stages an ahead-only agent branch directly into a candidate worktree and runs the verifier there. It does not advance `main`.

`land` stages, verifies, then attempts a normal fast-forward advance of `main` from the verified candidate. It should be used only after the planned workflow has been inspected and the branch is known to be the intended submission target.

`sync-all` syncs lanes that have no unique work. It refuses to discard unique work.

## Ahead-only requirement

The direct workflow runner currently accepts only ahead-only branches for verification or landing. A branch that is behind or diverged must be reconciled through the patch/replay path before it is landed.

This is deliberate. The workflow runner is for the simple safe case:

```text
origin/main is an ancestor of agents/<name>
agents/<name> has commits ahead of origin/main
agents/<name> has zero commits behind origin/main
```

## Generated state

Generated state is written under `.forks/`:

```text
.forks/worktrees/
.forks/candidates/
.forks/receipts/
.forks/workflow-runs/
```

This directory should remain untracked.

## Review checklist

Before using `land`, run:

```bat
forks.bat status
forks.bat plan land-agent <agent>
forks.bat verify-agent <agent>
```

Then inspect the relevant branch diff. If the branch is still the intended submission target and verification passes, `forks.bat land <agent>` may be used.

If `origin/main` moves between planning, verification, and landing, the workflow refuses and the candidate must be rebuilt.
