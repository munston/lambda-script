# Gizmo command calls

`tools/gizmo` can build command plans from a manifest-declared local gadget command or from an imported toolchain command.

## Local gadget calls

The default local gadget call is non-executing. It validates the manifest, checks the gadget and command name, verifies that every template placeholder has exactly one provided argument, rejects unused arguments, quotes safe argument values, and prints a command plan.

Example:

```bat
cd tools\gizmo
npm run build
node dist\src\cli.js call ..\..\examples\gizmos\metrics.gizmo.json image-metrics analyze --arg image=sample.png --arg out=out-dir
```

The output has format:

```text
LS_GIZMO_COMMAND_PLAN_V1
```

and includes the original template, rendered command, arguments, cwd, and whether execution was requested.

Execution is opt-in for local gadget commands:

```bat
node dist\src\cli.js call ..\..\examples\gizmos\metrics.gizmo.json image-metrics analyze --arg image=sample.png --arg out=out-dir --exec
node dist\src\cli.js call ..\..\examples\gizmos\metrics.gizmo.json image-metrics analyze --arg image=sample.png --arg out=out-dir --exec=true
node dist\src\cli.js call ..\..\examples\gizmos\metrics.gizmo.json image-metrics analyze --arg image=sample.png --arg out=out-dir --exec=false
```

Invalid execution values such as `--exec=maybe` are rejected.

## Workspace plans

Workspace plans translate provisioned imports into planned workspace mount locations without copying files or executing commands.

Example:

```bat
node dist\src\cli.js workspace-plan ..\..\examples\gizmos\metrics.gizmo.json --root workspace --out ..\..\runs\gizmo\metrics-workspace-plan.json
```

The output has format:

```text
LS_GIZMO_WORKSPACE_PLAN_V1
```

and lists each import's source, declared mount, workspace path, mutability, write policy, and planned action.

## Imported command plans

Imported command plans are intentionally non-executing. They resolve a command name through the manifest import allow-list and print a command plan with import metadata, but they do not mount workspaces, copy files, or run the imported command.

Example:

```bat
cd tools\gizmo
npm run build
node dist\src\cli.js import-call ..\..\examples\gizmos\metrics.gizmo.json lambdascript-core gizmo
node dist\src\cli.js import-call ..\..\examples\gizmos\metrics.gizmo.json lambdascript-core forks --exec=false
```

The resulting plan has:

```text
scope: import
execute: false
source: <from_gizmo>/<from_gadget>
mount: <declared mount>
mode: read-only | pinned | copy
target_ref: <declared target ref>
write_policy: deny | copy-on-write | allow
```

Imported command execution is refused for now:

```bat
node dist\src\cli.js import-call ..\..\examples\gizmos\metrics.gizmo.json lambdascript-core gizmo --exec
```

Imported command arguments are also refused for now. Argument binding, workspace mounting, and controlled import execution are later runner layers. The current import-call surface is a planning and validation step only.
