# Gadget initialization route

This document fixes the accepted route for initializing forks-backed gizmo gadgets. It is intended to prevent agents from confusing gadget initialization with manifest creation, manual branch mutation, or direct GitHub writes.

## Scope

The supported agent lanes are the configured lanes:

```text
ed
edd
eddy
guy
```

A new gizmo/gadget is initialized through the gadget branch tooling. The initializer creates or refreshes the gadget integration branch and the configured gadget-agent lanes. It is the accepted route for preparing a target such as `lambdascript/wavproc` or `metrics-lab/image-metrics` before normal lane-local patch submission.

## Accepted initialization command

Run from the repository root that contains `forks.bat`:

```bat
cd /d "C:\Users\guyas\Desktop\codebase\7\ollama.wires\foreign-language\lambda-script"

git fetch origin --prune

git restore --source=origin/gadgets/lambdascript/core/main -- forks.bat scripts/forks/forks_dispatch.py scripts/forks/gadget_branches.py scripts/forks/forks.py

python scripts\forks\gadget_branches.py init <gizmo> <gadget>

python scripts\forks\gadget_branches.py status <gizmo> <gadget>
```

Example:

```bat
python scripts\forks\gadget_branches.py init lambdascript wavproc

python scripts\forks\gadget_branches.py status lambdascript wavproc
```

Known metrics example:

```bat
python scripts\forks\gadget_branches.py init metrics-lab image-metrics

python scripts\forks\gadget_branches.py status metrics-lab image-metrics
```

Expected status shape:

```text
gadget <gizmo>/<gadget>
target origin/gadgets/<gizmo>/<gadget>/main
gadgets/<gizmo>/<gadget>/main: even
gadget-agents/<gizmo>/<gadget>/ed: even ahead=0 behind=0
gadget-agents/<gizmo>/<gadget>/edd: even ahead=0 behind=0
gadget-agents/<gizmo>/<gadget>/eddy: even ahead=0 behind=0
gadget-agents/<gizmo>/<gadget>/guy: even ahead=0 behind=0
```

## What the initializer does

`gadget_branches.py init <gizmo> <gadget>` ensures the gadget integration branch exists:

```text
gadgets/<gizmo>/<gadget>/main
```

It then ensures the configured agent lanes exist and are aligned to the gadget integration branch:

```text
gadget-agents/<gizmo>/<gadget>/ed
gadget-agents/<gizmo>/<gadget>/edd
gadget-agents/<gizmo>/<gadget>/eddy
gadget-agents/<gizmo>/<gadget>/guy
```

The command is allowed to create and align these branches through the forks/gadget tooling. Agents should not replace this with raw Git branch creation, direct pushes, direct GitHub mutation, promotion, or manual sync commands.

## What not to do

Do not use `gizmo init` for this. That command creates a fresh empty gizmo manifest and is not the accepted route for initializing a new gadget inside the current forks-backed workflow.

Do not manually edit `examples/gizmos/*.gizmo.json` as a substitute for initialization.

Do not use raw `git push`, direct GitHub connector writes, promotion commands, or ad hoc branch syncs as a substitute for gadget initialization.

Do not invent extra agent lanes. Use the configured lanes: `ed`, `edd`, `eddy`, and `guy`.

## Submitting work after initialization

After initialization, submit normal patches through the assigned lane-local submission button. For Edd this means:

```bat
edd-land-json.bat "C:\path\to\patch.json"
```

Then inspect the lane-local result through Git read-only commands if needed:

```bat
git show gadget-agents/<gizmo>/<gadget>/edd:<path-created-by-patch>
```

Read-only inspection is acceptable. Mutation should continue through the forks/gadget tooling.

## Amalgamating and tool-driven push

Use gadget-mode amalgamation for patches landed to gadget-agent lanes:

```bat
forks.bat amalgamate-all --gadget <gizmo> <gadget> --agents edd --apply
```

For all configured lanes:

```bat
forks.bat amalgamate-all --gadget <gizmo> <gadget> --agents ed edd eddy guy --apply
```

The `--apply` route performs the guarded capture, verification, integration-branch advance, final lane sync, and push through the forks tooling. Operators should not add a separate raw `git push` step unless they are deliberately repairing tooling outside this workflow.

After amalgamation, check status:

```bat
python scripts\forks\gadget_branches.py status <gizmo> <gadget>
```

Expected result after a clean amalgamation is that the gadget integration branch exists and the selected lanes are even against it.

## Example: initialize, submit, amalgamate

```bat
cd /d "C:\Users\guyas\Desktop\codebase\7\ollama.wires\foreign-language\lambda-script"

git fetch origin --prune

git restore --source=origin/gadgets/lambdascript/core/main -- forks.bat scripts/forks/forks_dispatch.py scripts/forks/gadget_branches.py scripts/forks/forks.py

python scripts\forks\gadget_branches.py init lambdascript wavproc

python scripts\forks\gadget_branches.py status lambdascript wavproc

edd-land-json.bat "C:\Users\guyas\Downloads\edd_wavproc_haskell_learning_patch_v2.json"

forks.bat amalgamate-all --gadget lambdascript wavproc --agents edd --apply

python scripts\forks\gadget_branches.py status lambdascript wavproc
```
