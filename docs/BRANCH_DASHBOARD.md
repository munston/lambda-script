# Branch race dashboard

LambdaScript includes a local read-only dashboard for viewing racing agent branches against `origin/main`.

Launch from the repository root:

```bat
branch-dashboard.bat
```

Or directly:

```sh
python scripts/web/branch_dashboard.py
```

Then open:

```text
http://localhost:8766
```

The dashboard shows:

- the current `origin/main` commit and tree hash
- visible agent branches such as `agent/ed`, `agent/edd`, and `agent/eddy`
- ahead and behind counts versus `origin/main`
- branch head hashes and tree hashes
- files changed by each branch relative to `origin/main`
- potential file collisions where multiple branches touch the same path

Use **Fetch origin then refresh** before deciding whether a branch is current. A branch with `behind > 0` is stale and should be rebased or reapplied before submission. A branch with `ahead > 0` and `behind = 0` is based on current `origin/main`, although it still needs normal verification before submission.

This dashboard does not submit, merge, rebase, or modify branches. It is an inspection interface only.
