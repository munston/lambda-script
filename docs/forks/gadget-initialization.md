# Gadget initialization for independent gizmos

This note records the accepted initialization route for forks-backed gizmo/gadget work.

## Rule

A new package must be initialized under its owning gizmo/gadget identity. Do not place an independent package inside the `lambdascript` gizmo merely to satisfy a landing error. The `lambdascript` gizmo is the core machinery supplier. It owns the compiler, forks tooling, gizmo tooling, and related core documentation. Independent packages should use their own gizmo name.

Examples:

```text
metrics-lab/image-metrics
audio-lab/wavproc
```

Use `lambdascript/<gadget>` only when the gadget is actually part of the LambdaScript core gizmo.

## Accepted initialization command

Run from the repository root:

```bat
cd /d "C:\Users\guyas\Desktop\codebase\7\ollama.wires\foreign-language\lambda-script"

git fetch origin --prune

git restore --source=origin/gadgets/lambdascript/core/main -- forks.bat scripts/forks/forks_dispatch.py scripts/forks/gadget_branches.py scripts/forks/forks.py

python scripts\forks\gadget_branches.py init <gizmo> <gadget>

python scripts\forks\gadget_branches.py status <gizmo> <gadget>
```

For the known metrics gadget:

```bat
python scripts\forks\gadget_branches.py init metrics-lab image-metrics

python scripts\forks\gadget_branches.py status metrics-lab image-metrics
```

For an independent WAV processor package, use an owning gizmo outside `lambdascript`, for example:

```bat
python scripts\forks\gadget_branches.py init audio-lab wavproc

python scripts\forks\gadget_branches.py status audio-lab wavproc
```

Expected status shape:

```text
gadget <gizmo>/<gadget>
target origin/gadgets/<gizmo>/<gadget>/main
gadgets/<gizmo>/<gadget>/main: even
gadget-agents/<gizmo>/<gadget>/ed: even
gadget-agents/<gizmo>/<gadget>/edd: even
gadget-agents/<gizmo>/<gadget>/eddy: even
gadget-agents/<gizmo>/<gadget>/guy: even
```

The supported configured lanes are currently:

```text
ed
edd
eddy
guy
```

Do not invent branch suffixes or agent names.

## Landing patches after initialization

A JSON patch must target the same initialized gizmo/gadget:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "<gizmo>",
    "gadget": "<gadget>"
  }
}
```

For an independent WAV processor, the target should be the independent gizmo/gadget, for example:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "audio-lab",
    "gadget": "wavproc"
  }
}
```

It should not be:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "lambdascript",
    "gadget": "wavproc"
  }
}
```

That target incorrectly asks the LambdaScript core gizmo to own `wavproc`.

Submit through the assigned agent button:

```bat
edd-land-json.bat "C:\path\to\patch.json"
```

Use the button matching the declared agent in the JSON patch.

## Amalgamation

After the lane-local patch lands, amalgamate the same gizmo/gadget:

```bat
forks.bat amalgamate-all --gadget <gizmo> <gadget> --agents edd --apply
```

Then inspect status:

```bat
python scripts\forks\gadget_branches.py status <gizmo> <gadget>
```

For an independent WAV processor under `audio-lab/wavproc`:

```bat
forks.bat amalgamate-all --gadget audio-lab wavproc --agents edd --apply

python scripts\forks\gadget_branches.py status audio-lab wavproc
```

The expected final state is that the selected lane is even with the gadget integration branch.

## Common error

This error:

```text
agent-land-json: manifest for lambdascript has no gadget wavproc
```

means the patch is being routed to `lambdascript/wavproc`. That is a target error for an independent package. Do not repair it by adding `wavproc` to the `lambdascript` gizmo. Retarget the patch to the owning gizmo/gadget and initialize that gizmo/gadget with `gadget_branches.py init`.

## Separation of responsibilities

`gadget_branches.py init <gizmo> <gadget>` creates and aligns the gadget integration branch and the configured agent lanes.

`edd-land-json.bat` and the other agent buttons submit JSON patches through one configured agent lane.

`forks.bat amalgamate-all --gadget <gizmo> <gadget> --agents <agent> --apply` captures the selected lane delta, applies it to the gadget integration branch, and syncs the selected lane back to the integration branch through the forks tooling.

Do not use raw Git mutation, direct GitHub mutation, promotion, or manual sync for the normal initialization-and-land path.
