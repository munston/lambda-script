# Recognized TypeScript subset

Status: Ed scaffold.

This document will define the TypeScript shapes that may be read back as LambdaScript core. It is an admission document, not a general TypeScript style guide and not a claim that arbitrary TypeScript can be imported.

## Purpose

A LambdaScript feature becomes robust only when its emitted TypeScript has a deliberately narrow recognized form. The recognized form should be simple enough to map back to the same core AST without importing TypeScript object dynamism, prototype behaviour, overloads, optional parameters, ambient module mutation, exceptions, or host-specific runtime assumptions.

## Initial scope

This scaffold covers the current Core-0 surface first:

```text
module declaration
top-level value declaration
literal expression
identifier expression
call expression
C++ foreign import wrapper
```

The following implementation forms exist in the current compiler but should remain outside accepted Ed status until their recognized TypeScript readings are specified with matching checker and fixture coverage:

```text
binary expression
if expression
let expression
typed function declaration
named recursion
```

## Provisional recognized forms

### Module boundary

A generated module comment may identify the originating LambdaScript module. The comment is metadata for readback and does not create TypeScript module semantics by itself.

```ts
// Module: Name
```

### Value declaration

A pure top-level LambdaScript declaration may read back from an exported constant when the initializer is itself in the recognized expression subset.

```ts
export const name = expression;
```

### Literal expression

Recognized literals are JSON-compatible strings, finite numeric literals, and booleans. TypeScript `null`, `undefined`, bigint, regular expressions, template strings with interpolation, object literals, and arrays remain outside this initial Core-0 reading unless accepted by a later feature rule.

### Identifier expression

A recognized identifier is a bare reference to a LambdaScript declaration, parameter, or foreign wrapper name already in scope. Property access, indexed access, `this`, destructuring, namespace mutation, and dynamic lookup remain outside the initial subset.

### Call expression

A recognized call is a direct call to a recognized identifier with positional arguments in the recognized expression subset.

```ts
callee(arg0, arg1)
```

Method calls, constructor calls, optional chaining, spread arguments, `apply`, `bind`, higher-order host callbacks, and implicit runtime dispatch are outside the initial subset.

### C++ foreign wrapper

The current TypeScript emitter represents C++ FFI through a wrapper that accepts `CppForeignRuntime` and calls `runtime.call` with a declared symbol and positional argument list. Ed needs to decide whether this exact wrapper shape is the recognized TypeScript reading for `ForeignImport`, or whether it should be treated as generated support code whose readback authority remains the LambdaScript `foreign cpp` declaration.

## Open Ed decisions

```text
whether TypeScript readback should parse generated support imports
whether foreign wrappers are read back directly or treated as support code
whether generated function declarations for Core-1 should become recognized before constants
how to represent effectful FFI calls without importing TypeScript runtime convention into the core
how strict the printer/readback round-trip should be for parentheses and expression precedence
```
