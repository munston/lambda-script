# LSC-1 Coordination Intake

Status: Edd-owned coordination-control document for the LSC-1 work round. This document records how Edd should intake other agents' work and how the operator should move durable work between JSON patches, agent lanes, gadget targets, and replay history.

This document does not replace Ed's language-admission account or Eddy's executable-truth account. It defines how Edd should read those outputs and decide whether to integrate, wait, or escalate.

## Purpose

`LSC1_COMPLETION_CONTROL.md` defines the stage boundary and closeout criteria for LSC-1. This intake document defines the turn-by-turn operating rule for Edd after each patch round.

The main problem this document addresses is sequencing. Edd should not produce speculative integration patches before Ed and Eddy outputs exist. Edd should also not treat direct agent-lane work as durable merely because it is visible on a branch. Durable work must be represented either by a landed JSON patch or by guarded capture/replay history.

## Current operator model

There are two valid ways for agents to work:

```text
1. Submit a JSON patch through the matching land command.
2. Commit provisional work directly to the agent's own lane.
```

The land command is target-directed. It does not mean "push this patch into the agent lane." For gadget work, the JSON patch usually declares the target:

```text
gadgets/lambdascript/core/main
```

and the replay ledger records the submitting agent. For example, an Edd gadget patch should be landed with:

```bat
edd-land-json.bat "C:\Users\guyas\Downloads\<patch>.json"
```

The patch target decides where the change lands. The agent name records authorship and replay history.

Direct lane commits are provisional working state until guarded capture has made them replayable. The guarded operator command is:

```bat
forks.bat amalgamate-all
```

This is plan-only by default. To execute the plan:

```bat
forks.bat amalgamate-all --apply
```

The command processes agents sequentially. For each active lane, it fetches origin, inspects the lane against current main, captures missing or stale lane diff history into `.forks/submissions/<agent>.json`, rewinds only the agent lane when safe, replays the captured diff onto current main, verifies, dry-run submits, submits, fetches the advanced main, and then moves to the next agent.

Main is not rewound by this tool. Only agent lanes may be rewound, and only after the lane work has been captured as replayable diff history and the lane head still matches the captured source commit.

For gadget work, landing JSON patches into `gadgets/lambdascript/core/main` may still require gadget-agent alignment afterwards:

```bat
forks.bat gadget-sync-all lambdascript core
```

`sync-all` remains ordinary lane housekeeping. It is not the guarded amalgamation command.

## Edd intake rule

At the start of every Edd implementation turn:

```text
1. Fetch or inspect the current target state.
2. Confirm whether the previous Edd JSON patch landed on its declared target.
3. Search for durable Ed outputs on the target branch.
4. Search for durable Eddy outputs on the target branch.
5. If direct lane outputs are visible but not yet durable, treat them as provisional until land-json or amalgamate-all capture makes them durable.
6. Produce only the smallest Edd patch justified by durable state.
```

Edd should not stack a new integration patch on a prior Edd patch that has not landed. If the prior Edd patch has not landed, either reissue it or stop and ask for the operator result.

## Durable output classes

Edd should treat the following as durable enough to integrate:

```text
- a landed JSON patch visible on the declared target branch
- replay-ledger history corresponding to a landed JSON patch
- captured direct-lane work after guarded amalgamate-all has replayed and submitted it
- a target-branch document created by Ed or Eddy
```

Edd should treat the following as provisional:

```text
- ordinary notes visible only on agents/<name>
- ordinary notes visible only on gadget-agents/lambdascript/core/<name>
- local files not represented by a JSON patch
- direct branch edits before guarded capture
- summaries of another agent's intentions without a target-branch artefact
```

## Non-overlap integration rule

If Ed produces a language-admission document, Edd may link it, cite it in the dependency section of `LSC1_COMPLETION_CONTROL.md`, and adjust the patch sequence around Ed's declared language increment.

Edd should not rewrite Ed's classification of admitted, provisional, or aspirational language features.

If Eddy produces an executable-truth document, Edd may link it, cite it in the dependency section of `LSC1_COMPLETION_CONTROL.md`, and adjust verification/closeout language around Eddy's proof command and fixture map.

Edd should not rewrite Eddy's status taxonomy, fixture map, target-output analysis, or proof-command details.

If both Ed and Eddy outputs are present, Edd may prepare an integration patch that updates:

```text
- Ed dependency link
- Eddy dependency link
- proof-object gate status
- provisional patch sequence
- closeout criteria
- risk register if a new risk is exposed
```

If neither is present, Edd should not expand into their lanes. The next Edd step should be either intake/control refinement or no patch.

## Decision table for Edd turns

```text
Previous Edd patch not landed:
  Reissue or wait. Do not stack.

Previous Edd patch landed; Ed/Eddy absent:
  Produce only non-overlap control refinement if needed.

Ed landed; Eddy absent:
  Link Ed output and update language-admission dependency only.

Eddy landed; Ed absent:
  Link Eddy output and update executable-truth dependency only.

Both landed:
  Update LSC-1 patch sequence around proof-fixture gate and implementation boundary.

Direct lane work visible but not captured:
  Treat as provisional. Wait for land-json or amalgamate-all capture before durable integration.

Gadget target updated:
  Expect operator to use gadget-sync-all for gadget-agent lane alignment if needed.
```

## Guardrails for Edd patches

Edd patches in this phase should:

```text
- touch docs/core/ control documents only unless Guy redirects
- avoid compiler source changes
- avoid selecting structural syntax
- avoid duplicating Ed's language catalogue
- avoid duplicating Eddy's fixture taxonomy
- record target and verification profile in the JSON patch
- preserve small replayable patch size
- include a next-turn preliminary plan
```

## Preliminary next-turn rule

After this document lands, Edd's next turn should begin by reading:

```text
docs/core/LSC1_COMPLETION_CONTROL.md
docs/core/LSC1_COORDINATION_INTAKE.md
latest Ed durable output, if any
latest Eddy durable output, if any
```

The next Edd patch should then be one of:

```text
1. Link Ed output.
2. Link Eddy output.
3. Link both outputs and revise the patch sequence.
4. Refrain from patching if no durable new input exists.
```
