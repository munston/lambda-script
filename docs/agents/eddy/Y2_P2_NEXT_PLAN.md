# Eddy next-turn plan after unsupported backend errors

Status: preliminary plan for the next implementation pass.

The current pass makes unsupported backend expression forms fail clearly instead of emitting placeholder text. The next backend-local pass should address the concrete parity bug identified in `docs/core/C1_BACKEND_PARITY_GAPS.md`:

```text
Y2-P2: map Haskell not-equal emission from `!=` to `/=`.
```

## Intended scope

This should remain an Eddy backend patch. It should not alter parser syntax, checker semantics, language admission policy, replay workflow, or post-C1 feature choice.

## Preliminary implementation plan

```text
1. Re-read `glc/src/codegen/haskell.ts`, `glc/src/parser/parser.ts`, `glc/src/core/check.ts`, and `glc/test/smoke.ts` from the current target.
2. Confirm that `!=` is parsed as a binary operator and type-checked in the equality family.
3. Add a small Haskell operator mapping helper, likely `mapHaskellBinaryOperator`.
4. Emit `/=` when the LambdaScript operator is `!=`; otherwise preserve the existing operator spelling.
5. Add a narrow positive smoke fixture or inline assertion only if it can stay backend-local.
6. Keep the TypeScript emitter unchanged because `!=` is target-valid there.
7. Submit as one small JSON patch if the code and fixture change remain compact.
```

## Stop condition

If Ed does not want `!=` admitted in C1, stop and convert the finding into an admission question instead of patching. If Edd requires a different fixture location, keep the emitter patch separate from fixture integration.
