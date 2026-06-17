# Land anything

`land-anything.bat <patch.json>` is the canonical JSON-patch landing surface.

The patch decides where it belongs. The operator supplies only the patch path.

A gadget patch should carry:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "edd",
  "target": {
    "kind": "gadget",
    "gizmo": "lambda-script",
    "gadget": "lambda-script"
  },
  "title": "Patch title",
  "files": []
}
```

The resolver derives:

```text
target integration: origin/gadgets/<gizmo>/<gadget>/main
agent lane:         gadget-agents/<gizmo>/<gadget>/<agent>
```

A repository patch should carry:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "edd",
  "target": {
    "kind": "repo"
  },
  "title": "Patch title",
  "files": []
}
```

The resolver derives:

```text
target integration: origin/main
agent lane:         agents/<agent>
```

If the resolved lane is already ahead-only relative to its integration target,
the next JSON patch lands on top of that lane. If the lane is even or behind,
the patch lands from the integration target. Diverged lanes are refused.
