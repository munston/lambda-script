# Gizmo branch model

A gizmo is a named development environment containing one or more gadgets. A gadget is a separately developed program or tool surface. Forks remains the patch, replay, verification, and submission mechanism; gizmos add a higher-level namespace for developing several related gadgets without collapsing their source ownership.

## Core objects

`main` is the accepted repository truth.

A `gizmo` is a named composition environment. It owns a manifest, one or more writable gadgets, and any read-only imports it provisions from other gizmos.

A `gadget` is a writable development unit inside a gizmo. Each gadget has its own integration branch, agent lanes, owned paths, verification profile, and command surface.

An `import` is a provisioned dependency from another gizmo. Imports may expose commands and artefacts, but they are modification-protected unless the current gizmo also owns that gadget.

## Branch convention

Repository-level work continues to target `origin/main`.

Gadget-level work targets a gadget integration branch:

```text
gadgets/<gizmo>/<gadget>/main
```

Each agent lane for a gadget follows:

```text
agents/<agent>/gadgets/<gizmo>/<gadget>
```

Examples:

```text
gadgets/lambdascript/core/main
agents/eddy/gadgets/lambdascript/core

gadgets/metrics/image-metrics/main
agents/eddy/gadgets/metrics/image-metrics

gadgets/metrics/text-metrics/main
agents/eddy/gadgets/metrics/text-metrics
```

## Forks compatibility

Every gadget source change must be representable as a forks submission against that gadget's target integration ref. The existing repository-level path is therefore a special case:

```text
target_ref = origin/main
```

A gadget-level path uses:

```text
target_ref = origin/gadgets/<gizmo>/<gadget>/main
```

A forks submission for a gadget must record at least:

```json
{
  "target_ref": "origin/gadgets/metrics/image-metrics/main",
  "gizmo": "metrics",
  "gadget": "image-metrics"
}
```

All existing forks invariants still apply: patch intent is replayed onto the current target ref, verification writes a receipt tied to candidate commit and tree, submit refuses stale candidates, and agent lanes sync only when safe.

## Promotion

Gadget landing and repository promotion are separate operations.

Agent patch to gadget branch:

```text
agent JSON patch -> gadget candidate -> gadget verification receipt -> push to gadgets/<gizmo>/<gadget>/main -> sync gadget agent lanes
```

Gadget branch to repository main:

```text
gadget integration branch -> repository candidate -> repository verification receipt -> push to main -> sync repository agent lanes
```

This lets several agents collaborate on a single gadget while keeping that gadget separate from other gadgets and from repository `main`.

## Connected gizmos

A gizmo can import a gadget from another gizmo as a protected toolchain. Imported gadgets may expose declared commands and artefacts. The importing gizmo may execute those commands through declared capabilities, but it may not mutate the imported gadget's source.

For example, the `metrics` gizmo may import `lambdascript/core` as a read-only toolchain so that image and text processors can call `forks`, `glc`, or future gizmo tools. Changes to that toolchain must still go through the `lambdascript` gizmo's own gadget process.

The invariant is:

```text
A connected gizmo may execute imported tools through declared capabilities, but may only modify gadgets it owns.
```
