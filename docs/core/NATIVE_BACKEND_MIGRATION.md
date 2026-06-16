# LambdaScript native backend migration

Status: project direction document.

This document records the migration plan for removing Python from required LambdaScript operation and replacing the mature implementation substrate with C++ tools exposed through the LambdaScript compiler/backend boundary.

## 1. Strategic pivot

LambdaScript should be treated as a small front-end/interface language over a native implementation backend. The project should not try to make generated TypeScript carry the complexity currently carried by Python tooling.

The intended shape is:

```text
LambdaScript:
  small admitted language surface
  stable typed declarations
  stable foreign/native-call boundary
  generated TypeScript control wrappers

Generated TypeScript:
  thin adapter layer
  stable wrapper output
  primitive argument/result routing
  no substantial tooling implementation

C++:
  implementation of forks tooling
  implementation of accelerator tooling
  implementation of native utilities
  filesystem/Git/JSON/hash/receipt logic
  mature compilation target

Python:
  migration debt
  temporarily tolerated only as scaffolding
  removed from ordinary workflows in dependency order
```

The main project direction is now to make LambdaScript useful as a stable interface language over C++ implementations.

## 2. Revised compiler objective

The first compiler completion stage should be understood as an interface-compiler milestone rather than a broad TypeScript-programming milestone.

The revised Core-1 objective is:

```text
Core-1 completes when the admitted LambdaScript surface can describe and emit stable control/wrapper code for native C++ implementations.
```

This means the compiler advances when it improves:

```text
stable generated TypeScript wrapper surface
typed C++ foreign/native-call declaration support
void and primitive result handling
string argument handling
runtime/resource boundary clarity
emitted-code stability for wrappers
removal of Python dependence from operational workflows
```

The compiler should avoid expanding TypeScript as an implementation language. Generated TypeScript should stay inside the small surface that the compiler can reliably produce.

## 3. Core architecture

The intended architecture is:

```text
.ls source
  -> LambdaScript parser/checker
  -> typed interface AST
  -> generated TypeScript wrapper/control code
  -> C++ executable/library/runtime boundary
  -> native implementation
```

The generated TypeScript layer should perform only simple auditable work:

```text
import runtime bindings
expose typed wrapper functions
pass primitive arguments
route calls to C++ symbols or tools
preserve boundary result typing
avoid complex local implementation logic
```

The C++ side should perform the real work:

```text
filesystem traversal
Git command orchestration
JSON parsing and patch application
manifest construction
hashing
replay-ledger validation
accelerator-state manipulation
verification orchestration
native image/metric processing
long-running or stateful computation
```

The compiler should preserve this distinction. LambdaScript and TypeScript define and call operations. C++ implements them.

## 4. Language-surface discipline

The LambdaScript surface should remain deliberately small during the migration. A small complete interface surface is more valuable than a broad unstable language.

The admitted Core-1 surface should cover:

```text
modules
top-level values
typed function declarations
primitive types: i32, f64, bool, string, void
function calls
foreign C++ declarations
simple expressions used for wrapper/control logic
conditionals where already admitted
let expressions where already admitted
binary operations where already admitted
```

The project should avoid adding broad constructs solely to make the Python rewrite easier. The correct response to implementation complexity is to move it into C++, not to turn generated TypeScript or LambdaScript into a general tooling language.

Defer until clearly required:

```text
records
arrays/lists
general object structures
filesystem APIs inside LambdaScript
complex async control
rich TypeScript-specific constructs
large standard-library logic
```

## 5. Native backend boundary

The foreign/native boundary should become a first-class project component.

The current primitive foreign declaration shape is:

```text
foreign cpp <name> : <primitive args> -> <primitive result> = "<symbol>"
```

The project may later need an executable-tool boundary, but the exact syntax belongs to language admission work. The backend requirement is that LambdaScript can express calls into native C++ implementations without embedding implementation logic in generated TypeScript.

The boundary should eventually distinguish:

```text
C++ symbol call
C++ executable invocation
C++ library/runtime call
void-returning operation
stateful operation
filesystem-mutating operation
pure computation
```

This distinction matters because forks and accelerator operations include mutating commands. The compiler should not permanently conflate pure expression calls with effectful native tool calls.

## 6. Generated TypeScript role

Generated TypeScript should become an adapter layer.

It is responsible for:

```text
type-level wrapper shape
runtime call routing
primitive argument marshalling
primitive result handling
simple generated exports
small CLI-adjacent control shells where necessary
```

It is not responsible for:

```text
implementing replay algorithms
implementing Git lane logic
implementing accelerator algorithms
implementing patch application
implementing manifest logic
serving as a full replacement for Python
```

The emitted TypeScript should be boring, stable, and auditable. The implementation should live in C++.

## 7. Python removal strategy

Python removal should proceed by strata. The project should not attempt a wholesale rewrite of every Python script at once.

Migration classes:

```text
Class A: leaf utilities
  small scripts with clear input/output
  minimal Git side effects
  good first migration targets

Class B: validators and readers
  scripts that inspect manifests, ledgers, JSON patches, or branch state
  good early confidence-building targets

Class C: mutators
  scripts that write submissions, update ledgers, sync branches, or mutate accelerator state
  require stronger verification before replacement

Class D: orchestration commands
  forks.py-style command dispatchers
  should be replaced after enough native subcommands exist

Class E: bootstrap/developer convenience scripts
  may be removed last, or retained temporarily as non-required helpers
```

The migration should begin with Class A and Class B. Mutators and dispatchers should come later, once native readers and planners are trusted.

## 8. Candidate first migration targets

Good early categories:

```text
hashing utilities
manifest readers
ledger readers
JSON schema/shape inspectors
dry-run patch summarizers
status-format helpers
small accelerator state readers
fixture/snapshot validators
```

Riskier early categories:

```text
gadget_land_json.py
amalgamate_all.py
forks.py dispatcher
branch sync logic
force-with-lease mutation logic
ledger append mutators
accelerator state mutators
```

The risky tools can be migrated, but they should follow native readers, validators, and dry-run planners.

## 9. Migration milestones

### M0 — Record the strategic direction

Document the project decision:

```text
LambdaScript remains small.
Generated TypeScript remains thin.
C++ becomes the implementation backend.
Python becomes migration debt.
```

This file is the first M0 artefact.

### M1 — Stabilize the compiler as an interface compiler

Complete the existing wrapper surface:

```text
typed foreign C++ declarations
void-return behaviour
string argument handling
primitive return handling
stable generated TypeScript wrappers
backend tests proving wrapper shape
```

### M2 — Define the native tool ABI

Create stable conventions for native tools:

```text
command-line argument format
JSON input format where needed
JSON output format where needed
exit-code rules
diagnostic rules
file mutation rules
dry-run/apply split
hashing and receipt rules
```

### M3 — Port the first leaf utility to C++

Select one low-risk Python utility and port it to C++.

Acceptance criteria:

```text
native executable builds
same inputs produce same outputs
same failure cases are reported
verification compares old and new behaviour
ordinary workflow can call the native version experimentally
```

### M4 — Add LambdaScript wrapper over the first native tool

Write `.ls` declarations for the first native boundary and verify generated TypeScript wrapper output.

Acceptance criteria:

```text
.ls parses
.ls checks
TypeScript wrapper emits
wrapper calls native backend through the runtime/tool boundary
smoke test covers expected wrapper output
```

### M5 — Replace a real workflow subcommand

Choose one operational subcommand and replace its Python implementation with the native path.

Acceptance criteria:

```text
existing operator command still works
native implementation is used in the command path
Python implementation can be bypassed
dry-run behaviour matches
failure behaviour matches
```

### M6 — Port mutating tooling under strict verification

Move from readers/validators to mutators:

```text
submission object creation
ledger append
candidate import
branch status inspection
safe sync
amalgamation plan
```

Each mutator requires replay tests and dry-run/apply separation.

### M7 — Remove Python from normal operation

Python should be absent from the normal path:

```text
patch landing
amalgamation
gadget synchronization
accelerator operation
compiler verification
tool invocation
```

Python may remain only as archived migration reference or optional developer scaffolding.

## 10. Forks migration order

Suggested dependency order:

```text
1. Native path/repository utilities
2. Native hash and manifest utilities
3. Native replay-ledger reader
4. Native submission object reader/writer
5. Native JSON patch validator
6. Native dry-run patch summarizer
7. Native candidate materializer
8. Native branch status inspector
9. Native safe push/force-with-lease wrapper
10. Native gadget lane planner
11. Native amalgamation planner
12. Native apply path
13. Native top-level forks command dispatcher
```

Mutating commands should be late. Readers and planners provide testable confidence first.

The dry-run/apply division must survive the migration:

```text
plan:
  read state
  report intended mutations
  write nothing

apply:
  recheck assumptions
  perform mutation
  verify result
  record receipt
```

## 11. Accelerator migration order

The accelerator migration should follow the same dependency discipline.

First identify:

```text
input artefacts
output artefacts
cache/state files
hashes
build products
compiler products
verification products
```

Then classify commands:

```text
read-only inspectors
cache validators
state initializers
mutators
build invokers
cleanup commands
```

Port read-only inspectors first, then validators, then mutators, then orchestration.

Accelerator C++ code should expose stable native commands. LambdaScript should expose only a typed wrapper/control surface over those commands.

## 12. Compiler work required

The compiler needs targeted improvements, not broad language expansion.

Required compiler/backend work:

```text
stable foreign C++ declaration emission
correct void handling
correct string marshalling path
explicit unsupported backend errors
stable generated TypeScript wrappers
stable tests for emitted wrapper shape
clear separation of pure calls and effectful/native calls
```

Likely later work:

```text
resource handles
typed opaque native references
tool invocation declarations
structured result envelopes
native error/result typing
```

Avoid for now:

```text
large TypeScript runtime features
general TypeScript program generation
Python-compatible semantics
broad language syntax expansion
```

## 13. Runtime/tool boundary

The project may need a small runtime interface that generated TypeScript can call.

Possible conceptual model:

```text
NativeToolRuntime:
  callSymbol(request) -> primitive
  runTool(request) -> ToolResult
```

A tool result should carry enough information for verification and replay:

```text
exit code
stdout
stderr
optional JSON payload
optional written artefact paths
```

For mutating tools, results should include receipts:

```text
source state
target state
hashes
files touched
dry-run/apply mode
verification result
```

The exact language and TypeScript shapes remain future admission/backend work. The principle is stable: generated wrappers should call a native runtime boundary, and C++ should implement the operation.

## 14. Verification strategy

Every migration step should compare old and new behaviour until the old Python path is retired.

Verification classes:

```text
golden output tests
snapshot tests
exit-code tests
diagnostic text tests
file-tree before/after tests
hash/receipt tests
dry-run/apply equivalence tests
replay tests
```

For mutating commands:

```text
old Python dry-run
new C++ dry-run
compare plan

old Python apply in disposable fixture repo
new C++ apply in disposable fixture repo
compare resulting tree, ledger, and status
```

Only after equivalence is established should the operational command switch to native.

## 15. Agent division after the pivot

### Ed

Ed owns language admission and the minimal LambdaScript surface.

Questions for Ed:

```text
What foreign/tool declarations are admitted?
What effect markers are required?
What constructs remain outside the language?
What is the exact Core interface language?
```

### Edd

Edd owns replay safety, migration verification, and tooling replacement discipline.

Questions for Edd:

```text
What patch sizes are safe?
Which migration steps require equivalence fixtures?
Which Python tools can be replaced first?
What dry-run/apply guarantees must native tools preserve?
```

### Eddy

Eddy owns backend wrapper generation and executable-surface parity.

Questions for Eddy:

```text
Does generated TypeScript stay within the limited compiler surface?
Are C++ calls emitted correctly?
Are void/string/native-result boundaries stable?
Are emitted wrappers snapshot-tested?
Does backend output remain boring and auditable?
```

### Guy/operator

Guy arbitrates project direction and promotion order.

Questions for Guy/operator:

```text
Which migration target matters operationally?
When is a native replacement good enough?
When can a Python script be removed from normal workflow?
When should main advance?
```

## 16. Immediate next work

The next concrete steps should be:

```text
1. Maintain this direction document as the M0 artefact.
2. Define the first native tool ABI convention.
3. Select the first Python utility class to migrate.
4. Continue hardening compiler support for native wrapper generation.
5. Keep generated TypeScript narrow.
```

A good next patch after this document is a narrow inventory of Python tooling by migration class, followed by selection of the first C++ leaf utility.

## 17. Risks

### Rewriting too much at once

Replacing the top-level forks dispatcher first would be high risk. Start with leaf utilities and readers.

### Growing LambdaScript too quickly

Adding language features to make the migration easier should be resisted. The migration succeeds by moving implementation complexity to C++.

### TypeScript becoming the new Python

Generated TypeScript should remain a wrapper/control output, not the replacement implementation language.

### Weak verification

Native tools that mutate Git branches, ledgers, or accelerator state require strict dry-run/apply equivalence tests before replacement.

### Foreign boundary ambiguity

Pure calls, IO calls, executable calls, and mutating calls should not be permanently conflated. The compiler needs enough boundary structure to keep those distinctions visible.

## 18. Completion criteria

The migration reaches a meaningful completion stage when:

```text
ordinary patch landing requires no Python
ordinary amalgamation requires no Python
ordinary gadget lane synchronization requires no Python
ordinary accelerator operation requires no Python
LambdaScript emits stable wrappers for required native tools
C++ implements the operational logic
verification proves native behaviour against prior Python behaviour
Python scripts are archived or optional, not required
```

An earlier practical milestone is:

```text
one real forks or accelerator subcommand is implemented in C++
called through the new native/backend path
verified against old Python behaviour
used in normal workflow without Python
```

## 19. Summary

LambdaScript should remain a small typed interface language. Generated TypeScript should remain a thin wrapper surface. C++ should become the implementation substrate for forks, accelerator, and related tooling. Python should be treated as migration debt and removed in dependency order, starting with low-risk leaf utilities and ending with mutating orchestration commands.

The compiler work supports this migration by hardening foreign/native boundaries, wrapper emission, primitive type behaviour, and emitted-output stability. The tooling work proceeds by porting Python scripts into C++ tools with strict verification. The target system is a small language, a stable compiler, a mature native backend, and no required Python in ordinary operation.
