# C++ FFI (v1)

LambdaScript can declare and call C++ functions.

## Syntax

```ls
foreign cpp add_i32 : i32 -> i32 -> i32 = "ls_add_i32"
answer = add_i32(40, 2)
```

## TypeScript
Uses `CppProcessRuntime` (Node subprocess).

## Haskell
Uses `foreign import ccall` + `IO`.

## Limitations
- No long-running native process yet
- String/bool ABI is provisional
