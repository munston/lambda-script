# Eddy Y3-P1 next plan: TypeScript emission stability notes

Status: preliminary planning note for the next implementation turn.

The next likely Eddy task is Y3-P1: produce a TypeScript emission stability pass after the foreign-call backend boundary has been made explicit.

## Scope

This task should remain backend-local. It should inspect TypeScript output shape for the current C1 constructs and decide whether any formatting or target-shape issue should become a narrow patch.

## Inputs to inspect

```text
glc/src/codegen/typescript.ts
glc/test/smoke.ts
examples/core/core0_values.ls
examples/core/core0_ffi.ls
examples/core/core1_functions.ls
examples/core/core1_let.ls
examples/core/core1_pure_calls.ls
```

## Questions

```text
1. Are emitted TypeScript snippets stable enough for snapshot fixtures?
2. Are IIFE let expressions readable and deterministic?
3. Are foreign-runtime imports emitted only when required?
4. Are top-level direct foreign calls visibly runtime-bound?
5. Are function declarations and constants emitted in source order after the foreign declaration prelude?
```

## Expected output

Preferred output is documentation-only unless a very small emitter-local formatting fix is obvious:

```text
docs/core/C1_TYPESCRIPT_EMISSION_STABILITY.md
```

The next turn should avoid parser changes, checker changes, replay-tooling changes, or post-C1 feature selection.
