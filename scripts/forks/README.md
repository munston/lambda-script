# forks

Repository tooling for coordinating side-lane agent branches and gadget-agent lanes.

## Repository-agent amalgamation

Repository mode operates over:

```text
agents/<agent> -> origin/main
```

Plan:

```bat
forks.bat amalgamate-all
```

Apply:

```bat
forks.bat amalgamate-all --apply
```

Repository mode applies replay-ledger-backed JSON work for the repository agent lane, captures any remaining direct lane delta, replays/verifies/submits it, then final-syncs the selected `agents/<name>` lanes to the final `origin/main`.

## Gadget-agent amalgamation

Gadget mode operates over:

```text
gadget-agents/<gizmo>/<gadget>/<agent> -> origin/gadgets/<gizmo>/<gadget>/main
```

For the LambdaScript core gadget, plan:

```bat
forks.bat amalgamate-all --gadget lambdascript core
```

Apply:

```bat
forks.bat amalgamate-all --gadget lambdascript core --apply
```

Use gadget mode for JSON patches landed through gadget targets such as:

```text
target.kind: gadget
target.gizmo: lambdascript
target.gadget: core
```

Gadget mode does two things:

```text
1. If a gadget-agent lane has direct unique work, capture that lane delta before rewind, rewind the lane to the gadget integration branch, apply the captured patch to the gadget integration branch, verify, and push with freshness protection.
2. After every selected agent has been visited, sync every selected gadget-agent lane to the final gadget integration branch and assert that the selected lanes are clean.
```

If the recent work was already landed by `ed-land-json.bat`, `edd-land-json.bat`, or `eddy-land-json.bat` to `gadgets/lambdascript/core/main`, gadget mode still matters because it updates:

```text
gadget-agents/lambdascript/core/ed
gadget-agents/lambdascript/core/edd
gadget-agents/lambdascript/core/eddy
```

to that final gadget branch.

## Important distinction

`forks.bat amalgamate-all --apply` without `--gadget` only processes repository lanes:

```text
agents/ed
agents/edd
agents/eddy
```

It does not process gadget-agent lanes.

For the current LambdaScript core work, use:

```bat
forks.bat amalgamate-all --gadget lambdascript core --apply
```

## Terminal invariant

After a successful apply, no separate sync step is expected for the selected lane family.

Repository mode leaves selected `agents/<name>` lanes even with `origin/main`.

Gadget mode leaves selected `gadget-agents/<gizmo>/<gadget>/<name>` lanes even with `origin/gadgets/<gizmo>/<gadget>/main`.

`main` is never rewound. Agent lanes may be rewound only after their unique direct work has been captured.
