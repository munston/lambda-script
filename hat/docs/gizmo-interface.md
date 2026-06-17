# Hat gizmo interface

Hat is now intended to operate as its own gizmo with one primary gadget:

```text
hat/hat
```

The gadget root is:

```text
hat/
```

The manifest is:

```text
examples/gizmos/hat.gizmo.json
```

## Branch routing

The Hat integration branch is:

```text
gadgets/hat/hat/main
```

The Hat agent lane template is:

```text
gadget-agents/hat/hat/{agent}
```

A web agent assigned to Hat should target only the Hat gadget. It should not submit changes to LambdaScript core, forks, gizmo tooling, Wires/self, or other protected tooling unless it has a separate explicit assignment.

## Owned paths

Hat owns:

```text
hat/
examples/gizmos/hat.gizmo.json
```

Incoming diffs for ordinary Hat development should stay inside those paths.

## Connected tooling

Hat imports the LambdaScript core tooling gizmo as a read-only toolchain. This gives Hat access to the gizmo/forks submission machinery without granting write authority over that machinery.

This preserves the intended authority boundary:

```text
Hat agents may edit Hat.
Hat agents may use connected tooling.
Hat agents may not edit connected tooling by accident.
```

## Public command model

Hat itself has a single public command shape:

```text
hat FILE.hat [ARGS...]
```

Everything else is internal. Hash verification, stale generated-Haskell detection, `.hs` emission, and `cabal run` invocation are implementation details of Hat.

## Current command exports

The gizmo manifest exposes:

```text
hat
install
check-install-source
```

These are thin command entries for connected gizmos and agent workspaces. They should remain small and should not grow into a second control surface.

## Incoming web-agent diffs

A web agent should submit either:

```text
1. a JSON patch targeting hat/hat
2. a lane diff against gadget-agents/hat/hat/<agent>
```

The preferred durable form is the JSON patch route once the receiving interface supports it. Direct lane diffs can be used as a transitional carrier, but they should eventually be replay-ledger-native.
