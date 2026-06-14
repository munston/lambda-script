# Merlin gizmo bootstrap

Merlin is developed in its own gizmo for now.

Initial branch setup:

```bat
forks.bat gadget-init merlin core
```

The first bootstrap patch may be landed with the target-ref JSON route because the manifest profile does not exist on the branch until this patch lands:

```bat
forks.bat land-json-file --target-ref origin/gadgets/merlin/core/main eddy C:\Users\guyas\Downloads\merlin_core_bootstrap_patch.json
forks.bat gadget-sync-all merlin core
```

After the bootstrap patch has landed, normal gadget landing is available:

```bat
forks.bat gadget-land-json-file merlin core eddy patch.json
forks.bat gadget-land-json-file --profile full merlin core eddy patch.json
```

Merlin stays separate from the LambdaScript gizmo until an explicit tooling integration path imports it as a protected tool or promotes it into a shared toolchain.
