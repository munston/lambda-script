# Merlin model

Merlin is a mock detector for forks-backed agent work. Its purpose is to distinguish operational progress from semantic hollowing-out. A gremlin may compile a patch by introducing a stub, dummy branch, bypass, or weakened return path; Merlin should make that kind of apparent progress visible before it is rewarded or promoted.

## Objects

A gear is a verification routine attached to a significant code junction. The gear checks that the component continues to transmit its intended semantic work rather than merely satisfying its type, interface, or compilation surface.

A gearbox is the collection of gears across a program. Because geared components compose, a gearbox can be treated as a gear for the whole program.

A mock signal is evidence that a patch has replaced semantic work with a placeholder. Early signals include explicit mock/stub language, `NotImplementedError`, unqualified `pass`, placeholder returns, dummy values, bypassed calls, and test weakening.

A Merlin scan is an auditable report over a tree of source files. It records the files scanned, the signals found, and enough location data to support review by an agent or operator.

## Gizmo placement

Merlin is initially developed in its own gizmo and its own writable gadget:

```text
gizmo:  merlin
gadget: mock-detector
branch: gadgets/merlin/mock-detector/main
lanes:  agents/<agent>/gadgets/merlin/mock-detector
```

This keeps Merlin separate while gizmos and gadgets mature. The `merlin/mock-detector` gadget may import `lambdascript/core` as a read-only toolchain so it can call forks, gizmo, or compiler commands through declared capabilities. It may not mutate LambdaScript source unless the work is later promoted through the LambdaScript gizmo's own gadget process.

## Integration target

The first operational form is a static source scan. It deliberately starts conservative: a finding is evidence for review, not a proof of fraud. Later gears can add stronger semantic checks, such as replayed behavioural tests, generated oracle fixtures, cross-version invariants, dependency boundary checks, and fork receipt comparison.

The eventual incorporation path is:

```text
merlin/mock-detector gadget -> verified Merlin integration branch -> promoted toolchain import -> LambdaScript core adopts Merlin as a declared command -> forks receipts can require Merlin scans
```

The separation is intentional. Merlin should become useful before it becomes authoritative.
