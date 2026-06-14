# Gizmo provision plans

A gizmo can import toolchains or programs from another gizmo without owning their source. The provision plan is the declarative bridge between the manifest and later sandbox execution.

The current command is intentionally non-mutating:

```bat
cd tools\gizmo
npm run build
node dist\src\cli.js provision-plan ..\..\examples\gizmos\metrics.gizmo.json
node dist\src\cli.js provision-plan ..\..\examples\gizmos\metrics.gizmo.json --out ..\..\runs\gizmo\metrics-provision-plan.json
```

The plan lists every import with:

```text
source gizmo/gadget
mount location
mode
target ref
allowed commands
write policy
whether the mounted import is mutable
```

For the metrics gizmo, `lambdascript/core` is imported as a read-only toolchain. That means metrics gadgets may use declared commands such as `forks`, `glc`, and `gizmo`, while source changes to those tools must be made through the `lambdascript/core` gadget process.

This patch only emits a plan. It does not copy files, create mounts, or execute commands. Later gizmo runner patches will consume this plan to build restricted workspaces.
