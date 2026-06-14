# Lambda Gizmo

`gizmo` is a TypeScript scaffold for describing separated development booths made of multiple gadgets.

A gizmo manifest declares isolated gadget roots, allowed filesystem operations, callable programs, and promotion intent. The initial tool validates manifests and prints a routing status view. It does not execute gadget commands yet; execution should be added only after command capability boundaries are explicit.

```sh
npm run build
npm test
node dist/src/cli.js validate ../../examples/gizmos/metrics-lab.gizmo.json
node dist/src/cli.js status ../../examples/gizmos/metrics-lab.gizmo.json
```

The intended development model is:

```text
gizmo = named sandboxed environment
gadget = separated program lane inside the gizmo
gadget root = virtual filesystem boundary
gadget command = declared callable interface
promotion = explicit conversion back into a forks JSON submission
```

Gadgets share declared interfaces and outputs, not arbitrary mutable source trees.
