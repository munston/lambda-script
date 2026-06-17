# Process result pruning contract

Forks tools are read by humans and models. Raw subprocess output is treated as a
costly transport format, not as the public interface. Each tool should report a
hierarchical result tree with aggressive pruning.

## Rule

Successful inner processes collapse to one line:

```text
gadget ingest: ok.
safe gadget amalgamation: ok.
```

Failed inner processes keep only the diagnostic core:

```text
safe gadget amalgamation: failed (exit 1).
  ghc: error:
  ...
```

The full stdout/stderr stream may be useful for local debugging, but it should
not be the default output of orchestration tools. The default surface should be
small enough to feed back into an agent without wasting tokens.

## Semantics

A process result has:

```text
label
argv
cwd
exit code
stdout
stderr
children
```

If `exit code == 0` and all children succeeded, the text output may be discarded
by default. If the exit code indicates failure, the output is pruned by scanners
for compiler and runtime diagnostic markers such as `error:`, `fatal:`,
`Traceback`, `AssertionError`, `Cabal-`, `ghc-`, `npm ERR`, `not found`, and
similar failure phrases.

The caller decides whether a child process has failed by its exit code. Text is
not parsed to infer success when the process already provided a success code.

## Policy

Transport commands should stay language-neutral. Cabal, npm, GHC, Python, image
tools, and other inner tools may be executed as explicit verification gates, but
their output should be summarized through the same process-result layer.
