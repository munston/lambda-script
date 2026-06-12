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

## Diff Spring (Bidirectional Sync)

**Generate patch from local changes:**
```bash
bash scripts/diff_spring/generate-and-drop.sh "Your description here"
```

**Interactive REPL for pasting Grok patches:**
```bash
bash scripts/diff_spring/patch-repl.sh
```

Paste the full JSON patch, then press **Enter once**. The REPL automatically detects when the JSON object is complete.

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
