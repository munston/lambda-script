# LambdaScript Core-0 bootstrap contract

Core-0 is the current executable interchange subset for LambdaScript. Its purpose is to keep TypeScript and Haskell emission tied to one canonical LambdaScript program, with tests that exercise the compiler surface that actually exists today.

Core-0 is intentionally narrower than the eventual language. A construct belongs to Core-0 only when it has one canonical AST form, one checker rule, one TypeScript emission rule, one Haskell emission rule, and fixtures for both emitters.

This document is Eddy-owned. Its job is to describe the implemented bootstrap subset and keep the fixtures/tests honest. Ed owns the broader bijection discipline. Edd owns the Core-1 roadmap and the later Python-destruction policy.

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

## Shared feature schema

Every feature tracked by the core docs should use this schema. Core-0 fills only the fields that are implemented today; future Core-1 work must fill the remaining fields before a feature is accepted.

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

## Core-0 feature table

```text
Feature: module declaration
Owner: Eddy
Status: Core-0
Core AST: Program -> Module
Surface syntax: module Name
Checker rule: module accepted when parsed into Program
TypeScript emission: comment boundary for module name
Haskell emission: comment boundary for module name
Recognized TypeScript subset: pending
Recognized Haskell subset: pending
Fixtures: examples/hello.ls, examples/core/core0_values.ls, examples/core/core0_ffi.ls
Python destruction relevance: recovered files should choose explicit LambdaScript module names
C++ boundary relevance: none
Open decisions: real module imports are Core-1

Feature: top-level value declaration
Owner: Eddy
Status: Core-0
Core AST: Declaration
Surface syntax: name = expression
Checker rule: current checker accepts parsed declaration
TypeScript emission: export const for literal/identifier values; wrapper function for FFI calls
Haskell emission: top-level binding or IO binding for FFI calls
Recognized TypeScript subset: pending
Recognized Haskell subset: pending
Fixtures: examples/hello.ls, examples/core/core0_values.ls, examples/core/core0_ffi.ls
Python destruction relevance: module constants and simple pure assignments may recover here
C++ boundary relevance: declaration may call a foreign cpp symbol
Open decisions: typed definitions and parameterized functions are Core-1

Feature: literal expression
Owner: Eddy
Status: Core-0
Core AST: Literal
Surface syntax: booleans, numbers, strings
Checker rule: accepted when parsed as Literal
TypeScript emission: JSON-style literal output
Haskell emission: numeric/string output; booleans map to True/False
Recognized TypeScript subset: pending
Recognized Haskell subset: pending
Fixtures: examples/hello.ls, examples/core/core0_values.ls
Python destruction relevance: Python constants may recover here
C++ boundary relevance: literals may become foreign-call arguments
Open decisions: numeric precision classes beyond current i32/f64 boundary are Core-1+

Feature: identifier expression
Owner: Eddy
Status: Core-0
Core AST: Identifier
Surface syntax: name
Checker rule: current checker remains light; fixtures should keep references simple
TypeScript emission: identifier name
Haskell emission: identifier name
Recognized TypeScript subset: pending
Recognized Haskell subset: pending
Fixtures: examples/hello.ls, examples/core/core0_values.ls
Python destruction relevance: simple name references may recover here
C++ boundary relevance: foreign import names may be referenced by calls
Open decisions: stronger name resolution is Core-1

Feature: call expression
Owner: Eddy
Status: Core-0
Core AST: CallExpression
Surface syntax: callee(arg0, arg1, ...)
Checker rule: current checker accepts parsed call; FFI examples keep callee simple
TypeScript emission: call expression or runtime-backed FFI wrapper call
Haskell emission: direct application for supported forms; FFI calls become IO bindings
Recognized TypeScript subset: pending
Recognized Haskell subset: pending
Fixtures: examples/core/core0_ffi.ls
Python destruction relevance: direct calls to known functions may recover here when semantics are explicit
C++ boundary relevance: primary mechanism for calling declared foreign cpp functions
Open decisions: nested call parity and higher-order calls are Core-1+

Feature: C++ foreign import
Owner: Eddy
Status: Core-0
Core AST: ForeignImport
Surface syntax: foreign cpp local_name : arg_type -> result_type = "external_symbol"
Checker rule: primitive signature accepted for target cpp
TypeScript emission: exported wrapper taking CppForeignRuntime
Haskell emission: foreign import ccall declaration
Recognized TypeScript subset: pending
Recognized Haskell subset: pending
Fixtures: examples/core/core0_ffi.ls
Python destruction relevance: native-support destructuring may emit matching declarations
C++ boundary relevance: explicit native boundary; C++ remains a foreign target, not a backend
Open decisions: effect typing for FFI calls is Core-1
```

## Growth rule

Future language features should be added only by extending the shared core docs, adding fixtures, and updating both emitters together.

Candidate Core-1 features include typed function declarations, explicit parameter lists, conditionals, local bindings, product records, tagged sums, recursion policy, module imports, and stronger type checking.

Until a feature appears in the shared contract and in both emitters, it should not be treated as part of the robust interchange subset.
