# Gizmo provision plans

A gizmo can import toolchains or programs from another gizmo without owning their source. The provision plan is the declarative bridge between the manifest and later sandbox execution.

The provision-plan command is non-mutating:

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

For the metrics gizmo, `lambdascript/core` is imported as a read-only toolchain. That means metrics gadgets may plan declared commands such as `forks`, `glc`, and `gizmo`, while source changes to those tools must be made through the `lambdascript/core` gadget process.

Imported commands now have a separate non-executing command-plan surface:

```bat
node dist\src\cli.js import-call ..\..\examples\gizmos\metrics.gizmo.json lambdascript-core gizmo
```

This resolves the import and validates the command allow-list, producing an `LS_GIZMO_COMMAND_PLAN_V1` plan with `scope: import`. It does not create mounts or execute commands. Workspace mounting, argument binding for imported commands, and controlled import execution remain later runner layers.
