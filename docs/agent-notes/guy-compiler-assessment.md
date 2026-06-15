# Guy lane note: LambdaScript compiler assessment

Status: provisional lane note, not a JSON submission, not durable ledger state.

Purpose: make the assistant/Guy-side assessment visible to other agents before consensus is attempted. This note is intentionally placed on `agents/guy` as working state and may be destructively overwritten by synchronization.

## Observed compiler surface

Current `glc` exposes parse, check, and emit commands. Emission targets are TypeScript and Haskell only; Python emission is rejected by design.

The implemented compiler surface appears broader than the older narrow Core-0 wording. The parser/checker/smoke path now covers typed function declarations, function signatures, parameters, binary operations, `if`, lexical `let`, pure calls, recursion examples, top-level values, literals, identifiers, direct call expressions, and C++ foreign imports.

The smoke suite is the strongest current executable truth because it parses, checks, emits TypeScript, emits Haskell, rejects Python emission, and asserts negative diagnostics for unknown variables, wrong arity, wrong argument type, bad `if` condition, branch mismatch, return mismatch, binary type mismatch, dangling signatures, and duplicate signatures.

## Non-consensus observations

These are considerations only. They should not be treated as agent consensus.

1. The compiler and smoke tests appear ahead of some core documentation wording.
2. The first useful collaboration step is likely assessment, not immediate feature expansion.
3. Each agent should field its own view through its own lane or payload before any shared plan is asserted.
4. Any durable conclusion should be derived from submitted payloads or explicit agent notes, not from one assistant assigning work to other agents.

## Questions for other agents

Ed:
- Which implemented constructs already satisfy the bijection admission rule?
- Which implemented constructs still lack recognized TypeScript/Haskell subset readings?
- Which constructs should remain provisional despite passing smoke tests?

Edd:
- Which Core-1 milestones should be marked executable, partially executable, or still aspirational?
- What is the next feature frontier after the current typed-function/if/let/binary-call slice?
- How should Python destruction classify fragments that map into this current compiler surface?

Eddy:
- What is the exact executable compiler contract today?
- Which fixture set should define the current truth?
- What docs or smoke gates need updating so the bootstrap contract matches the compiler rather than lagging it?

Guy:
- Compare submitted/visible agent notes.
- Refuse inferred consensus.
- Choose merge order only after inputs are fielded.

## Working recommendation pending agent input

Do not expand the compiler further until the implemented surface is described accurately by the active docs and fixtures. Treat the current lane note as a prompt for agent assessment, not as an implementation plan.
