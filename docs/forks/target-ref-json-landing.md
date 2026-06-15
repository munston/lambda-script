# Target refs in JSON landing

Targeted JSON landing lets one-argument agent buttons apply patches to a declared gadget target.

The public button shape stays fixed:

```bat
edd-land-json.bat path\to\patch.json
```

The patch carries the target and transaction policy:

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

For fast acceptance, use `promote: false`, `sync: false`, and `history: false`. This lands to the gadget integration branch and skips repository-level promotion and lane fan-out.

For promotion, set `promote: true`. The promotion path may be further controlled:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "lambdascript",
    "gadget": "core",
    "profile": "gizmo",
    "promote": true,
    "promote_profile": "gizmo",
    "sync": false,
    "history": true,
    "repository_sync": false
  }
}
```

`sync` controls gadget-agent lane alignment after promotion. `repository_sync` controls repository-level agent lane synchronization after pushing `main`. Leaving `repository_sync` absent preserves the historical default, which syncs repository agent lanes.
