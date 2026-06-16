# Forks C++/TypeScript Migration Plan

Status: initial specification-led migration plan for replacing the reactive Python forks tooling with a smaller C++ core and a thin TypeScript CLI.

## Starting principle

This migration is a specification-led replacement, not a transliteration of the Python scripts.

The current Python tooling grew reactively around land, replay, gadget lanes, amalgamation, advisory drift, and accelerator state. The replacement should first freeze the intended operational semantics, then implement only the smallest command set that preserves those semantics.

Python parity is a migration target, not an architecture target. The new system should be smaller, stricter, and easier to audit than the current scripts.

## Core principles

1. Each command has one mutation scope. A command may perform lane-local land, gadget amalgamate, promote, accelerator edit, or status/audit. It must not silently perform a second class of mutation.

2. Replay evidence is primary. Accepted work must remain reconstructible from payload, ledger, target ref, changed files, hashes, timestamps, and verification result.

3. Destructive branch movement requires prior proof. The tool must have materialisation audit, dry-run output, expected ref, and force-with-lease before any destructive lane movement.

4. Policy and mechanics must be separated. TypeScript owns CLI shape, validation messages, and operator ergonomics. C++ owns deterministic filesystem access, JSON parsing/printing, hashing, subprocess execution, git-ref inspection, ledger materialisation, and replay/audit routines.

5. The new implementation should preserve intended workflow semantics rather than accidental Python behaviour.

6. Agent work should remain non-overlapping by default. Accelerator state assigns responsibilities, paths, current slot, next plan, and lookahead. Amalgamation consumes lanes after those responsibilities have produced replayable work.

## Least-sufficient architecture

The replacement should have one executable C++ core and one thin TypeScript CLI package.

```text
forks-core          C++ executable core
tools/forks-ts     TypeScript CLI wrapper
```

The TypeScript package parses operator-facing arguments, prints readable output, and invokes `forks-core`. It may reject malformed input early, but the C++ core must still validate every path, hash, ref, and replay object.

The C++ core should not reimplement Git. It should invoke Git through a controlled subprocess runner that records typed command plans and captures stdout, stderr, and exit status.

## Initial command surface

The first command surface should be deliberately small:

```text
status        read-only repository/gadget/lane status
audit         read-only replay/materialisation audit
agent-land    lane-local JSON patch landing
amalgamate    guarded capture/replay/verify/submit/sync
accelerator   accelerator state read/write
promote       later; outside first replacement stage
```

Each command must declare its mutation scope. Read-only commands must not mutate. Mutating commands must state the exact refs and paths they may alter before execution.

## Durable data model

The durable JSON data model should include these records:

```text
JsonPatch
ReplayLedger
ReplayEntry
AgentLane
GadgetTarget
MaterialisationAudit
AcceleratorState
VerificationProfile
CommandPlan
SubprocessResult
```

Each record should have an explicit schema and a deterministic serialisation form. The C++ core should reject unknown destructive intent and unsafe paths.

## Milestone 1: observational core

The first implementation milestone is read-only.

Required commands:

```text
forks-core status
forks-core audit --gadget lambdascript core
tools/forks-ts status
tools/forks-ts audit --gadget lambdascript core
```

Required facts:

```text
integration ref
agent refs
ahead/behind relation
replay ledger entries
payload presence
latest replay writer per path
strict mismatch versus advisory mismatch
expected mutations if a later mutating command were applied
```

This milestone tests the data model without touching branches.

## Milestone 2: lane-local landing

The second implementation milestone is lane-local only.

Required command:

```text
agent-land
```

Its scope is restricted to applying a JSON patch to:

```text
gadget-agents/<gizmo>/<gadget>/<agent>
```

It must prove that it did not advance:

```text
gadgets/<gizmo>/<gadget>/main
```

It must record replay evidence in the agreed durable ledger format. It must not promote, amalgamate, sync unrelated lanes, or perform repository-agent mutation.

## Milestone 3: guarded gadget amalgamation

The third implementation milestone consumes several ahead-only gadget-agent lanes.

Required command:

```text
amalgamate --gadget <gizmo> <gadget>
```

It must process lanes sequentially. For each lane, it should:

```text
fetch origin
inspect lane against current integration ref
capture missing or stale replay history
verify materialisation
apply replay to current integration candidate
run configured verification
dry-run submit
submit with expected-ref protection
fetch newly advanced integration ref
move to the next lane
sync selected lanes to final integration commit
```

Promotion to repository main remains outside this stage.

## Agent responsibility split

Agent responsibilities should be by continuous concern, not arbitrary files.

Ed owns operational semantics and migration safety:

```text
command contracts
audit invariants
accelerator schema
no implicit sync rules
destructive movement preconditions
```

Edd owns compiler-facing interface stability:

```text
TypeScript CLI package shape
diagnostic formatting
verification profile invocation
operator-facing command presentation
compiler/gadget target argument handling
```

Eddy owns backend and test evidence:

```text
golden outputs for current Python commands
fixture repositories for ahead-only, diverged, and replay-drift cases
parity tests proving intended workflow semantics
coverage for accidental Python behaviour that should be rejected
```

## First patch after this plan

The first implementation patch after this design note should add read-only scaffolding and fixtures, not mutating behaviour.

Preferred content:

```text
tools/forks-ts/package.json
tools/forks-ts/src/cli.ts
native/forks-core/README.md or native/forks-core skeleton
test fixtures for status/audit inputs
golden output expectations for read-only status/audit
```

No mutating command should be implemented before read-only status and audit are correct.

## Non-goals for the first replacement stage

The first replacement stage does not include:

```text
promotion to repository main
full Python feature parity
rewriting Git
implicit sync side effects
branch rewinds without captured replay proof
combining land, sync, replay, and amalgamation into one opaque command path
```

## Acceptance criteria for the design stage

This plan is sufficient when it lets the next patch add read-only C++/TypeScript scaffolding without deciding mutating command behaviour prematurely.

The next patch must preserve the separation:

```text
TypeScript: CLI shape, argument validation, readable diagnostics.
C++: filesystem, JSON, hashing, subprocess, git refs, replay materialisation.
Tests: intended semantics, not accidental Python behaviour.
```
