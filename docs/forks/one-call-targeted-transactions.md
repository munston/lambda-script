# One-call targeted JSON transactions

A targeted JSON patch may now describe the entire landing transaction. The operator supplies only the patch path to the correct agent button:

```bat
guy-land-json.bat C:\Users\guyas\Downloads\patch.json
```

The patch target controls landing, promotion, history, and sync:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "metrics",
    "gadget": "image-metrics",
    "profile": "quick",
    "promote": true,
    "sync": true,
    "history": true
  }
}
```

When `promote` is true, the button lands the patch to the gadget integration branch, aligns gadget-agent lanes to the accepted gadget head, promotes the gadget to `main`, records main-history when enabled, syncs repository agent lanes through the promotion path, and finally aligns the gadget branch and gadget-agent lanes to `origin/main`.

The older commands remain implementation primitives. The intended operator surface is the one-argument agent button.
