# Gizmo command calls

`tools/gizmo` can now build a command plan from a manifest-declared gadget command.

The default is non-executing. It validates the manifest, checks the gadget and command name, verifies that every template placeholder has exactly one provided argument, rejects unused arguments, quotes safe argument values, and prints a command plan.

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

Execution is opt-in:

```bat
node dist\src\cli.js call ..\..\examples\gizmos\metrics.gizmo.json image-metrics analyze --arg image=sample.png --arg out=out-dir --exec
```

This first runner only supports local gadget commands. Imported toolchain commands remain represented in the provision plan until workspace mounting and import command resolution are added.
