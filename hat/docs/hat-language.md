# Hat language pass

Hat replaces shell-specific buttons with a deliberately small line-oriented source format.

Public invocation has exactly one shape:

```text
hat FILE.hat [ARGS...]
```

There are no public Hat subcommands. Hash checking, backend emission, cache checking, and Cabal invocation are internal behaviours.

## Boundary

Hat is not intended to support most of `cmd.exe` or batch scripting. It is only a small, auditable subset suitable for command-button files that have already been reduced to per-line command invocations.

A select `.bat` file can be translated to `.hat` by changing the extension only when it already passes this subset check. In practice that means:

```text
allowed:
  rem comments
  :: comments
  cd PATH
  cd /d PATH
  mkdir PATH
  PROGRAM ARG ARG ...
  quoted single-token arguments
  %1..%9 positional arguments
  %* all-arguments forwarding

rejected:
  @echo off
  set / setlocal / endlocal
  if / for / goto / call / shift
  labels
  errorlevel control flow
  && / || fallback chains
  pipes
  redirection
  ambient %VARIABLE% expansion
  %~dp0 and other batch path modifiers
```

This is an intentional guardrail. Hat should not be maintained toward general batch compatibility. If an existing `.bat` needs unsupported features, the file should be simplified into explicit per-line invocations before becoming `.hat`.

## Source hash

A `.hat` file starts with a first-line hash over the rest of the file. For files expected to be close to batch syntax, prefer:

```text
rem hat-hash: <hash>
```

Hat also accepts:

```text
# hat-hash: <hash>
:: hat-hash: <hash>
```

Hat refuses to run when the declared value differs from the computed value.

## Backend cache

Hat emits generated Haskell into:

```text
.hat-cache/<source-name>-<source-hash>-<backend-version>.hs
```

The generated backend records the source hash and backend version. Hat writes it only when it is missing or stale. Local build products are ignored by `hat/.gitignore`.

## Current command subset

The current command subset is direct command invocation rather than a separate Hat command vocabulary:

```text
rem hat 0
cd PATH
cd /d PATH
mkdir PATH
PROGRAM ARG ARG ...
```

Blank lines and comment lines are ignored. Double-quoted strings are treated as single tokens. Backslash escapes the next character.

## Runtime arguments

Runtime arguments are supplied after the `.hat` file. Generated backends support these tokens:

```text
%1
%2
%*
$1
$2
$@
```

`%*` and `$@` expand to all runtime arguments.

## Generated Haskell backend

The generated `.hs` file is a cache/output, not the authority. The `.hat` source is the maintained file. Hat uses the first-line source hash and backend-version marker to avoid null rewrites.

## Local verification

The current implementation was built and exercised in the agent kernel with:

```text
cabal build src/hat
cabal run src/hat -- installation_script.hat
./bin/hat installation_script.hat
./bin/hat passthrough.hat alpha beta gamma
```

The install path produced `bin/hat`, and the argument smoke verified `%1`, `%2`, and `%*` expansion through generated Haskell into an invoked process.
