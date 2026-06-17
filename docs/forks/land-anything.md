# Land anything

`land-anything.bat <patch.json>` is the canonical JSON landing entry point.

The patch payload decides where it belongs. Target-specific landing buttons may
exist as visible labels, but they are conveniences only. The authoritative
routing data is inside the patch.

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
  "title": "Example",
  "files": []
}
```

The landing button resolves this to:

```text
integration: origin/gadgets/<gizmo>/<gadget>/main
lane:        gadget-agents/<gizmo>/<gadget>/<agent>
```

A repository-level patch may use:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "edd",
  "target": {
    "kind": "repo"
  },
  "title": "Example",
  "files": []
}
```

which resolves to the repository main target and the corresponding
`agents/<agent>` lane.

The button lands the patch to the resolved lane only. Shipping remains a
separate onepush operation.
