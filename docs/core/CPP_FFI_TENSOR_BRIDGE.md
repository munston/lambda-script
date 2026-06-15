# C++ FFI tensor bridge

Status: Ed stage-0 bridge.

This document records the immediate C++ FFI route for GPT/tensor work without adding `hmatrix` or any other Haskell numeric dependency.

## Current ABI choice

The current LambdaScript FFI surface admits only primitive types:

```text
i32
f64
bool
string
void
```

Until LambdaScript admits explicit `handle`, `f64buf`, `i32buf`, array, vector, and matrix types, the stage-0 tensor bridge represents opaque C++ resources as `i32` handles. Numeric buffers and model objects live in C++ and are referred to by integer handles at the LambdaScript boundary.

This is deliberately an ABI convention rather than the final type discipline.

## Stage-0 handle discipline

A C++ tensor bridge should expose small, explicit resource operations:

```text
gpt_alloc_f64_buffer : i32 -> i32
gpt_free_handle      : i32 -> void
gpt_read_f64         : i32 -> i32 -> f64
gpt_write_f64        : i32 -> i32 -> f64 -> void
gpt_dot_f64          : i32 -> i32 -> i32 -> f64
gpt_matmul_f64       : i32 -> i32 -> i32 -> i32 -> i32 -> i32 -> i32
```

The first `i32` parameters are handles or dimensions depending on the function contract. Functions returning `i32` may return newly allocated handles. Functions returning `void` perform updates or release resources.

## Why this is useful now

This makes the existing C++ FFI do more useful work immediately:

```text
scalar LambdaScript kernels remain dependency-free
bulk tensor work can be delegated to local C++
Haskell emission remains ordinary `foreign import ccall`
TypeScript emission remains runtime-mediated through `CppForeignRuntime`
the same LambdaScript source still emits both Haskell and TypeScript
```

## Known limitation

Because stage-0 handles are represented as `i32`, the checker cannot distinguish dimensions from buffer handles or model handles. The next admitted FFI extension should add explicit handle and buffer primitive types:

```text
handle
f64buf
i32buf
```

Those types should map to local runtime representations in TypeScript and to pointer/foreign-handle representations in Haskell without requiring `hmatrix`.
