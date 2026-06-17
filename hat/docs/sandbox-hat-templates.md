# Hat sandbox templates

This directory contains `.hat` wrappers for the existing sandbox command interface.

The templates are intentionally small:

```text
hat/templates/sandbox/sandbox.hat
hat/templates/sandbox/onepush.hat
hat/templates/sandbox/land.hat
```

They do not define a new submission mechanism. They call the existing sandbox command surface through Cabal:

```text
cabal run sandbox -- ...
```

## Intended placement

A provisioned sandbox directory should contain its normal `sandbox.json` and one or more copied Hat templates. Since Hat-generated backends run with the `.hat` file directory as the working directory, the sandbox config is read from that directory.

## Invocation examples

```text
hat sandbox.hat help
hat onepush.hat
hat onepush.hat --ship
hat land.hat patch.json
```

Equivalent generic form:

```text
hat sandbox.hat onepush --ship
hat sandbox.hat land patch.json
```

## Boundary

These wrappers replace `.bat` launchers only. The authoritative interface remains the existing sandbox/gizmo command-line interface. Hat supplies portability, first-line hashing, generated Haskell backend caching, and strict rejection of richer batch semantics.
