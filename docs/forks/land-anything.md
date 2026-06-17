# land-anything

`land-anything.bat <patch.json>` is the canonical JSON patch entry point.

The patch payload is the routing authority. The payload supplies the author/agent and the target object. The landing tool derives the integration ref and agent lane from that information.

Example gadget target:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "edd",
  "target": {
    "kind": "gadget",
    "gizmo": "lambda-script",
    "gadget": "lambda-script"
  },
  "title": "Example",
  "files": []
}
```

This resolves to:

```text
integration: origin/gadgets/lambda-script/lambda-script/main
lane:        gadget-agents/lambda-script/lambda-script/edd
```

The lane is treated as a disposable carrier. Before landing the new patch, the tool reconstructs the lane from the current integration target plus durable replay entries already recorded for that agent and target. Branch topology is not authoritative: stale, ahead, behind, reset, or divergent lane carriers are handled through replay recovery when the replay payloads are present and valid.

A landing fails when the durable replay data is incomplete or cannot be applied, when the new patch cannot be applied after replay, or when the remote lane changes during the final leased push.
