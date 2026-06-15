# Edd fast-acceptance patches

Fast acceptance is the default operator mode for small Edd and support-agent patches while the gadget integration branch is being built up.

Use a targeted gadget JSON patch with:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "edd",
  "target": {
    "kind": "gadget",
    "gizmo": "lambdascript",
    "gadget": "core",
    "profile": "gizmo",
    "promote": false,
    "sync": false,
    "history": false
  },
  "files": []
}
```

The same convention applies to other gadget targets by changing `gizmo`, `gadget`, and `profile`.

Fast acceptance does:

```text
resolve gadget target ref
import JSON patch onto the gadget integration target
run the selected verification profile
dry-run push
push to gadgets/<gizmo>/<gadget>/main
print gadget status
```

Fast acceptance intentionally skips:

```text
promotion to repository main
repository-agent lane sync
gadget-agent lane sync
main-history stamping
```

This is useful when a batch of small patches should be accepted quickly before one deliberate promotion/sync pass. After several patches have accumulated and verification is stable, use a separate promotion path to advance repository `main` and align lanes.

Expected local command form:

```bat
edd-land-json.bat "C:\Users\guyas\Downloads\<patch-file>.json"
```

If the patch is for a support agent, use that agent's button and make the patch's `agent` field match the button identity.
