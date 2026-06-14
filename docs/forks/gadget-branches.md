# Gadget branch commands

Gadget branches give each gizmo gadget its own forks-compatible integration branch on GitHub.

The integration branch naming convention is:

```text
gadgets/<gizmo>/<gadget>/main
```

Each agent lane for that gadget is:

```text
agents/<agent>/gadgets/<gizmo>/<gadget>
```

## Create a gadget lane set

```bat
forks.bat gadget-init metrics image-metrics
forks.bat gadget-init metrics text-metrics
forks.bat gadget-init lambdascript core
```

By default this creates the remote gadget integration branch from `origin/main`, then creates remote and local agent lanes for `ed`, `edd`, `eddy`, and `guy`.

To create only the integration branch:

```bat
forks.bat gadget-init metrics image-metrics --no-agents
```

## Inspect a gadget

```bat
forks.bat gadget-status metrics image-metrics
forks.bat gadget-status metrics image-metrics --json
```

Status is computed against the gadget integration target, not repository `main`.

## Sync gadget agent lanes

```bat
forks.bat gadget-sync metrics image-metrics eddy
forks.bat gadget-sync-all metrics image-metrics
```

Sync refuses when an agent lane has unique work ahead of the gadget integration branch. It only updates missing, even, or behind-only lanes.

## Land a patch to a gadget branch

After a gadget integration branch exists, use the target-ref JSON landing path:

```bat
forks.bat land-json-file --target-ref origin/gadgets/metrics/image-metrics/main eddy patch.json
```

This pushes to `gadgets/metrics/image-metrics/main`, not repository `main`.

Repository-level sync is intentionally skipped for non-main targets. Use `gadget-sync-all` to sync the agent lanes for that gadget.
