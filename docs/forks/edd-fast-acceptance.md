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
    "history": false,
    "refresh": true
  },
  "files": []
}
```

The same convention applies to other gadget targets by changing `gizmo`, `gadget`, and `profile`.

Fast acceptance does:

```text
fetch origin
refresh the gadget integration branch against origin/main
resolve gadget target ref
import JSON patch onto the refreshed gadget integration target
run the selected verification profile
dry-run push
push to gadgets/<gizmo>/<gadget>/main
print gadget status
```

The refresh step treats `main` as the replaceable authority:

```text
even       -> apply the patch
ahead-only -> apply the patch
behind-only -> reset the gadget integration branch to origin/main before applying the patch
diverged   -> rebase the gadget integration branch onto origin/main and verify before applying the patch
```

Fast acceptance intentionally skips:

```text
promotion to repository main
repository-agent lane sync
gadget-agent lane sync
main-history stamping
```

This is useful when a batch of small patches should be accepted quickly before one deliberate promotion/sync pass. The gadget branch remains a replay cache over current `main`, not an independent long-lived truth branch.

Expected local command form:

```bat
edd-land-json.bat "C:\Users\guyas\Downloads\<patch-file>.json"
```

If the patch is for a support agent, use that agent's button and make the patch's `agent` field match the button identity.
