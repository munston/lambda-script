# LambdaScript Core-1 roadmap

This document defines the first serious target language for LambdaScript. It is the normalized form of Edd's Core v1 work.

Core-1 is a design target, not an implementation claim. Core-0 remains the executable truth for the current bootstrap compiler. Core-1 describes the next typed, Turing-complete common subset that should eventually be emitted to both TypeScript and Haskell.

Python remains unsupported as an emission backend. C++ is not a LambdaScript backend. C++ is a possible native support target for Python destruction and is called from LambdaScript through explicit `foreign cpp` declarations.

## Goals

Core-1 should be small enough to implement in the bootstrap compiler, but expressive enough to write ordinary programs and to serve as a migration target.

The core should support:

```text
named modules
top-level function definitions
value definitions
lexical let
conditionals
recursion by named function reference
primitive arithmetic and comparison
booleans, integers, floating point numbers, strings, and unit
simple product records or tuples
lists
explicit function types
explicit C++ foreign imports
deterministic TypeScript and Haskell emission
```

Core-1 should be Turing complete through recursive functions plus conditionals, or through a later explicit loop form that lowers into recursion. The first implementation should prefer recursion because it has a direct Haskell interpretation and a straightforward TypeScript interpretation.

## Non-goals

Core-1 should not include Haskell type families, higher-rank types, GADTs, type-level computation, laziness as an observable guarantee, implicit typeclass resolution, JavaScript prototype behaviour, TypeScript structural type tricks, Python objects, Python exceptions, Python decorators, Python generators, Python reflection, or Python monkey-patching.

Core-1 should not attempt to preserve all source-language idioms. It is the common semantic denominator for LambdaScript-owned logic.

## Source shape

A module contains imports, foreign imports, type declarations, and definitions.

```ls
module Math

add : i32 -> i32 -> i32
add x y = x + y

fact : i32 -> i32
fact n = if n <= 1 then 1 else n * fact(n - 1)
```

The concrete syntax can remain simple while the parser matures. The important point is the AST shape.

## Target AST forms

The implementation should move toward an AST with at least these expression forms:

```text
Identifier
Literal
Call
Lambda
Let
If
BinaryOp
UnaryOp
Tuple
Record
FieldAccess
List
Match or Case
```

`Lambda` is useful but not strictly required for the first executable Core-1 slice if named functions exist. It becomes important for higher-order functions and for a better TypeScript/Haskell correspondence.

`Match` or `Case` can be delayed until algebraic data types are added, but a typed eliminator for booleans and lists will become necessary quickly.

## Types

The first type layer should include:

```text
Unit
Bool
i32
f64
string
List<T>
Tuple<T...>
Record { field : T, ... }
Function<T1, ..., R>
```

The first implementation can use explicit annotations for top-level definitions. Local inference may be added later.

Type names should be chosen for stable cross-emission rather than for Haskell or TypeScript idiom. For example, `i32` and `f64` are acceptable source primitives even if TypeScript maps both to `number`.

## Evaluation model

Core-1 should be strict by default. This aligns naturally with TypeScript and prevents accidental dependence on Haskell laziness.

Haskell emission should use ordinary pure functions where possible, with `IO` only around explicit foreign imports or other declared effects. TypeScript emission should use ordinary functions and values. If an expression is pure in Core, both emitters should keep it pure.

## Effects

Core-1 should separate pure code from effectful code.

A minimal first form is:

```text
pure expression
foreign cpp call returns effectful value when necessary
```

The current C++ FFI already forces different TypeScript and Haskell shapes: TypeScript passes a `CppForeignRuntime`, while Haskell uses `foreign import ccall` and `IO`. Core-1 should make that boundary explicit rather than hiding it.

A later design may introduce an effect type such as `IO<T>` or `Eff<T>`. The first implementation can use a restricted rule: calls to `foreign cpp` functions are effectful, and any definition depending on them is effectful.

## TypeScript correspondence

Pure Core functions should emit to TypeScript functions or constants.

```ls
add : i32 -> i32 -> i32
add x y = x + y
```

should map to a TypeScript shape like:

```ts
export function add(x: number, y: number): number {
  return x + y;
}
```

Recursive functions should emit as named functions, not anonymous constants, so recursion is direct.

Core records should emit to plain object types or generated interfaces. Core tuples should emit to fixed arrays or small object records. The choice should be made once and kept stable.

## Haskell correspondence

Pure Core functions should emit to ordinary Haskell functions.

```hs
add :: Int -> Int -> Int
add x y = x + y
```

Core should avoid features that require advanced Haskell extensions in v1. If an emitted Haskell file needs language pragmas, that should be treated as a design warning unless the feature was explicitly accepted.

## Bijective discipline

The goal is not full round-trip parsing of arbitrary TypeScript or arbitrary Haskell. The goal is a common LambdaScript core whose emitted TypeScript and Haskell are predictable enough that the same Core AST can explain both outputs.

A practical bijection means:

```text
Core AST -> TypeScript output
Core AST -> Haskell output
TypeScript subset shape <-> Core AST
Haskell subset shape <-> Core AST
```

The subset shapes should be deliberately narrow. A TypeScript function emitted from Core should avoid optional arguments, overloads, prototypes, `this`, exceptions, mutation-heavy object patterns, and ambient dynamic module behaviour. A Haskell function emitted from Core should avoid typeclass-heavy implicit logic, laziness-dependent definitions, advanced extensions, and partial pattern failures.

## Python destruction target

The future Python destructor should target Core-1 plus C++ support code. It should classify each Python fragment into one of four categories:

```text
recoverable_core
native_support_cpp
external_tooling_residue
unsupported_dynamic_semantics
```

`recoverable_core` becomes `.ls`.

`native_support_cpp` becomes `.cpp` / `.h`, with matching `foreign cpp` declarations in `.ls`.

`external_tooling_residue` remains outside LambdaScript temporarily and should be documented as tooling debt.

`unsupported_dynamic_semantics` becomes a report entry with a reason and a manual migration obligation.

The destructor must not emit Python and must not imply that Python is a supported LambdaScript runtime.

## Python constructs likely recoverable into Core

The first destructor can recover:

```text
module-level constants
first-order pure functions
arithmetic and boolean expressions
simple if / else
local assignments that can become let
direct calls to known functions
simple lists and tuples once Core supports them
simple dataclass-like records once Core supports records
```

## Python constructs likely routed to C++

The destructor may route these to C++ when recovery into Core would be misleading:

```text
tight numeric loops
array or buffer manipulation
stateful low-level algorithms
direct file or process primitives intended as native support
performance-critical kernels
ABI-shaped helper functions
```

Such C++ should be made explicit. LambdaScript should call it through `foreign cpp` declarations.

## Python constructs to reject or report

The first destructor should report rather than translate:

```text
decorators with semantic effect
metaclasses
monkey-patching
reflection-driven dispatch
dynamic imports
generators and coroutines
exception-heavy control flow
context managers with nontrivial resource semantics
mutation through arbitrary object graphs
duck-typed protocols without an explicit structural model
```

Rejecting these is a feature. The destructor is a migration tool, not a Python compatibility layer.

## Implementation milestones

Milestone 1: extend the AST with typed function definitions, parameters, binary operations, conditionals, and lexical `let`.

Milestone 2: emit the same pure recursive examples to TypeScript and Haskell.

Milestone 3: add minimal records or tuples and lists.

Milestone 4: make effect marking explicit for C++ FFI calls.

Milestone 5: write the first Python destructor that emits Core skeletons and migration reports.

## First acceptance examples

The first acceptance suite should include:

```ls
module CoreSmoke

id_i32 : i32 -> i32
id_i32 x = x

add : i32 -> i32 -> i32
add x y = x + y

fact : i32 -> i32
fact n = if n <= 1 then 1 else n * fact(n - 1)
```

These examples should emit to both TypeScript and Haskell and should preserve direct named recursion.

## Open decisions

```text
whether function application syntax should be f(x, y) only, Haskell-style whitespace application, or both
whether records or tuples should come first
whether Core-1 should include anonymous lambdas immediately or delay them until after named functions work
whether effects should be represented in source type syntax in v1 or inferred from foreign calls temporarily
whether lists should be primitive syntax or library-provided constructors
```
