# forks model notes

`forks` is a replay-and-attest tool for multi-agent Git work. It should not treat an agent branch as safe merely because the branch exists.

The agent lane preserves intent. The candidate workspace is the proof surface. `main` remains the source of truth.

## Terms

`base snapshot` means the `origin/main` commit and tree where the agent work originally began.

`patch intent` means the agent lane diff plus metadata: agent name, branch, base commit, base tree, changed files, source head, source tree, and patch text.

`current main snapshot` means the latest fetched `origin/main` at staging time.

`candidate snapshot` means current main with patch intent applied on top.

`verification receipt` means the candidate commit, candidate tree, command, exit code, time, ahead/behind state, and bounded output.

`submit freshness` means that immediately before submit, current `origin/main` is still an ancestor of candidate `HEAD` and the candidate is zero commits behind current `origin/main`.

`lane preservation` means ordinary sync does not discard unique agent work.

## Core rule

```text
ready candidate = candidate snapshot + passing verification receipt + fresh main ancestry
```

A branch name alone is not enough. A patch file alone is not enough. A verification run from the wrong checkout is not enough.

## Expected flow

```text
agents/eddy
  -> forks diff eddy
  -> .forks/patches/eddy.json
  -> forks stage eddy
  -> .forks/worktrees/eddy-candidate/
  -> .forks/candidates/eddy.json
  -> forks verify eddy
  -> .forks/receipts/eddy.json
  -> forks submit eddy
```

The candidate can be rebuilt freely. The agent lane should be preserved during normal sync.

## Refusal cases

If main moved after staging, submit refuses and the user reruns stage and verify.

If the patch no longer applies, stage refuses and the lane must be reworked.

If the candidate changed after verify, submit refuses and verify must be rerun.

If a blocked stale path appears, stage or verify refuses unless an override is explicitly supplied.

If an agent lane has unique work and is behind main, ordinary sync refuses. Use diff, stage, and replay instead.

## Moderator reading

`forks status` is a routing view, not a submit decision. Submit eligibility comes from candidate metadata and verification receipt freshness.
