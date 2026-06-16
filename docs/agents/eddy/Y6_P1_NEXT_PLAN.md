# Eddy next turn plan — C1 backend executable snapshots

Status: preliminary implementation plan.

Replay status: this advisory Eddy planning note is now carried by an explicit `LS_FORK_JSON_PATCH_V1` submission so gadget replay history can account for it. It does not change compiler semantics, tests, scripts, examples, accelerator state, replay ledgers, or core docs.

The next C1 step should continue concrete compiler completion rather than meta-documentation. If this Haskell multi-string FFI patch lands, the next useful Eddy pass is to begin snapshot-style backend fixture stabilization for existing Core-1 examples.

Planned task:

```text
Y6-P1: Add emitted-output snapshot fixtures for one small Core-1 example.
```

Candidate target:

```text
examples/core/core1_functions.ls
```

Implementation outline:

```text
1. Inspect current emitted TypeScript and Haskell output for the selected fixture.
2. Add target snapshot files under glc/test/snapshots or an existing fixture directory if one is present.
3. Extend smoke.ts with a compact snapshot comparison helper.
4. Keep the patch backend-test-only: no parser, checker, workflow, or language-surface changes.
5. Use the snapshot to stabilize emitted output for recursive functions, if expressions, and basic numeric operations.
```

Stop conditions:

```text
- If Edd has introduced a different fixture/snapshot convention, follow that instead.
- If snapshot files make the quick profile too heavy, reduce to one fixture.
- If emitted output exposes language-admission ambiguity, route to Ed.
```
