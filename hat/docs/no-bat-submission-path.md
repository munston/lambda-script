# Bat-free submission path target

The project goal is for submission and shipping to be operable without calling `.bat` files. A `.bat` may remain temporarily as a compatibility launcher on Windows, but the maintained and invoked command source should be `.hat`.

## Operating rule

The execution form is:

```text
cabal run src/hat -- FILE.hat [ARGS...]
```

or, after Hat has installed itself:

```text
hat FILE.hat [ARGS...]
```

The `.hat` source is then checked, compiled to a generated Haskell backend when stale, and executed through Cabal. The generated `.hs` backend is cache/output.

## Translation rule

A legacy command button can become Hat only after it has been reduced to simple linewise invocations. If it already fits the subset, translation is an extension change plus insertion of the first-line hash:

```text
old: name.bat
new: name.hat
```

The contents should not carry batch fallback logic forward. Unsupported batch constructs should be removed rather than implemented in Hat.

## Submission wrappers

The submission surface should eventually be represented as Hat files such as:

```text
land-anything.hat
onepush.hat
gadget-amalgamate.hat
gadget-sync-all.hat
```

These wrappers should call the underlying accepted gizmo/forks entrypoints as ordinary per-line command invocations. They should not call `.bat` files.

## Readiness condition

The submission process becomes fully usable from an agent kernel when:

```text
1. Hat is installable and runnable in the kernel.
2. Every submission button used by the agent has a `.hat` source.
3. No `.hat` source invokes a `.bat` file.
4. Generated Haskell backends live under `.hat-cache/` and are treated as cache.
5. The accepted gizmo interface accepts the resulting Hat-mediated command output.
```

The current Hat runtime satisfies item 1 locally and provides the language needed for items 2 through 4. The next implementation pass should convert the actual submission wrappers into `.hat` files and exercise them against a non-destructive lane operation.
