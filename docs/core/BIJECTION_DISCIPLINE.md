# LambdaScript bijection discipline

This document defines the discipline that keeps LambdaScript from becoming a collection of ad hoc translators. It is the normalized form of Ed's core-bijection work.

The core AST is the authority. Haskell and TypeScript are co-equal realizations of that AST. Python is not a backend. C++ is not a LambdaScript backend; it appears only as an explicit foreign/native boundary and as a possible destruction sink for Python implementation material.

## Current implementation status

The current bootstrap compiler emits TypeScript and Haskell only. It rejects Python emission by design.

The current AST supports identifiers, string/number/boolean literals, simple call expressions, top-level declarations, and C++ foreign imports. That implemented surface is documented by `CORE_0_INTERCHANGE.md` and exercised by the Core-0 fixtures.

This document describes the acceptance discipline for future growth, not a claim that all of the discipline is implemented already.

## Core authority

A valid LambdaScript core program should have a canonical meaning independent of whether it is emitted to Haskell or TypeScript. The emitted forms should be equivalent presentations of the same program.

The target is a portable typed functional subset with explicit effects and explicit native boundaries. It should avoid importing Haskell type-level methodology and avoid importing JavaScript object dynamism.

## Bijection principle

For every accepted core construct, there must be a corresponding Haskell realization and a corresponding TypeScript realization. The mapping does not require textual round-tripping through arbitrary host-language source files. It requires semantic round-tripping through recognized host subsets:

```text
LambdaScript core AST
  -> Haskell emission
  -> recognized Haskell subset
  -> LambdaScript core AST

LambdaScript core AST
  -> TypeScript emission
  -> recognized TypeScript subset
  -> LambdaScript core AST
```

Where a host-language feature cannot be re-read into the core model, that feature is outside the bijective subset. Host-specific helpers may exist in generated support code, but they are not core language features.

## Minimum eventual core

The first complete core should include:

```text
modules
imports
primitive values
named values
first-order and higher-order functions
function application
let bindings
if expressions
algebraic data types
product types
pattern matching
recursive definitions
simple parametric polymorphism
explicit effect boundary
explicit foreign declarations
```

This set is sufficient for Turing-complete computation once recursive definitions and function values are available. Recursion should be defined directly rather than smuggled through host-language escape hatches.

## Expressions

Core expressions should include literals, variables, lambda abstractions, applications, let bindings, conditionals, constructors, records or product construction, field projection, case analysis, and explicitly marked effectful calls.

The expression language should stay expression-oriented. Statement-style sequencing belongs either to a small explicit effect form or to desugaring into bindings. This keeps the Haskell and TypeScript readings aligned.

## Types

The first stable type layer should include:

```text
Int
i32
f64
Bool
String
Unit
function types
named algebraic data types
product types
simple type variables
```

The core should not initially include type families, higher-kinded types, GADTs, dependent types, row-polymorphic object calculus, structural TypeScript object mutation, or implicit JavaScript-style nullability. Such features may be considered later only as explicit extensions with clear Haskell and TypeScript interpretations.

## Data discipline

Algebraic data types should be the main portable data mechanism. TypeScript emission can use tagged unions. Haskell emission can use ordinary `data` declarations. Product values may be represented as records or single-constructor data declarations, provided the chosen representation has one canonical LambdaScript reading.

Objects in the JavaScript sense are not core data. If a TypeScript object literal is used as an emission detail, it must correspond to a declared LambdaScript product or record type.

## Pattern matching

Pattern matching should cover literals, wildcards, variables, constructors, and products. Guards may be added after the base case form is stable.

TypeScript emission may use discriminant checks and local bindings. Haskell emission may use native pattern matching.

Pattern matching should be totality-auditable even if the language permits partial matches. The verifier should eventually be able to warn on incomplete matches.

## Effects

The core should treat effects explicitly. Pure definitions and effectful definitions should be distinguishable in the core model.

Haskell may represent effects with `IO` or a later effect abstraction. TypeScript may represent effects as ordinary function calls or promises only where the core marks the boundary.

Implicit host effects are outside the bijective core. File I/O, mutation, foreign calls, randomness, time, subprocesses, and host runtime access should enter only through explicit effect or foreign declarations.

## Foreign and native boundary

Foreign declarations are part of the core boundary mechanism. They describe names, target boundary, symbols, and primitive signatures.

C++ is a native/foreign target for boundary code and for Python destruction salvage. C++ is not a LambdaScript backend.

A LambdaScript module may call a C++ foreign symbol only through an explicit declaration. Generated Haskell and TypeScript may use different host mechanisms to reach that symbol, but the LambdaScript declaration remains the source of truth.

## Exclusions

The following are outside the core bijection:

```text
Python emission
Python runtime integration
Python module FFI
C++ emission as a LambdaScript backend
untyped host object mutation
reflection and eval
dynamic import as language semantics
host exception models as implicit control flow
Haskell type-level programming
TypeScript conditional or mapped type computation as language semantics
```

Python may be consumed by a destructor tool. The destructor may recover LambdaScript, C++, or a loss report. That process does not add Python to the compiler boundary.

## Python destruction relation

The Python destructor should target the accepted core when it can recover pure program structure. It may target C++ when it encounters imperative/native salvage material such as byte handling, performance kernels, explicit runtime adapters, or FFI housing.

The destructor should produce a destruction report when Python source depends on semantics that the core deliberately refuses. It must not define new LambdaScript semantics merely because Python used them.

## Acceptance rule

A construct is accepted into the LambdaScript core only when all of the following are true:

```text
it has a precise core AST representation
it has a checker rule
it has a Haskell emission rule
it has a TypeScript emission rule
it has a recognized Haskell-subset reading rule
it has a recognized TypeScript-subset reading rule
it has fixtures or golden tests
it does not rely on Python semantics
it does not treat C++ as a LambdaScript backend
```

Core-0 may temporarily mark recognized-subset reading rules as pending while the bootstrap compiler grows. New Core-1 features should not be called fully accepted until the full rule is satisfied.
