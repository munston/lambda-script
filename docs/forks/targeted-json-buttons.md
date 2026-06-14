# Targeted JSON patches and agent buttons

A targeted JSON patch carries its own gadget destination. The operator supplies only the file path through an agent-specific button.

Example:

```bat
guy-land-json.bat C:\Users\guyas\Downloads\some_patch.json
```

The button hardcodes the agent. `guy-land-json.bat` always lands as `guy`; `eddy-land-json.bat` always lands as `eddy`. The target is read from the JSON patch:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "guy",
  "target": {
    "kind": "gadget",
    "gizmo": "lambdascript",
    "gadget": "core",
    "profile": "quick"
  },
  "title": "Short description",
  "files": [
    {
      "op": "upsert",
      "path": "relative/path.txt",
      "encoding": "utf-8",
      "content": "file contents\n"
    }
  ]
}
```

`target.profile` is optional and defaults through the existing gadget landing path. Use `"profile": "gizmo"` or `"profile": "full"` when a stronger gate is needed. `"gadget"` may also be written as `"lane"` for operator-facing terminology.

The default mode validates that the patch's `agent` field matches the hardcoded button. This prevents accidentally landing an `eddy` patch through `guy-land-json.bat`.
