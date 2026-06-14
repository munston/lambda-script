# Gadget verification profiles

Gadget JSON landing now uses verification profiles from the gizmo manifest.

For a gadget landing, the default profile is `quick`:

```bat
forks.bat gadget-land-json-file metrics image-metrics eddy patch.json
```

This resolves the target ref from the gadget branch model, then looks in:

```text
examples/gizmos/<gizmo>.gizmo.json
gadgets.<gadget>.verification_profiles.quick
```

and runs those commands in the imported candidate worktree before the dry-run push.

Use a named profile explicitly:

```bat
forks.bat gadget-land-json-file --profile full metrics image-metrics eddy patch.json
forks.bat gadget-land-json-file --profile gizmo lambdascript core eddy patch.json
```

`--full` is now interpreted as the manifest `full` profile when that profile exists. If a manifest profile does not exist, the old `verify.bat` fallback is retained for repository-style use.

Current profiles:

```text
lambdascript/core quick  = Python syntax check for forks scripts
lambdascript/core gizmo  = tools/gizmo build and smoke test
lambdascript/core full   = verify.bat

metrics/image-metrics quick = compile Python image-metrics package
metrics/image-metrics full  = image-metrics smoke test

metrics/text-metrics quick = TypeScript build
metrics/text-metrics full  = TypeScript tests
```

This keeps verification local to the gadget under development instead of running the whole LambdaScript compiler suite for every documentation or metrics patch.
