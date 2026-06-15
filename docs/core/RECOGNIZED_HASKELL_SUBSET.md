# Recognized Haskell subset

Status: Ed scaffold.

This document will define the Haskell shapes that may be read back as LambdaScript core. It is an admission document, not a general Haskell style guide and not a claim that arbitrary Haskell can be imported.

## Purpose

A LambdaScript feature becomes robust only when its emitted Haskell has a deliberately narrow recognized form. The recognized form should be simple enough to map back to the same core AST without importing Haskell type-level programming, implicit typeclass design, laziness-dependent semantics, advanced extensions, partial pattern behaviour, or host-specific module conventions.

## Initial scope

This scaffold covers the current Core-0 surface first:

```text
module declaration
top-level value declaration
literal expression
identifier expression
call expression
C++ foreign import declaration
```

The following implementation forms exist in the current compiler but should remain outside accepted Ed status until their recognized Haskell readings are specified with matching checker and fixture coverage:

```text
binary expression
if expression
let expression
typed function declaration
named recursion
```

## Provisional recognized forms

### Module boundary

A generated module comment may identify the originating LambdaScript module. The comment is metadata for readback and does not create Haskell module semantics by itself.

```hs
-- Module: Name
```

### Value declaration

A pure top-level LambdaScript declaration may read back from a simple top-level binding when the right-hand side is in the recognized expression subset.

```hs
name = expression
```

A binding whose type is `IO T` should not be treated as pure core. It must be tied to an explicit foreign/effect rule.

### Literal expression

Recognized literals are strings, numeric literals, and booleans emitted as `True` or `False`. Lists, tuples, records, constructors, characters, overloaded numeric forms, and polymorphic literal use remain outside the initial Core-0 reading unless accepted by a later feature rule.

### Identifier expression

A recognized identifier is a bare reference to a LambdaScript declaration, parameter, or foreign import name already in scope. Qualified names, operators as values, record accessors, implicit class methods, and names introduced by generated support imports remain outside the initial subset.

### Call expression

A recognized call is direct Haskell application of a recognized identifier to positional arguments in the recognized expression subset.

```hs
callee arg0 arg1
```

Sections, infix host-specific rewrites, higher-order host callbacks, `$`, `.`, laziness-dependent control, and partial application as a host feature remain outside the initial subset until admitted by a specific Core feature rule.

### C++ foreign import

The current Haskell emitter represents C++ FFI through `foreign import ccall` and uses `IO` around foreign calls. Ed needs to decide whether this exact declaration shape is the recognized Haskell reading for `ForeignImport`, or whether it should be treated as generated boundary code whose readback authority remains the LambdaScript `foreign cpp` declaration.

```hs
foreign import ccall "symbol" localName :: A -> B -> IO R
```

## Open Ed decisions

```text
whether generated support imports such as Foreign.C.String participate in readback
whether foreign imports are read back directly or treated as support code
how to distinguish pure Core bindings from IO-backed foreign bindings
whether named recursive functions are admitted before lambdas and higher-order functions
how strict the printer/readback round-trip should be for parentheses and expression precedence
```
