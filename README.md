# lambda-script

`lambda-script` is the language repository.

Source programs are written in LambdaScript (`.ls`). The local compiler is `glc`, kept as a TypeScript subproject under `glc/`.

Initial shape:

```text
lambda-script/
  examples/
    hello.ls
  glc/
    src/
      cli/
      core/
      parser/
      codegen/
      runtime/
    test/
```

## Getting Started

From the repository root:

```bat
install.bat
verify.bat
```

See `docs/INSTALL.md` for full instructions.

## Compiler boundary

LambdaScript code generation is deliberately limited to TypeScript and Haskell. Those are the supported backends, and backend work should preserve a clean correspondence between the TypeScript and Haskell forms.

Python is deliberately unsupported as a code generation target. LambdaScript must not emit Python, register Python as a backend, integrate Python modules through FFI, or treat Python as a supported runtime surface. Python may appear only as external tooling or as legacy input to be parsed, translated from, migrated away from, or replaced by LambdaScript-owned forms.

C++ is available only as a foreign runtime demonstration through explicit FFI examples; it is not a LambdaScript emission backend.

## Diff Spring (Bidirectional Sync)

**Generate patch from local changes:**
```bash
bash scripts/diff_spring/generate-and-drop.sh "Your description here"
```

**Interactive REPL (terminal):**
```bash
bash scripts/diff_spring/patch-repl.sh
```

**GUI Wrapper:**
```bash
python scripts/diff_spring/patch-repl-gui.py
```

**Local Web Interface (chat-style):**
```bash
python scripts/web/patch_chat.py
```

> Launch from an MSYS2 shell where `ssh -T git@github.com` already succeeds. The Python commands above are repository support scripts only; they are not LambdaScript language support, a Python backend, or Python FFI integration.

Open http://localhost:8765 in your browser. Paste JSON and submit.

## Build the compiler

```sh
cd glc
npm install
npm test
npm run build
```

## Compile a LambdaScript file locally

```sh
cd glc
npm run glc -- emit ../examples/hello.ls --target ts
npm run glc -- emit ../examples/hello.ls --target hs
```

Current `glc` is a deliberately small bootstrap compiler. It parses modules, declarations, string/int literals, variables, simple calls, and C++ foreign imports, then emits TypeScript or Haskell text. Python emission is excluded by design.
