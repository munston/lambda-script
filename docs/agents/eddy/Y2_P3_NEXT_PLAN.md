# Eddy next-turn plan after Haskell not-equal parity fix

Status: preliminary plan for the next implementation pass.

This pass fixes the backend-local Haskell parity gap where LambdaScript `!=` previously emitted as raw `!=` instead of Haskell `/=`. The next backend-local pass should address the remaining foreign-call boundary identified in `docs/core/C1_BACKEND_PARITY_GAPS.md`.

```text
Y2-P3: classify and narrow the foreign-call backend boundary.
```

## Intended scope

This should stay within Eddy's backend/executable-surface lane. It should not change language admission, add new FFI syntax, alter checker semantics, or define Edd's verification policy.

## Preliminary implementation plan

```text
1. Re-read TypeScript and Haskell emitters from the current gadget target.
2. Re-read `examples/core/core0_ffi.ls` and the relevant smoke expectations.
3. Confirm the current special case: direct top-level declarations that call a foreign import receive runtime/IO-aware emission.
4. Confirm the current boundary: generic call emission is not runtime-aware in TypeScript and not IO-aware in Haskell.
5. Decide whether the next patch should be documentation-only or a small explicit backend guard.
6. Prefer documentation-only if the boundary is an admission/checker question for Ed.
7. Prefer a guard only if an emitted target program would currently be misleading for a source form already admitted in C1.
```

## Stop condition

Stop and ask Ed if this becomes a question of whether foreign calls are admitted inside pure functions. Stop and ask Edd if the useful output is a fixture/profile change rather than a backend-local patch.
