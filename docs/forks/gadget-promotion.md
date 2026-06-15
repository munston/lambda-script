# Gadget promotion

`forks.bat gadget-promote` promotes a gadget integration branch back to repository `main`.

The source branch is resolved from the gizmo/gadget pair:

```text
origin/gadgets/<gizmo>/<gadget>/main
```

A promotion is allowed only when the gadget branch is ahead-only relative to `origin/main`. If repository `main` has moved independently, the command refuses and the gadget must be synchronized or rebased before promotion.

Dry run:

```bat
forks.bat gadget-promote lambdascript core --dry-run
```

Submit:

```bat
forks.bat gadget-promote lambdascript core
```

Verification defaults to the gadget's `quick` manifest profile. Use a stronger profile explicitly:

```bat
forks.bat gadget-promote lambdascript core --profile gizmo
forks.bat gadget-promote lambdascript core --full
```

On submit, the command performs:

```text
fetch origin
check gadget branch is ahead-only of origin/main
create disposable promotion worktree from the gadget branch
run the selected verification profile
recheck freshness
dry-run or push HEAD:main
sync repository agent lanes unless disabled
print repository status
```

Repository agent lane sync can be skipped:

```bat
forks.bat gadget-promote lambdascript core --no-repository-agent-sync
```

Targeted JSON patches can also control the same step:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "lambdascript",
    "gadget": "core",
    "promote": true,
    "sync": false,
    "repository_sync": false
  }
}
```

`sync` controls gadget-agent lane normalization after promotion. `repository_sync` controls repository-level agent lane synchronization after pushing `main`. They are deliberately separate because repository agent synchronization is often the slowest fan-out step.

This keeps development and promotion separate: ordinary work lands first to the gadget branch; only a verified promotion advances repository `main`.
