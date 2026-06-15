# C++ FFI tensor bridge

Status: Ed typed-FFI bridge.

This document records the immediate C++ FFI route for GPT/tensor work without adding `hmatrix` or any other Haskell numeric dependency.

## Typed ABI surface

LambdaScript now admits the following C++ FFI boundary types:

```text
i32
f64
bool
string
void
handle
f64buf
i32buf
```

The new types have these intended meanings:

```text
handle  opaque C++ resource handle
f64buf  pointer-like handle to a Double buffer
i32buf  pointer-like handle to an Int buffer
```

They are explicit FFI boundary types, not general LambdaScript data structures. They let LambdaScript distinguish model handles, floating buffers, integer token buffers, dimensions, and ordinary scalar values.

## Haskell mapping

The Haskell emitter maps the typed bridge as:

```text
handle -> Ptr ()
f64buf -> Ptr CDouble
i32buf -> Ptr CInt
```

Foreign returns are emitted as `IO (Ptr CDouble)`, `IO (Ptr CInt)`, or `IO (Ptr ())` where required. This gives the generated Haskell an ordinary `foreign import ccall` surface while avoiding `hmatrix`.

## TypeScript mapping

The TypeScript emitter maps these FFI resource values to `number` for the current runtime-mediated `CppForeignRuntime` bridge. That keeps the current runtime shape intact while preserving source-level LambdaScript type checking.

## GPT direction

GPT tensor code should now use explicit typed FFI declarations for native resource operations:

```text
gpt_alloc_f64_buffer : i32 -> f64buf
gpt_alloc_i32_buffer : i32 -> i32buf
gpt_create_model     : string -> handle
gpt_model_score      : handle -> i32buf -> i32 -> f64
```

The later compiler work is to lift these into native LambdaScript arrays/vectors/matrices. Until then, C++ can own heavy tensor memory while LambdaScript retains typed, portable declarations and can still emit both TypeScript and Haskell.
