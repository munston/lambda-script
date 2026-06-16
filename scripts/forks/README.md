# forks

Repository tooling for coordinating side-lane agent branches and gadget-agent lanes.

## Batch dispatch

`forks.bat` is intentionally minimal. It changes to the repository root and forwards the original command line to:

```bat
python scripts\forks\forks_dispatch.py %*
```

The Python dispatcher performs subcommand routing. This avoids the Windows batch `%1` through `%9` forwarding limit and preserves long commands such as:

```bat
forks.bat accelerator init lambdascript core lsc1 --agents ed edd eddy --slots 7 --objective "Reach the first compiler completion stage"
```

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

## Gadget JSON landing

Gadget JSON landing records replay history and advances the gadget integration branch. It must not silently force-align every gadget-agent lane, because that masks whether propagation happened through the intended amalgamation stage.

Default landing:

```bat
python scripts\forks\gadget_land_json.py --require-file lambdascript core edd "<patch>.json"
```

Default behaviour:

```text
append the submitting agent's replay ledger
materialise the patch on origin/gadgets/<gizmo>/<gadget>/main
leave gadget-agent lanes untouched
print gadget status
```

Explicit repair/alignment is still available, but it must be requested:

```bat
python scripts\forks\gadget_land_json.py --require-file --align-lanes lambdascript core edd "<patch>.json"
```

Use `--align-lanes` only when the operator intentionally wants immediate lane force-alignment. The normal collaborative workflow should leave lane propagation to gadget amalgamation.

`--no-align-lanes` remains accepted for compatibility and is now the default.

For one-button agent landers, omitted `target.sync` now defaults to `false`. A patch must explicitly set `"sync": true` to request immediate lane alignment.

## Accelerator planning

An accelerator is a tracked staged workflow template for parallel agent development. It keeps each agent on a continuous development sequence while making overlap visible before patches collide.

Create an accelerator:

```bat
forks.bat accelerator init lambdascript core lsc1 --agents ed edd eddy --slots 7 --objective "Reach the first compiler completion stage"
```

Set slot objectives and agent tracks:

```bat
forks.bat accelerator set-slot lambdascript core lsc1 1 --objective "Boolean logic and backend parity"
forks.bat accelerator set-agent lambdascript core lsc1 edd 1 --responsibility "Boolean surface syntax and typechecking" --paths "glc/src/parser/,glc/src/core/"
forks.bat accelerator set-agent lambdascript core lsc1 eddy 1 --responsibility "Backend parity and smoke snapshots" --paths "glc/src/codegen/,glc/test/"
```

Print the packet for a working turn:

```bat
forks.bat accelerator packet lambdascript core lsc1 edd
```

Record failed and accepted attempts:

```bat
forks.bat accelerator attempt lambdascript core lsc1 edd 1 --status failed --error-file err.txt
forks.bat accelerator accept lambdascript core lsc1 edd 1 --ledger-path forks/replay-ledger/gadgets/lambdascript/core/edd.json --sequence 3
```

Advance only after every active agent is accepted or skipped:

```bat
forks.bat accelerator advance lambdascript core lsc1
```

The three-slot cadence is:

```text
current slot: full plan exists; submit patch and loop until verification accepts it
next slot: extend the prior lookahead into a complete plan
plus-two slot: add or refresh the lookahead objective
```

The accelerator is non-destructive. It never lands patches, rewinds lanes, promotes branches, or syncs agents. It coordinates the work that is then consumed through JSON landing and audited gadget amalgamation.

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

Gadget mode begins with a non-destructive replay-materialisation audit. The audit reads each selected agent's gadget replay ledger from the gadget integration branch, checks that every payload object exists, and verifies final materialisation using timestamped last-writer-wins semantics: historical entries may be superseded across agents, so final file content is checked against the latest replay fingerprint touching each path.

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

Use this before accepting claims that a patch was or was not applied. If a replay-ledger payload is missing, or if the final branch content does not match the latest timestamped replay fingerprint for a touched path, `amalgamate-all` fails before destructive lane sync.

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
