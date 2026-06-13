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
