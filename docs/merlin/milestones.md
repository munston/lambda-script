# Merlin embodiment milestones

## M0: Isolated gadget scaffold

Merlin exists as `merlin/mock-detector` with its own owned paths, target ref, agent lane template, commands, and verification profiles.

## M1: Branch-real gadget operation

Initialise the gadget branch and lanes:

```bat
forks.bat gadget-init merlin mock-detector
forks.bat gadget-status merlin mock-detector
```

Merlin work should then land through the gadget target:

```bat
forks.bat land-json-file --target-ref origin/gadgets/merlin/mock-detector/main eddy patch.json
```

## M2: Manifest enforcement

The gizmo validator must accept and inspect branch-model fields: `target_ref`, `integration_branch`, `agent_branch_template`, `owned_paths`, `verification_profiles`, `imports`, and `connections`.

## M3: Gear receipts

Merlin reports must be structured as gear receipts. A report should say which gears were evaluated, whether each gear passed, and which source locations triggered findings.

## M4: Candidate gating

Forks verification should be able to call Merlin in gated mode. Error-grade gear failures should block candidate promotion. Warning-grade findings should be reviewable without blocking ordinary detector source that legitimately talks about mocks and stubs.

## M5: LambdaScript import

Once the gadget branch is stable, `lambdascript/core` can import `merlin/mock-detector` as a read-only command provider. At that stage LambdaScript receipts can include a Merlin scan without giving Merlin write access to LambdaScript source.

## M6: Economic use

Gremlin credit should count only work that satisfies compilation, tests, forks receipts, and Merlin gear checks. Compile-only success becomes insufficient once Merlin is part of the receipt gate.
