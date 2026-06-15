# C1 backend parity gap list

Status: implementation pass Y2-P1 from Eddy's C1 backend/executable-surface lane.

Scope: backend evidence only. This document records gaps and parity risks between the TypeScript and Haskell emitters for the current visible C1 compiler surface. It does not decide language admission, verification policy, replay policy, or the post-C1 structural feature.

## Evidence read

This parity pass is based on the current visible compiler sources:

```text
glc/src/core/ast.ts
glc/src/parser/parser.ts
glc/src/core/check.ts
glc/src/codegen/typescript.ts
glc/src/codegen/haskell.ts
glc/src/cli/lsc.ts
glc/test/smoke.ts
```

The current AST surface includes expression forms `Literal`, `Identifier`, `CallExpression`, `BinaryExpression`, `IfExpression`, and `LetExpression`, plus top-level `Declaration`, `FunctionDeclaration`, and `ForeignImport`. The TypeScript and Haskell emitters both cover those visible forms, but several emitted-shape differences need classification before C1 is called complete.

## Gap classification keys

| Key | Meaning | Owner route |
|---|---|---|
| OK | Backend difference is expected target syntax. | Eddy records only. |
| Fixture | The behaviour should be fixed into a fixture or snapshot. | Edd decides fixture integration. |
| Admission | The construct's allowed C1 status requires language decision. | Ed decides admission/provisional/deferred. |
| Backend | The emitter should change in Eddy's lane. | Eddy prepares a backend patch. |
| Stop | Independent backend work should stop until Ed/Edd/Guy input is available. | Confer before patching. |

## Parity gap table

| Surface item | TypeScript shape | Haskell shape | Classification | Eddy note | Route |
|---|---|---|---|---|---|
| Module boundary | Emits comment `// Module: Name`. | Emits comment `-- Module: Name`. | OK / Fixture | Comment-only module boundaries are target-conventional. They do not create actual TS namespaces or Haskell modules. | Ed should decide whether C1 admits only single-module programs or comment-separated multi-module output. |
| Top-level value declaration | Emits `export const name = expr`. | Emits `name = expr`. | OK / Fixture | Expected target difference. Haskell lacks explicit type signatures for pure top-level declarations. | Edd may snapshot representative values; Ed may decide whether top-level inferred values are admitted. |
| Function declaration | Emits exported TS function with annotated parameters and result. | Emits Haskell type signature plus equation. | OK / Fixture | This is the cleanest current parity surface. | Edd should keep dual-target fixture snippets. |
| Primitive type mapping | `i32` and `f64` both become `number`; `bool` becomes `boolean`; `string` becomes `string`; `void` becomes `null`. | `i32` becomes `Int`; `f64` becomes `Double`; `bool` becomes `Bool`; `string` becomes `CString`; unknown/void-like cases become `()`. | Fixture / Admission | The target mapping is intentionally non-isomorphic at the runtime boundary. `string` and `void` deserve special attention because Haskell uses `CString`/`()`, while TS uses ordinary `string`/`null`. | Ed should mark string/void support precisely; Edd should require fixture coverage before relying on it. |
| Literal expression | Uses `JSON.stringify`, so strings and booleans use JS spelling. | Booleans become `True`/`False`, strings are JSON-quoted, numbers use `String`. | OK / Fixture | Basic literal parity is covered for values; string behaviour is less clear when a function type maps string to `CString`. | Edd can snapshot `string` use beyond top-level values if Ed admits it. |
| Identifier expression | Emits the identifier name. | Emits the identifier name. | OK | No backend gap visible. | None. |
| Pure call expression | Emits `callee(arg0, arg1)`. | Emits curried form `callee arg0 arg1`, parenthesizing non-atomic arguments. | OK / Fixture | Current smoke covers nested pure calls. | Edd should retain nested-call parity fixture coverage. |
| Binary arithmetic | Emits JS operators `+`, `-`, `*`, `/`. | Emits the same symbols. | OK / Fixture | Arithmetic operators are target-compatible enough for current scalar C1. Division semantics may diverge for `i32` but that is a language/checker question. | Ed should decide whether `/` over `i32` is admitted as-is. |
| Binary comparison except not-equal | Emits `<`, `>`, `<=`, `>=`, `==`. | Emits the same symbols. | OK / Fixture | These operators are syntactically valid in both targets. | Edd should ensure positive fixture coverage is broad enough. |
| Binary not-equal `!=` | Emits `!=`. | Emits `!=`. | Backend / Fixture | This is a real Haskell backend gap: Haskell not-equal is `/=`, while `!=` is not the ordinary Haskell operator. The parser/checker list `!=`, but smoke does not appear to assert a positive `!=` emitted snippet. | Eddy should prepare a small Haskell-emitter patch; Edd should add/keep a fixture; Ed should confirm `!=` is admitted. |
| If expression | Emits ternary `(cond ? a : b)`. | Emits `(if cond then a else b)`. | OK / Fixture | Target syntax differs but semantics align under checker-enforced bool condition and branch compatibility. | Edd should keep existing negative branch/condition diagnostics. |
| Let expression | Emits IIFE `(() => { const x = value; return body; })()`. | Emits `(let x = value in body)`. | OK / Fixture | Target syntax differs substantially but intentionally. Fixture snapshots should lock this down because regressions are easy. | Edd should own fixture integration. |
| Foreign import declaration | Emits TS wrapper taking `CppForeignRuntime` and calling `runtime.call`. | Emits `foreign import ccall ... :: ... -> IO ret`. | Fixture / Admission | Backend shapes are intentionally different. TS uses an explicit runtime object; Haskell uses FFI and IO. This boundary should be described as runtime-bearing rather than pure. | Ed should classify foreign imports carefully; Edd should require runtime-boundary fixtures. |
| Top-level declaration whose value directly calls a foreign import | Emits an exported TS function `name(runtime)` that calls the foreign wrapper. | Emits an IO binding `name :: IO ret` and `name = foreign args`; special-cases first string literal with `withCString`. | Fixture / Admission | This is a backend-supported special case, not a general call-expression rule. It should be documented as such. | Ed should decide whether direct top-level foreign-call declarations are admitted; Edd should fixture this exact pattern. |
| Foreign import call inside a pure function body | Ordinary call emission would produce `foreignName(args)` without the required TS runtime. | Ordinary Haskell expression emission would call an IO-returning foreign import in a pure expression. | Admission / Backend / Stop | This is not safely supported by the visible backend strategy. The checker treats foreign signatures like function signatures, so source may check while emitted targets become semantically invalid. | Stop before changing semantics. Ed should decide whether C1 forbids this. If admitted, Eddy needs a runtime/IO backend design and Edd needs fixtures. |
| Nested foreign call expression | Same risk as foreign call in function body: no runtime threading in generic expression emission. | Same risk: IO boundary is not handled in generic expression emission. | Admission / Backend / Stop | Only the direct top-level declaration case is visibly special-cased. | Confer before patching. |
| String arguments to foreign calls | TS passes strings through runtime call. | Direct top-level foreign call with first string literal uses `withCString`; broader cases are not visibly generalized. | Admission / Backend / Fixture | Haskell string FFI support appears narrow and first-argument/literal-specific in the direct top-level case. | Ed should keep broad string FFI provisional unless further fixtures exist. |
| Void-returning foreign imports | TS maps `void` to `null` in type position. | Haskell maps to `()` inside `IO ()`. | Admission / Fixture | This may be acceptable, but C1 needs explicit evidence if void foreign calls are relied on. | Edd fixture request if Ed admits void-returning FFI. |
| Unsupported expression fallback | Emits `/* unsupported */`. | Emits `/* unsupported */`. | Backend | Both emitters silently return a comment-like placeholder for unknown expression objects. In TS this may mask a backend bug; in Haskell the `/* */` comment form is not target-native. | Eddy should replace this with explicit target-labelled backend errors in a small patch. |
| Unsupported target `py` / `python` | CLI rejects with a design message. | Same CLI path; no backend emission. | OK / Fixture | Python destruction is explicit in CLI and smoke. | No Eddy action unless target list changes. |

## Highest-priority backend findings

### 1. Haskell `!=` emission is the clearest backend-local bug

The parser recognizes `!=` and the checker treats `==` and `!=` as equality-family operators. The TypeScript emitter can emit `!=` directly. The Haskell emitter currently emits the same string, but ordinary Haskell not-equal syntax is `/=`. This is narrowly in Eddy's lane because it concerns target emission, although Ed should confirm the operator is admitted and Edd should add fixture coverage.

Proposed later patch shape:

```text
Change Haskell binary emission so operator "!=" maps to "/=".
Add a small fixture or smoke assertion only if Edd's fixture policy allows it in the same patch.
```

### 2. Generic foreign calls are not backend-safe

Direct top-level declarations that call a foreign import are special-cased by both emitters. Generic call-expression emission is not foreign-aware. A foreign call inside a pure function body or nested expression would not thread the TS runtime and would not respect Haskell IO. This should not be fixed ad hoc by Eddy without Ed/Edd input because it touches language admission and runtime strategy.

Proposed handling:

```text
For C1, classify generic foreign calls as unsupported/provisional unless Ed admits them explicitly.
If Ed admits them, design a backend runtime/IO strategy before patching.
```

### 3. Unsupported backend fallbacks should fail clearly

Both emitters use a silent `/* unsupported */` fallback. C1 backend completion should prefer explicit target-labelled errors. This is a backend-local hardening patch that can be tested without adding a new language construct by constructing a deliberately invalid AST in a backend unit/smoke test.

Proposed later patch shape:

```text
Replace TS fallback with: throw new Error("Unsupported TypeScript expression kind: ...")
Replace HS fallback with: throw new Error("Unsupported Haskell expression kind: ...")
Add a narrow smoke assertion if acceptable.
```

### 4. String and void FFI support needs fixture evidence before broad reliance

The Haskell backend maps `string` to `CString` and imports `withCString` when a foreign signature uses strings. The currently visible special handling is narrow: direct top-level foreign call declarations with a first argument that is a string literal. Broader string FFI cases should remain provisional until evidence is added.

## Recommended routing

| Finding | Primary route | Secondary route | Suggested next action |
|---|---|---|---|
| Haskell `!=` emission | Eddy | Ed/Edd | Prepare backend-local fix plus fixture request. |
| Generic foreign calls lack runtime/IO strategy | Ed | Eddy/Edd | Decide whether C1 forbids or admits this shape. |
| Unsupported fallback comments | Eddy | Edd | Prepare explicit backend-error patch and narrow test. |
| String/void FFI breadth | Ed | Edd/Eddy | Keep provisional until fixture-backed. |
| Let/IIFE vs Haskell let shape | Edd | Eddy | Snapshot, no semantic change. |
| Pure call syntax differences | Edd | Eddy | Existing nested-call fixture likely sufficient for C1. |

## Candidate Eddy patch order after this pass

The next backend patches should remain small:

```text
Y5-P1: explicit unsupported backend errors in both emitters, with a narrow smoke assertion if acceptable.
Y2-P2: Haskell not-equal operator mapping from `!=` to `/=`, with a positive dual-emitter fixture if Ed/Edd accept `!=` as admitted.
Y2-P3: foreign-call support note or diagnostic request, depending on Ed's admission decision.
```

I rank unsupported backend errors before the `!=` fix because it improves future feature safety without deciding admission. The `!=` fix is smaller technically, but it benefits from Ed confirming the operator's admitted status and Edd confirming fixture placement.

## Preliminary next-turn plan

The next implementation turn should elaborate and implement:

```text
Y5-P1: explicit unsupported backend errors.
```

Initial concrete plan:

```text
1. Re-read `glc/src/codegen/typescript.ts` and `glc/src/codegen/haskell.ts` from current main.
2. Replace the silent fallback in `emitExpr` with a thrown TypeScript-backend error that includes the expression kind when available.
3. Replace the silent fallback in `emitHaskellExpr` with a thrown Haskell-backend error that includes the expression kind when available.
4. Add a narrow smoke assertion only if it can be done without altering language admission or verification policy. The likely test is a backend-only invalid AST object cast to `any` and passed to each emitter.
5. Keep the patch backend-local. Do not alter parser, checker, CLI target policy, or replay tooling.
6. Submit as one small JSON patch if the code and test changes remain compact. Otherwise split into code-only and test-only patches.
```

Stop condition for next turn:

```text
If testing unsupported fallback requires broad verification-policy changes, stop and produce a request to Edd instead of patching smoke.
```
