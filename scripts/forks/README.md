# forks

Repository tooling for coordinating side-lane agent branches and gadget-agent lanes.

## Batch dispatch

`forks.bat` is intentionally minimal. It changes to the repository root and forwards the original command line to:

```bat
python scripts\forks\forks_dispatch.py %*
```

The Python dispatcher performs subcommand routing. This avoids the Windows batch `%1` through `%9` forwarding limit and preserves long commands.

## Agent JSON landing buttons

The agent buttons are lane-local:

```bat
ed-land-json.bat patch.json
edd-land-json.bat patch.json
eddy-land-json.bat patch.json
guy-land-json.bat patch.json
```

Each button lands the JSON patch only to that agent's gadget-agent branch:

```text
gadget-agents/<gizmo>/<gadget>/<agent>
```

The patch's `target` still selects the gizmo, gadget, and verification profile, but the hardcoded button ignores patch requests to promote, sync, or align lanes. This is deliberate. Agent submissions should accumulate as lane-local diffs. Audited gadget amalgamation is the only normal path that propagates those diffs to the shared gadget integration branch and then to other agent lanes.

The lane-local landing output states:

```text
scope=agent-lane-only
sync=False promote=False amalgamate=False
```

## Gadget JSON landing

Direct gadget JSON landing is still available for operator/tooling repair:

```bat
python scripts\forks\gadget_land_json.py --require-file lambdascript core ed "<patch>.json"
```

This advances `origin/gadgets/<gizmo>/<gadget>/main`. It does not align agent lanes unless `--align-lanes` is explicitly passed.

Normal agent patches should use the agent buttons, not direct gadget landing.

## Accelerator planning

An accelerator is a tracked staged workflow template for parallel agent development. It keeps each agent on a continuous development sequence while making overlap visible before patches collide.

Create an accelerator:

```bat
forks.bat accelerator init lambdascript core lsc1 --agents ed edd eddy --slots 7 --objective "Reach the first compiler completion stage"
```

Print the packet for a working turn:

```bat
forks.bat accelerator packet lambdascript core lsc1 edd
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

Gadget mode begins with a non-destructive replay-materialisation audit. The audit reads each selected agent's gadget replay ledger from the gadget integration branch, checks that every payload object exists, and verifies final materialisation using timestamped last-writer-wins semantics.

Per-agent planning notes under `docs/agents/` are warning-only by default; pass `--strict-agent-docs` to make them fatal.

After a successful apply, the selected `gadget-agents/<gizmo>/<gadget>/<name>` lanes are even with `origin/gadgets/<gizmo>/<gadget>/main`.
