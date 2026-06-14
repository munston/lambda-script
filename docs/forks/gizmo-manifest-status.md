# Gizmo manifest status

`tools/gizmo` validates and summarizes gizmo manifests.

It now understands the branch model used by forks-backed gadgets:

```text
target_ref
integration_branch
agent_branch_template
owned_paths
verification_profiles
imports
connections
```

Run from `tools/gizmo` after building:

```bat
npm run build
node dist/src/cli.js validate ..\..\examples\gizmos\metrics.gizmo.json
node dist/src/cli.js status ..\..\examples\gizmos\metrics.gizmo.json
node dist/src/cli.js branches ..\..\examples\gizmos\metrics.gizmo.json
```

`status` emits a JSON summary of gadgets, imports, and connections. `branches` prints the target refs and branch templates in an operator-readable form.

The gizmo tool does not inspect Git state yet. Git branch state is still handled by:

```bat
forks.bat gadget-status metrics image-metrics
forks.bat gadget-status metrics text-metrics
forks.bat gadget-status lambdascript core
```

This keeps manifest validation separate from Git operations while preserving a shared branch vocabulary.
