# Core work allocation

This document records the current parallel work split for the LambdaScript core and Python-destruction programme. It is a coordination note, not a language specification.

## Branch lanes

```text
agents/ed    bijection discipline and recognized-subset rules
agents/edd   Core-1 target and Python-destruction policy
agents/eddy  Core-0 bootstrap fixtures and executable interchange tests
agents/guy   user arbitration, local verification, merge order, release judgement
```

Each agent should keep work inside its owned artifact class. Cross-cutting edits should be discussed through the shared feature schema before code or documents are changed.

## Immediate ownership

```text
Ed:
  docs/core/BIJECTION_DISCIPLINE.md
  future recognized TypeScript subset design
  future recognized Haskell subset design

Edd:
  docs/core/CORE_1_ROADMAP.md
  future docs/core/PYTHON_DESTRUCTION.md
  future classification of Python into recoverable core, native C++ support, tooling residue, or unsupported dynamic semantics

Eddy:
  docs/core/CORE_0_BOOTSTRAP.md
  examples/core/*
  glc/test/smoke.ts fixture enforcement

Guy:
  merge arbitration
  local verification
  final acceptance of branch order
```

## Merge order

The preferred merge order for this normalization phase is:

```text
1. Eddy: Core-0 executable baseline and fixtures
2. Ed: bijection discipline and acceptance rules
3. Edd: Core-1 roadmap and Python-destruction policy
```

This order keeps the present compiler surface honest before adding the general discipline and the future target.

## Non-overlap rules

```text
Eddy should not expand Core-1 feature order.
Eddy should not redefine bijection discipline except by reference.
Ed should not add fixtures or smoke-test implementation.
Ed should not define the Core-1 feature sequence.
Edd should not alter Core-0 tests.
Edd should not duplicate Ed's acceptance rules except by reference.
Guy may make final integrating edits after comparing staged patches.
```

## Shared feature schema

Every new core feature should be described with this schema before implementation:

```text
Feature:
Owner:
Status: outside / Core-0 / Core-1 candidate / accepted
Core AST:
Surface syntax:
Checker rule:
TypeScript emission:
Haskell emission:
Recognized TypeScript subset:
Recognized Haskell subset:
Fixtures:
Python destruction relevance:
C++ boundary relevance:
Open decisions:
```

## Iteration protocol

```text
1. Each agent syncs to current main.
2. Each agent edits only owned files.
3. Each agent runs or relies on the relevant fixture/verifier path.
4. The patches are compared for conceptual overlap before merge.
5. The accepted patch lands on main.
6. All agent lanes fast-forward to main before the next iteration.
```

The goal is parallel progress without duplicate theory, duplicate feature ownership, or hidden drift in the compiler boundary.
