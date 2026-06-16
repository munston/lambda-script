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

## First materialisation support

A newly initialized independent gizmo/gadget may not have a manifest or verification profile yet. This is a real bootstrap state:

1. `gadget_branches.py init <gizmo> <gadget>` has created `origin/gadgets/<gizmo>/<gadget>/main`.
2. The four configured lanes exist and are even with that target.
3. The first JSON patch must materialize the package files and any manifest/profile files needed by later manifest-gated operations.

The agent buttons support this bootstrap case through an explicit target flag:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "<gizmo>",
    "gadget": "<gadget>",
    "first_materialisation": true,
    "sync": false
  }
}
```

When `first_materialisation` is true, `agent_land_json.py` lands the patch by explicit gadget target-ref:

```text
origin/gadgets/<gizmo>/<gadget>/main
```

It bypasses the manifest-gated `gadget_land_json` profile lookup only for this first materialising patch. This is proper tooling support for the bootstrap corner case, rather than an operator workaround.

For an independent WAV processor under `audio-lab/wavproc`, the patch target should be:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "audio-lab",
    "gadget": "wavproc",
    "first_materialisation": true,
    "sync": false
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

## Later patch landing

After the first materialisation has created the independent package manifest/profile files, ordinary manifest-gated landing may be used without `first_materialisation`:

```bat
edd-land-json.bat "C:\path\to\patch.json"
```

Use the button matching the declared agent in the JSON patch.

## Amalgamation

After lane-local work exists, amalgamate the same gizmo/gadget:

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

This error:

```text
agent-land-json: manifest for <gizmo> has no gadget <gadget>
```

on a genuinely new independent gizmo/gadget means the first patch should set `target.first_materialisation=true`.

## Separation of responsibilities

`gadget_branches.py init <gizmo> <gadget>` creates and aligns the gadget integration branch and the configured agent lanes.

`edd-land-json.bat` and the other agent buttons submit JSON patches through one configured agent lane. With `target.first_materialisation=true`, they can also materialize the first package patch onto the explicit gadget target-ref when no manifest/profile exists yet.

`forks.bat amalgamate-all --gadget <gizmo> <gadget> --agents <agent> --apply` captures the selected lane delta, applies it to the gadget integration branch, and syncs the selected lane back to the integration branch through the forks tooling.

Do not use raw Git mutation, direct GitHub mutation, promotion, or manual sync for the normal initialization-and-land path.
