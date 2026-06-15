# LSC-1 Completion Control

Status: first-stage completion-control document for the LambdaScript compiler. This document defines the control surface for LSC-1. It does not classify the whole language surface, design the first structural feature, or replace fixture/status work from the executable-truth lane.

## LSC-1 definition

LSC-1 is complete when LambdaScript can compile one small model-relevant source fixture through parse, check, TypeScript emission, and Haskell emission, with documented language surface, tested failure modes, and a replay-safe development path.

The stage is deliberately smaller than a full GPT implementation and larger than a documentation pass. It must terminate in an executable proof object: a source fixture, a verification command, and a recorded account of the admitted language/runtime boundary required to make that fixture real.

Documentation supports LSC-1, but documentation alone does not complete it. A structural feature supports LSC-1 only when it is required by the proof fixture and admitted through parser, AST, checker, TypeScript emitter, Haskell emitter, and tests. FFI support supports LSC-1 only when LambdaScript still retains a visible source-level contract rather than becoming only a native-code launcher.

## Lane boundaries

The first LSC-1 work round has three GPT-agent lanes.

Ed owns language admission and feature legitimacy. Ed should decide which constructs are admitted, provisional, or aspirational, and which minimal language increment is required for the proof fixture.

Eddy owns executable truth and fixture discipline. Eddy should make the visible compiler contract inspectable through fixtures, commands, target output, failure modes, status categories, and drift checks.

Edd owns completion control. Edd should maintain the LSC-1 boundary, evidence classes, patch order, replay discipline, risk register, out-of-scope boundary, and closeout criteria.

Edd should not replace Ed's language-admission catalogue. Edd should not replace Eddy's fixture/status taxonomy or target-output analysis. Edd's role is to define how those outputs connect into a coherent completion stage.

## Current verification context

The current compiler verification surface already includes a smoke test path covering parsing, checking, TypeScript emission, Haskell emission, and Python target rejection for several examples. The current package test command for `glc` is:

```text
npm run build && node dist/test/smoke.js && node dist/test/gpt_haskell_smoke.js && node dist/test/cpp_ffi_extended_types_smoke.js
```

Edd records this as current context, not as a complete executable-truth taxonomy. Eddy should own the detailed fixture/status map and the final proof-command account.

## Proof-object gate

A named proof fixture should exist before the first structural compiler implementation patch begins.

The proof fixture should satisfy these conditions:

```text
model-relevant
smaller than full GPT
larger than scalar arithmetic
closeable inside LSC-1
able to expose a real language/runtime boundary
able to be checked against TypeScript and Haskell emission
```

Candidate proof-object categories may include:

```text
token or feature-vector transform
tiny embedding lookup surrogate
scalar-plus-structured numeric pipeline
typed FFI resource wrapper with visible LambdaScript-level contract
reduced model-step skeleton proving data shape and function composition
```

The proof fixture should not be selected merely because a feature is attractive. The selected fixture should determine the minimal language/runtime increment, not the other way around.

## Evidence classes

Each LSC-1 stride should leave one or more durable evidence objects.

Required evidence classes are:

```text
current-source documentation
positive fixture
negative diagnostic fixture
TypeScript emission proof
Haskell emission proof
CLI verification command
replay-ledger JSON submission result
explicit limitation or out-of-scope note
```

A patch that produces no evidence object should be treated as planning prose rather than LSC-1 progress.

## Provisional patch sequence

The first pass should follow this sequence unless Guy explicitly redirects it.

```text
Patch 1: LSC-1 completion-control document.
Patch 2: Ed/Eddy evidence account or status-map work.
Patch 3: proof-fixture candidate or proof-fixture stub.
Patch 4: minimal compiler increment required by the proof fixture.
Patch 5: parity, golden-output, or CLI verification hardening.
Patch 6: LSC-1 closeout document with limitations.
```

This order is provisional. It should be updated after Ed's language-admission account and Eddy's executable-truth account are fielded.

## Replay and JSON-submission discipline

Durable implementation work should enter through JSON patches. Provisional lane notes remain ordinary branch state and may be destructively overwritten by synchronization.

For durable LSC-1 patches:

```text
read current source before constructing the patch
keep each patch small enough to replay safely
avoid uncommitted local dependencies
record the target gadget and verification profile
use sync or refresh when other agents have moved the target
avoid overlapping edits with Ed and Eddy lanes
leave evidence that can be inspected after replay
```

The intended target for this control document is the `lambdascript/core` gadget, under `docs/core/`.

## Risk register

The following risks should be checked during each LSC-1 stride.

```text
documentation capture: documentation becomes the milestone instead of supporting it
arrays capture: arrays/lists become the milestone instead of a possible fixture dependency
parser-substrate capture: parser machinery becomes the milestone instead of a supporting requirement
FFI native-launcher drift: LambdaScript becomes a launcher for hidden native code
fixture-taxonomy drift: the fixture map becomes inventory work without a proof object
overlap drift: agents create competing documents that cannot be reconciled
premature implementation: implementation begins before proof object and evidence gates are fixed
branch-state drift: patches depend on local state rather than replayable JSON submissions
target-drift: TypeScript and Haskell outputs stop representing the same intent
```

## Out of scope for LSC-1

The following are outside LSC-1 unless Guy explicitly changes the stage:

```text
full GPT implementation
full tensor runtime
broad parser rewrite unless required by the selected proof fixture
full module/import system unless required by the selected proof fixture
complete records/arrays/vector algebra unless required by the selected proof fixture
performance optimization except where required for verification
generic roadmap prose that does not terminate in the LSC-1 proof object
```

## Dependencies on Ed

Edd closeout depends on Ed producing or approving a language-admission account.

That account should identify:

```text
which current constructs are admitted
which current constructs are provisional
which current constructs are aspirational
which language features the proof fixture requires
which minimal language increment should be attempted first
which positive and negative tests prove admission
```

Edd should link Ed's document here once it is available.

```text
Ed language-admission account: pending
```

## Dependencies on Eddy

Edd closeout depends on Eddy producing or approving an executable-truth account.

That account should identify:

```text
the current command proving the present compiler state
the fixture/status taxonomy for visible compiler truth
target-parity risks
hidden runtime or CLI assumptions
the future command that should prove LSC-1 complete
```

Edd should link Eddy's document here once it is available.

```text
Eddy executable-truth account: pending
```

## LSC-1 closeout criteria

LSC-1 can close only when all of the following are true:

```text
current executable surface account exists and is linked
proof fixture exists and is linked
Ed has classified the proof fixture's required language features
Eddy has identified the command or profile proving compiler behaviour
positive fixtures exist for the admitted increment
negative diagnostics exist for malformed or ill-typed neighbouring cases
TypeScript emission succeeds for the proof fixture or an accepted reduced version
Haskell emission succeeds for the proof fixture or an accepted reduced version
verification profile is named and runnable
remaining limitations are documented
replay/submission path for closing patches is recorded
```

## Preliminary next-turn plan

After this document lands, Edd's next turn should begin by reading current target source and the latest Ed and Eddy outputs.

If Ed has produced a language-admission document, Edd should prepare a small integration patch linking it here and updating the dependency section.

If Eddy has produced an executable-truth or fixture-status document, Edd should prepare a small integration patch linking it here and updating the verification and evidence sections.

If neither has landed yet, Edd should avoid expanding into their lanes. The next Edd patch should be delayed or limited to a minimal non-overlap refinement.

If both have landed, Edd should produce the next control patch: a revised patch sequence that names the proof-fixture decision gate, records Ed's feature recommendation, records Eddy's proof-command constraints, and prepares the implementation boundary for Patch 3.
