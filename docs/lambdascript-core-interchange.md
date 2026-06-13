# LambdaScript Core-0 interchange contract

Core-0 is the first deliberately small interchange subset for LambdaScript. Its purpose is to make TypeScript and Haskell emission act as co-equal witnesses of one canonical LambdaScript program, rather than as independent convenience outputs.

Core-0 is intentionally narrower than the eventual language. A construct belongs to Core-0 only when it has one canonical AST form, one checker rule, one TypeScript emission rule, one Haskell emission rule, and golden tests for both emitters.

## Current role

Core-0 is the stable target for early Python destruction. The Python destructor may emit LambdaScript only for fragments that fit this contract. Python implementation bodies that do not fit Core-0 should be routed to C++ or to a manual migration report.

C++ is a destruction target for implementation bodies and native surfaces. It is not a LambdaScript backend in this contract. LambdaScript should carry the interface, module boundary, orchestration surface, and C++ FFI declaration.

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

A Core-0 fixture must satisfy this whole sequence:

```text
parse succeeds
check succeeds
TypeScript emission succeeds
Haskell emission succeeds
Python emission is rejected
```

The TypeScript and Haskell outputs need not be textually identical, because they have different runtime conventions. They must represent the same LambdaScript declarations, literals, calls, and C++ FFI surface.

## Current asymmetries to remove

The present emitters are useful but not yet a proof of robust interchange.

TypeScript routes C++ calls through a runtime object. Haskell emits direct `foreign import ccall` declarations. This is acceptable as a backend convention, provided the same LambdaScript FFI surface is preserved.

TypeScript currently emits general nested call expressions more broadly than Haskell. Haskell emission must be tightened so every Core-0 accepted call form has a corresponding Haskell output, or the checker must reject the form as outside Core-0.

## Core-0 fixtures

The initial fixtures are:

```text
examples/core/core0_values.ls
examples/core/core0_ffi.ls
```

Each fixture must be parsed, checked, emitted to TypeScript, emitted to Haskell, and included in smoke tests.

## Growth rule

Future language features should be added only by extending this contract, adding fixtures, and updating both emitters together.

Candidate Core-1 features include typed function declarations, explicit parameter lists, conditionals, local bindings, product records, tagged sums, recursion policy, module imports, and stronger type checking.

Until a feature appears in the contract and in both emitters, it should not be treated as part of the robust interchange subset.
