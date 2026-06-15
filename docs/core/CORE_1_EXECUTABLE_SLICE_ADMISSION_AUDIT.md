# Core-1 executable slice admission audit

Status: Ed admission audit for the first compiler-completion stage.

This audit separates executable compiler facts from roadmap intent. The target milestone is:

```text
Core-1 Executable Slice
```

This is narrower than full Core-1. It is the first stable typed, recursive, dual-emitter compiler slice.

## Source basis

Prepared from the current `gadgets/lambdascript/core/main` surface:

```text
docs/core/CORE_0_BOOTSTRAP.md
docs/core/CORE_1_ROADMAP.md
glc/test/smoke.ts
glc/test/gpt_haskell_smoke.ts
glc/test/cpp_ffi_extended_types_smoke.ts
glc/src/core/ast.ts
glc/src/parser/parser.ts
glc/src/core/check.ts
glc/src/codegen/typescript.ts
glc/src/codegen/haskell.ts
glc/src/cli/lsc.ts
examples/core/core1_functions.ls
examples/core/core1_let.ls
examples/core/core1_pure_calls.ls
examples/core/core2_bool_logic.ls
examples/core/core0_ffi_typed_buffers.ls
```

## Admission vocabulary

```text
slice-admitted: parsed, represented in AST, checked, emitted to TypeScript, emitted to Haskell, and fixture-covered.
partial: present but missing important coverage or clarity.
runtime-provisional: compiler/emitter support exists but runtime semantics remain host-dependent.
coverage-gap: implementation exists but tests are incomplete.
doc-gap: implementation exists but docs understate or misclassify it.
deferred: belongs to a later milestone and should not block this slice.
```

## Proposed slice boundary

Included in the first executable slice:

```text
module declaration
top-level typed function definitions
top-level value definitions
lexical let
if expression
named recursion
primitive arithmetic
primitive comparison
boolean operators
primitive literals
primitive types: i32, f64, bool, string, void result boundary
explicit C++ foreign imports
foreign C++ calls through declared imports
deterministic TypeScript emission
deterministic Haskell emission
Python emission rejection
positive fixtures
negative diagnostics
documentation matching executable behaviour
```

Deferred from the first executable slice:

```text
lists
records
tuples
field access
match/case
lambda and higher-order functions
module imports
general effect typing
Python destruction
full GPT implementation
```

## Construct audit

| Construct | Status | Evidence | Gap |
| --- | --- | --- | --- |
| Module declaration | slice-admitted | Parser recognizes `module Name`; AST has modules; both emitters preserve module markers; all core fixtures use modules. | None blocking. |
| Top-level value declaration | slice-admitted | Parser emits `Declaration`; checker infers values; TS emits `export const` or FFI wrapper; HS emits binding or IO binding. | Docs should separate pure values from FFI-backed effectful values. |
| Top-level typed function | slice-admitted | Parser pairs signatures with definitions; AST has `FunctionDeclaration`; checker validates params and return; TS/HS emit named functions. | Core-0 docs understate this as future Core-1 while smoke tests already prove it. |
| Lexical `let` | slice-admitted | Parser has `LetExpression`; checker extends local scope; TS emits IIFE; HS emits `let ... in`; `core1_let.ls` proves positives. | Dedicated negative `let` coverage would strengthen the gate. |
| `if` expression | slice-admitted | Parser/checker/emitter support exists; negative tests cover condition and branch mismatch. | None blocking. |
| Named recursion | slice-admitted | Function signatures are collected before body checking; `fact` parses, checks, and emits recursively. | No recursion-specific negative test; quality-only. |
| Primitive arithmetic | slice-admitted | Binary parser/checker/emitter support; smoke tests cover positive and arithmetic type error. | More operator-specific coverage is quality-only. |
| Primitive comparison | partial / coverage-gap | `<`, `>`, `<=`, `>=` parse, check, and emit; examples use them. | Missing direct negative test for nonnumeric comparison. |
| Equality operators | partial / coverage-gap | `==` and `!=` parse/check/emit through binary operator path. | No visible positive or negative smoke fixture proves equality. |
| Boolean operators | slice-admitted | `&&` and `||` parse, check, emit; `core2_bool_logic.ls` and negative logical-type test prove the surface. | File naming is ahead of the C1 slice label but not blocking. |
| Primitive literals | slice-admitted | Bool, number, and string literals parse, infer, and emit. | None blocking. |
| Primitive types | slice-admitted for `i32`, `f64`, `bool`, `string`, `void` result | Parser/checker/emitters share the primitive type names. | Source-level unit value remains out of scope. |
| Typed FFI resources | compiler-admitted / runtime-provisional | `handle`, `f64buf`, `i32buf` parse/check/emit; typed-buffer test proves positive and mismatch cases. | Runtime meaning is host-dependent, especially TS number handles. |
| Explicit C++ foreign import | slice-admitted | Parser recognizes `foreign cpp`; checker records signatures; TS emits runtime wrapper; HS emits `foreign import ccall`. | Source-level effect typing is deferred. |
| Foreign C++ call | slice-admitted / runtime-provisional | Checker validates declared signatures; TS uses runtime; HS uses IO. | Effect propagation is emitter-convention-based. |
| Function and foreign calls | slice-admitted | Checker validates existence, function-ness, arity, and argument types; TS/HS emit pure calls and FFI wrappers. | Existing docs mention older nested-call asymmetry, but current smoke proves nested pure calls. |
| TypeScript emission | slice-admitted for current slice | Smoke tests assert fragments for values, FFI, typed functions, let, calls, bool logic, typed buffers, and scalar GPT kernels. | Eddy owns backend stability/snapshot decisions. |
| Haskell emission | slice-admitted for current slice | Smoke tests assert fragments for the same current slice surfaces. | Eddy owns backend stability/snapshot decisions. |
| Python emission rejection | slice-admitted | CLI rejects `py` and `python`; smoke tests assert rejection. | None blocking. |
| Negative diagnostics | partial / coverage-gap | Current tests cover unknown variable, wrong arity, wrong arg type, if condition, if branch, return mismatch, arithmetic mismatch, logical mismatch, dangling signature, duplicate signature. | Missing direct coverage for equality mismatch, comparison mismatch, duplicate parameter, duplicate top-level, function-used-as-value, invalid signatures. |

## Deferred construct map

| Construct | Reason | Later milestone |
| --- | --- | --- |
| Lists | Roadmap Core-1 feature, no current inspected AST/checker/emitter support. | Core-1 structural slice. |
| Records/tuples | Roadmap Core-1 feature, no current inspected AST/checker/emitter support. | Core-1 structural slice. |
| Field access | Depends on records/tuples. | Core-1 structural slice. |
| Match/case | Roadmap allows delay; depends on richer data forms. | Core-1 eliminator/data slice. |
| Lambda/higher-order functions | Useful later; named functions suffice for first executable slice. | Core-1 higher-order slice. |
| Module imports | Not present in inspected compiler path. | Core-1 module slice. |
| General effect typing | FFI boundary exists operationally, source-level effects do not. | Core-1 effects slice. |
| Python destruction | Roadmap target, not this compiler slice. | Python destruction slice. |
| Full GPT implementation | Current GPT fixture is scalar emitter evidence, not a model architecture. | GPT/model slice after structural support. |

## Gap summary

No hard blocker is visible for the proposed narrow slice, provided lists, records/tuples, imports, general effect typing, Python destruction, and full GPT remain deferred.

Quality and coverage gaps inside the slice:

```text
1. Documentation understates the executable surface.
2. Equality operators need visible positive/negative fixture coverage.
3. Comparison operators need direct nonnumeric negative coverage.
4. Typed FFI resources are compiler-admitted but runtime-provisional.
5. FFI effects are target-convention-based rather than source-effect-typed.
```

## Agent-lane dependencies

Ed owns construct inclusion, admission vocabulary, gap classification, and admission-facing patches.

Edd owns patch-size constraints, replay safety, verification profile expectations, failure/retry mechanics, and promotion route.

Eddy owns backend coverage, TS/HS parity gaps, output stability, unsupported backend cases, backend examples, and backend completion reporting.

Guy owns consensus, priority, acceptance, promotion, and any decision to widen or narrow the slice.

## Ed result

```text
The proposed Core-1 Executable Slice is viable as a first compiler-completion stage.
The current compiler already admits the core of the slice: typed functions, values, let, if, recursion, primitive operations, boolean logic, C++ FFI, TS/HS emission, and Python rejection.
The next Ed-side patch should close a small admission-coverage gap rather than add a deferred structural feature.
```

## Preliminary next Ed task

Recommended next patch:

```text
Add smoke-test coverage for existing comparison/equality diagnostics.
```

Candidate scope:

```text
glc/test/smoke.ts only
```

Candidate assertions:

```text
comparison-type: f x = x < true
equality-type: f x = x == true
```

Purpose:

```text
Strengthen the admission gate for existing binary operators without adding syntax, checker semantics, backend behaviour, or workflow machinery.
```
