# C1 backend coverage inventory

Status: implementation pass Y1-P1 from Eddy's C1 backend/executable-surface lane.

Scope: backend evidence only. This document records TypeScript and Haskell emission coverage for the currently visible C1 compiler surface. It does not admit language constructs, choose the post-C1 feature family, define verification policy, or change parser/checker semantics.

## Evidence read

This inventory is based on the current visible `main` compiler files:

```text
glc/src/core/ast.ts
glc/src/core/program.ts
glc/src/parser/parser.ts
glc/src/core/check.ts
glc/src/codegen/typescript.ts
glc/src/codegen/haskell.ts
glc/src/cli/lsc.ts
glc/test/smoke.ts
```

The AST currently exposes modules, top-level declarations, function declarations, C++ foreign imports, and expressions consisting of literals, identifiers, calls, binary expressions, `if`, and `let`. The TypeScript and Haskell emitters both walk each module and handle the visible top-level forms and expression forms. The smoke test checks parser/checker success, TypeScript output snippets, Haskell output snippets, and Python-target rejection.

## Backend coverage table

| Construct / surface item | TypeScript backend | Haskell backend | Fixture evidence | Backend parity note | Routing note |
|---|---|---|---|---|---|
| Program / module boundary | Emits `// Module: <name>` comments while iterating modules. | Emits `-- Module: <name>` comments while iterating modules. | Covered indirectly by all smoke fixtures. | Both targets preserve module name only as a comment, not as a target-language module declaration. | Ed should decide whether comment-only module preservation is sufficient for C1 admission. |
| Top-level value declaration | Emits `export const name = expr`. | Emits `name = expr`. | `hello.ls`, `core0_values.ls`, and `core1_pure_calls.ls`. | TS exports values; HS emits bare bindings. This is stable but target idiomatic rather than structurally identical. | Edd may choose whether output snippets are enough or snapshot fixtures are needed. |
| Function declaration | Emits `export function name(params): result { return body; }`. | Emits a type signature plus equation. | `core1_functions.ls` and `core1_let.ls`. | Both targets preserve function names, parameter order, and return expression. TS uses annotated parameters; HS emits curried signatures/equations. | Backend coverage appears complete for the current C1 function form. |
| Foreign C++ import declaration | Emits a `CppForeignRuntime` wrapper function that calls `runtime.call`. | Emits `foreign import ccall`, with `CString` import when needed. | `core0_ffi.ls`. | Targets expose different runtime models: TS runtime object call versus HS FFI declaration. This is deliberate backend divergence, not necessarily a gap. | Ed should classify FFI admission level; Edd should decide whether runtime-facing fixtures are required. |
| Top-level declaration calling a foreign import | Emits `export function name(runtime: CppForeignRuntime)` forwarding through the runtime. | Emits an `IO` binding for the foreign call. | `core0_ffi.ls`. | Both targets preserve the foreign-call boundary, but the TS form is a function taking runtime and the HS form is an IO action. | This should remain explicitly documented as a backend convention. |
| Literal expression: number | Emits JSON/stringified numeric value. | Emits `String(value)`. | `hello.ls`, `core0_values.ls`, arithmetic fixtures. | Integer and floating values emit plainly in both targets. Type-level distinction is supplied by checker/signature, not literal syntax. | No backend blocker seen. |
| Literal expression: boolean | Emits `true` / `false`. | Emits `True` / `False`. | `hello.ls`, `core0_values.ls`, negative checker fixtures. | Target-specific boolean spelling handled in HS emitter. | No backend blocker seen. |
| Literal expression: string | Emits JSON string literal. | Emits JSON string literal text; C FFI signatures map string type to `CString`. | `hello.ls`, possible FFI string handling by emitter logic. | Ordinary top-level string values emit as string literals; FFI string values require `CString` treatment in HS. | Ed/Edd may want a direct string-FFI fixture if string FFI is admitted for C1. |
| Identifier expression | Emits identifier name. | Emits identifier name. | Covered inside calls, `let`, and function bodies. | Both emitters preserve the name directly. | No backend blocker seen. |
| Call expression | Emits `callee(arg1, arg2)`. | Emits `callee arg1 arg2`, parenthesizing compound arguments. | `core1_pure_calls.ls`, recursive `fact` in `core1_functions.ls`. | HS application requires parenthesized compound arguments; emitter handles non-literal/non-identifier arguments. | No backend blocker seen for current call form. |
| Binary expression: arithmetic | Emits parenthesized infix expression. | Emits parenthesized infix expression. | `core1_functions.ls`, `core1_let.ls`, negative `binary-type` fixture. | Both preserve operator and operand order. | No backend blocker seen. |
| Binary expression: comparison / equality | Emits parenthesized infix expression. | Emits parenthesized infix expression. | `core1_functions.ls`, `core1_let.ls`, negative `if-condition-type` / branch tests. | Operators are textually shared for current comparison/equality set. | No backend blocker seen. |
| `if` expression | Emits a TS ternary expression. | Emits a Haskell `if ... then ... else ...` expression. | `core1_functions.ls`, `core1_let.ls`, negative branch/condition fixtures. | Shape differs by target, but branch order and condition are preserved. | No backend blocker seen. |
| `let` expression | Emits an immediately invoked arrow function with a `const` binding and returned body. | Emits a Haskell `let ... in ...` expression. | `core1_let.ls`. | TS requires an IIFE to keep expression position; HS is direct. This is stable but should be snapshot-tested before larger nesting work. | Edd may want parity snapshots for nested `let` cases. |
| Python target rejection | CLI rejects `py` and `python` targets before emission. | Not applicable. | Smoke test explicitly checks rejection. | This is part of executable surface policy, not backend parity. | Keep as C1 policy evidence; no backend action. |
| Unsupported expression fallback | Emits `/* unsupported */` for unknown expression shape. | Emits `/* unsupported */` for unknown expression shape. | No direct fixture. | Since the current AST union is closed over the listed C1 expression forms, this should be unreachable for current C1. For future AST additions it could silently produce invalid output. | This is a Y5 follow-up candidate: make unsupported backend cases fail explicitly. |

## Backend parity risks

1. Module preservation is comment-only in both emitters. This is stable but weak if C1 intends target-language module identity.
2. Foreign imports are intentionally divergent across targets: TS uses `CppForeignRuntime`; HS uses `foreign import ccall` and `IO`.
3. Top-level foreign-call declarations emit as a TS runtime-taking function and as a Haskell IO binding. This should remain visible in docs and fixtures.
4. `let` emission is semantically comparable but structurally different: TS IIFE versus Haskell `let`.
5. Unsupported expression fallbacks currently emit a comment string rather than throwing or reporting a backend diagnostic.

## Backend evidence questions for Ed

Ed should decide whether these backend statuses are enough for language admission:

```text
module identity preserved only as comments
foreign imports with target-specific runtime shape
top-level foreign-call declarations as TS runtime functions / HS IO actions
comment-based unsupported fallback remaining unreachable for current AST
```

## Backend evidence questions for Edd

Edd should decide whether the following should become verification artefacts:

```text
snapshot fixtures for TypeScript and Haskell output
a direct nested-call snapshot fixture
a direct nested-let snapshot fixture
a string-FFI fixture if string FFI is admitted
an explicit unsupported-backend test once backend errors are hardened
```

## Eddy next-pass recommendation

The next Eddy pass should be:

```text
Y2-P1: Backend parity gap list.
```

That pass should classify each parity issue as one of:

```text
format-only
target-runtime convention
fixture/snapshot requirement
language-admission question for Ed
verification-policy question for Edd
backend patch candidate for Eddy
```

The likely concrete follow-up after Y2 is Y5 rather than immediate emitter formatting: replace or guard the silent `/* unsupported */` backend fallback so future AST additions fail visibly.
