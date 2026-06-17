# Hat web-agent diff intake

This note defines the expected shape for another web agent sending work to Hat.

## Target

The target is the Hat gadget:

```json
{
  "kind": "gadget",
  "gizmo": "hat",
  "gadget": "hat"
}
```

## Agent lane

For an agent named `web`, the carrier lane is:

```text
gadget-agents/hat/hat/web
```

For any other agent name, substitute that name into:

```text
gadget-agents/hat/hat/{agent}
```

## Integration branch

The integration branch is:

```text
gadgets/hat/hat/main
```

## Allowed file scope

The normal writable scope is:

```text
hat/
examples/gizmos/hat.gizmo.json
```

The agent should not include changes to unrelated project folders, protected self/tooling folders, or LambdaScript core machinery in a Hat patch.

## Preferred patch shape

The preferred submission is `LS_FORK_JSON_PATCH_V1` with an explicit Hat gadget target:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "web",
  "target": {
    "kind": "gadget",
    "gizmo": "hat",
    "gadget": "hat"
  },
  "title": "...",
  "files": [
    {
      "op": "upsert",
      "path": "hat/...",
      "text": "..."
    }
  ]
}
```

## Hat source rules

Hat source files are `.hat` files. Their first line carries a fingerprint over the rest of the file:

```text
# hat-hash: <hash>
```

The rest of the file is the source body. Hat validates the fingerprint before generating or executing the backend.

The public invocation form is always:

```text
hat FILE.hat [ARGS...]
```

A web agent should not introduce additional Hat subcommands unless the language itself is deliberately extended.

## Generated Haskell backend

Generated `.hs` files are cache/backends. They may be included in a patch when useful for bootstrapping, but the `.hat` source is the authority. A backend should record the originating Hat source hash so null edits can be avoided.

## Verification expectation

At minimum, a Hat development patch should preserve:

```text
cd hat && cabal build src/hat
cd hat && cabal run src/hat -- installation_script.hat
```

The installed executable should remain capable of accepting a `.hat` file as its first argument.
