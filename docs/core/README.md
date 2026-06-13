# LambdaScript core documentation

This directory is the shared documentation spine for the LambdaScript core and the Python-destruction migration path.

The purpose is to prevent parallel agents from writing competing doctrine documents. Each file has a different authority layer.

## Files

```text
docs/core/CORE_0_INTERCHANGE.md
docs/core/CORE_1_ROADMAP.md
docs/core/BIJECTION_DISCIPLINE.md
```

`CORE_0_INTERCHANGE.md` is the current executable truth. It describes the subset that the compiler can parse, check, emit to TypeScript, emit to Haskell, and test today. It is Eddy-owned.

`CORE_1_ROADMAP.md` is the next language target. It describes the typed, Turing-complete core that the compiler should grow toward. It is Edd-owned.

`BIJECTION_DISCIPLINE.md` is the semantic admission rule. It describes what a feature must prove before it is accepted into the robust TS/HS interchange core. It is Ed-owned.

Python destruction policy belongs with Core-1 planning unless and until it receives its own file. Python remains outside the compiler backend surface. C++ is a native support and destruction sink, not a LambdaScript backend.

## Agent lanes

```text
Eddy: implemented Core-0 contract, fixtures, smoke tests, executable gates
Ed: bijection discipline, accepted-feature rule, recognised TS/HS subset design
Edd: Core-1 roadmap, language-growth order, Python-destruction policy
Guy: arbitration, local verification, merge order, final approval
```

## Per-feature schema

Every feature proposal should eventually be described using this schema:

```text
feature
status: core0 | core1-candidate | future | rejected
syntax
AST form
checker rule
TypeScript emission
Haskell emission
fixtures
Python-destruction relevance
C++ relevance, if any
open questions
owner
```

A feature is not part of the robust core merely because it appears in one document. It becomes accepted only when the relevant authority layers agree and the executable fixtures pass.

## Iteration rule

Each iteration should move one feature or one boundary rule forward without overlapping file ownership.

A normal feature iteration should look like this:

```text
Ed defines the admission rule.
Edd defines the Core-1 target shape and migration consequence.
Eddy adds or updates the Core-0/Core-next fixture and compiler gate.
Guy reviews the combined result and chooses merge order.
```

This lets agents work in parallel while converging on one shared schema.
