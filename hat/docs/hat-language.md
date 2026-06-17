# Hat language pass

Hat replaces shell-specific buttons with a small line-oriented source format.

Public invocation has exactly one shape:

```text
hat FILE.hat [ARGS...]
```

There are no public Hat subcommands. Hash checking, backend emission, cache checking, and Cabal invocation are internal behaviours.

## Source hash

A `.hat` file starts with:

```text
# hat-hash: <hash>
```

The hash is computed over the rest of the file. Hat refuses to run when the declared value differs from the computed value.

## Backend cache

Hat emits generated Haskell into:

```text
.hat-cache/<source-name>-<source-hash>-<backend-version>.hs
```

The generated backend records the source hash and backend version. Hat writes it only when it is missing or stale. Local build products are ignored by `hat/.gitignore`.

## Current command subset

```text
hat 0
say TOKENS...
cd PATH
mkdir PATH
run PROGRAM ARGS...
cabal-run TARGET ARGS...
install-copy EXECUTABLE BIN_DIR
```

Blank lines and comment lines are ignored. Double-quoted strings are treated as single tokens. Backslash escapes the next character.

## Runtime arguments

Runtime arguments are supplied after the `.hat` file. Generated backends support these tokens:

```text
$1
$2
$@
```

`$@` expands to all runtime arguments.

## Local verification

The current implementation was built and exercised in the agent kernel with:

```text
cabal build src/hat
cabal run src/hat -- installation_script.hat
./bin/hat installation_script.hat
./bin/hat args_smoke.hat alpha beta gamma
```

The install path produced `bin/hat`, and the argument smoke verified `$1`, `$2`, and `$@` expansion through generated Haskell into an invoked process.
