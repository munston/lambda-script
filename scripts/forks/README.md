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

Gadget mode now begins with a non-destructive replay-materialisation audit. The audit reads each selected agent's gadget replay ledger from the gadget integration branch, checks that every payload object exists, and verifies final materialisation using timestamped last-writer-wins semantics: historical entries may be superseded across agents, so final file content is checked against the latest replay fingerprint touching each path.

The audit prints each replay entry before any lane is rewound:

```text
gadget replay materialisation audit for lambdascript/core
ed: ledger entries=...
  #N: files=... title=...
edd: ledger entries=...
  #N: files=... title=...
eddy: ledger entries=...
  #N: files=... title=...
ok gadget replay materialisation audit passed
```

Use this before accepting claims that a patch was or was not applied. If a replay-ledger payload is missing, or if the final branch content does not match the latest timestamped replay fingerprint for a strict touched path, `amalgamate-all` fails before destructive lane sync. Per-agent planning notes under `docs/agents/` are warning-only by default; pass `--strict-agent-docs` to make them fatal.

Optional stricter mode:

```bat
forks.bat amalgamate-all --gadget lambdascript core --require-ledgers
```

This fails if any selected agent has no gadget replay ledger. The default merely reports a missing ledger so that agents with no submitted patch do not block unrelated work.

After all selected agents have been visited, gadget mode final-syncs the selected gadget-agent lanes to the gadget integration branch and repeats the replay-materialisation audit unless `--skip-replay-audit` is given.

## Important distinction

`forks.bat amalgamate-all --apply` without `--gadget` only processes repository lanes:

```text
agents/ed
agents/edd
agents/eddy
```

For the current LambdaScript core gadget workflow, use:

```bat
forks.bat amalgamate-all --gadget lambdascript core --apply
```

## Terminal invariant

After a successful apply, no separate sync step is expected for the selected lane family.

Repository mode leaves selected `agents/<name>` lanes even with `origin/main`.

Gadget mode leaves selected `gadget-agents/<gizmo>/<gadget>/<name>` lanes even with `origin/gadgets/<gizmo>/<gadget>/main` and proves the selected agents' replay-ledger entries are materialised on that branch.

`main` is never rewound. Agent lanes may be rewound only after their unique direct work has been captured or their replay-backed content has been proven materialised.

## Advisory agent-note drift

Per-agent planning notes under `docs/agents/` are coordination artefacts. If their replay fingerprint drifts from the materialised file, gadget amalgamation prints a warning by default and continues. Use `--strict-agent-docs` when those notes must be treated as strict replay material.
