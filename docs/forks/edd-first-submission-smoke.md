# Edd first submission smoke

This file is a low-risk fixture for the first Edd-targeted gadget JSON submission.

The transaction is intended to exercise the targeted agent-button path without promoting the gadget branch to repository `main` and without synchronising all agent lanes.

Expected operator surface:

```bat
edd-land-json.bat path\to\edd_first_submission_smoke_patch.json
```

Expected target policy:

```json
{
  "kind": "gadget",
  "gizmo": "lambdascript",
  "gadget": "core",
  "profile": "gizmo",
  "promote": false,
  "sync": false,
  "history": false
}
```

This fixture should be accepted only as process validation. It does not change compiler, fork, gizmo, metric, or runtime behaviour.
