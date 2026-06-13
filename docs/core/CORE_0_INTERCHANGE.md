# LambdaScript Core-0 interchange contract

Core-0 is the current executable interchange subset for LambdaScript. Its purpose is to keep TypeScript and Haskell emission tied to one canonical LambdaScript program, with tests that exercise the compiler surface that actually exists today.

Core-0 is intentionally narrower than the eventual language. A construct belongs to Core-0 only when it has one canonical AST form, one checker rule, one TypeScript emission rule, one Haskell emission rule, and fixtures for both emitters.

This document is Eddy-owned. Its job is to describe the implemented bootstrap subset and keep the fixtures/tests honest. Ed owns the broader bijection discipline. Edd owns the Core-1 roadmap.

## Current role

Core-0 is the stable target for early Python destruction only when the recovered fragment fits the implemented LambdaScript subset. Python implementation bodies that do not fit Core-0 should be routed to C++ or to a manual migration report.

C++ is a destruction target for implementation bodies and native surfaces. It is not a LambdaScript backend in this contract. LambdaScript carries the interface, module boundary, orchestration surface, and C++ FFI declaration.

## Accepted top-level forms

A Core-0 file contains one or more modules.

A module contains declarations and C++ foreign imports.

```text
module Name

name = expression
foreign cpp local_name : arg_type -> result_type = "external_symbol"
```

Core-0 currently accepts two top-level statement families:

```text
Declaration
ForeignImport
```

## Accepted expressions

Core-0 expressions are:

```text
Identifier
Literal
CallExpression
```

Literals are booleans, numbers, and strings.

Identifiers name previous declarations or foreign imports. The current checker remains light; until stronger name and type checking lands, Core-0 examples should keep reference structure simple and explicit.

Call expressions use a named callee and positional arguments.

## Accepted foreign types

Core-0 C++ FFI signatures use this primitive set:

```text
i32
f64
bool
string
void
```

`void` may appear only as a result type.

## Interchange rule

A Core-0 fixture must satisfy this sequence:

```text
parse succeeds
check succeeds
TypeScript emission succeeds
Haskell emission succeeds
Python emission is rejected
```

The TypeScript and Haskell outputs need not be textually identical, because they use different runtime conventions. They must represent the same LambdaScript declarations, literals, calls, and C++ FFI surface.

## Current implemented feature matrix

This matrix records what Eddy's lane may enforce directly today. It is intentionally practical rather than aspirational.

```text
feature: module declaration
status: core0
syntax: module Name
AST form: Module
checker rule: module is accepted when parser creates a module container
TypeScript emission: module comment plus emitted declarations
Haskell emission: module comment plus emitted declarations
fixtures: examples/hello.ls, examples/core/core0_values.ls, examples/core/core0_ffi.ls
Python-destruction relevance: recovered Python files need a LambdaScript module container
owner: Eddy
```

```text
feature: literal value declaration
status: core0
syntax: name = 42 | 3.5 | true | false | "text"
AST form: Declaration containing Literal
checker rule: accepted by current checker
TypeScript emission: export const name = literal
Haskell emission: name = literal, with booleans emitted as True or False
fixtures: examples/hello.ls, examples/core/core0_values.ls
Python-destruction relevance: module-level Python constants can map here when the value is primitive
owner: Eddy
```

```text
feature: identifier alias declaration
status: core0
syntax: copy = answer
AST form: Declaration containing Identifier
checker rule: currently light; examples should reference simple previous declarations
TypeScript emission: export const copy = answer
Haskell emission: copy = answer
fixtures: examples/core/core0_values.ls
Python-destruction relevance: simple aliases can map here when name resolution is unambiguous
owner: Eddy
```

```text
feature: call declaration
status: core0
syntax: answer = add_i32(40, 2)
AST form: Declaration containing CallExpression
checker rule: currently light; Core-0 fixtures should use named callees and positional primitive arguments
TypeScript emission: exported runtime-passing function for C++ calls
Haskell emission: IO binding for foreign call results
fixtures: examples/core/core0_ffi.ls
Python-destruction relevance: direct calls to known functions can map here when effects are explicit
owner: Eddy
```

```text
feature: C++ foreign import
status: core0
syntax: foreign cpp local : i32 -> i32 = "symbol"
AST form: ForeignImport
checker rule: signature uses the accepted primitive FFI set and void appears only as result
TypeScript emission: runtime call wrapper using CppForeignRuntime
Haskell emission: foreign import ccall declaration
fixtures: examples/core/core0_ffi.ls
Python-destruction relevance: Python fragments routed to C++ should expose explicit foreign symbols here
owner: Eddy
```

```text
feature: Python emission rejection
status: core0
syntax: lsc emit file.ls --target py|python
AST form: none
checker rule: CLI rejects unsupported Python target
TypeScript emission: none
Haskell emission: none
fixtures: glc/test/smoke.ts
Python-destruction relevance: preserves the boundary that Python is legacy input/tooling only, not a backend
owner: Eddy
```

## Current asymmetries to remove

The present emitters are useful but not yet a proof of robust interchange.

TypeScript routes C++ calls through a runtime object. Haskell emits direct `foreign import ccall` declarations. This is acceptable as a host convention, provided the same LambdaScript FFI surface is preserved.

TypeScript currently emits general nested call expressions more broadly than Haskell. Haskell emission must be tightened so every Core-0 accepted call form has a corresponding Haskell output, or the checker must reject the form as outside Core-0.

## Core-0 fixtures

The initial fixtures are:

```text
examples/core/core0_values.ls
examples/core/core0_ffi.ls
```

Each fixture must be parsed, checked, emitted to TypeScript, emitted to Haskell, and included in smoke tests.

## Feature schema

Every Core-0 feature should be tracked with this schema:

```text
status
AST form
syntax
checker rule
TypeScript emission
Haskell emission
fixtures
Python-destruction relevance
```

The current Core-0 features are bootstrap-status features. They document what the compiler presently accepts rather than what Core-1 should eventually contain.

## Growth rule

Future language features should be added only by extending the shared core docs, adding fixtures, and updating both emitters together.

Candidate Core-1 features include typed function declarations, explicit parameter lists, conditionals, local bindings, product records, tagged sums, recursion policy, module imports, and stronger type checking.

Until a feature appears in the shared contract and in both emitters, it should not be treated as part of the robust interchange subset.
