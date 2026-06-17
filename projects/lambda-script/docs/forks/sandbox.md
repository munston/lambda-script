# Sandbox access surface

The sandbox is the agent-facing entry point for target work. An agent working inside a sandbox directory should use only:

```bat
cabal run sandbox -- onepush
cabal run sandbox -- onepush --ship
cabal run sandbox -- onepush --init-from-dir "C:\path\to\source"
cabal run sandbox -- onepush --ship --init-from-dir "C:\path\to\source"
cabal run sandbox -- land "C:\path\to\patch.json"
```

The sandbox directory contains two files:

```text
cabal.project
sandbox.json
```

`cabal.project` exposes the package that provides the `sandbox` executable. `sandbox.json` names the trusted tooling root and the target button stem. Example:

```json
{
  "tool_root": "C:\\Users\\guyas\\Desktop\\codebase\\7\\ollama.wires\\foreign-language\\lambda-script",
  "button": "lambda-script-edd"
}
```

The target button stem is produced by the targeted-button generator. For agent `edd` on `lambda-script/lambda-script`, the stem is `lambda-script-edd`.

The sandbox intentionally exposes only folder checkpoint, shipping, first materialisation from a directory, and JSON patch landing. The patch landing route resolves author and target from the patch payload itself. Target-specific landing buttons may exist as visual labels, but the canonical landing route is the patch-routed landing entry point.

A typical sandbox folder for the LambdaScript Haskell migration can use this `cabal.project` content, adjusted to the local absolute path:

```cabal
packages: C:\Users\guyas\Desktop\codebase\7\ollama.wires\projects\lambda-script\src\lambda-script
```

Then run commands from inside that sandbox folder. Success output should be one short line; failure output should name the failed stage and keep only the diagnostic core.
