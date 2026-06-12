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
      ir/
      parser/
      emit/
      backend/
      protocol/
      test/
```

## Getting Started

From the repository root:

```bat
install.bat
verify.bat
```

See `docs/INSTALL.md` for full instructions.

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

> Launch from an MSYS2 shell where `ssh -T git@github.com` already succeeds.

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
npm run glc -- ../examples/hello.ls --target ts
npm run glc -- ../examples/hello.ls --target hs
npm run glc -- ../examples/hello.ls --target py
npm run glc -- ../examples/hello.ls --target cpp
```

Current `glc` is a deliberately small bootstrap compiler. It parses modules, declarations, string/int literals, variables, and simple calls, then emits TypeScript, Haskell, Python, or C++ text.
