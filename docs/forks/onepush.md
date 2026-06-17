# Onepush button contract

`onepush-<agent>.bat` is the single high-level submission button for an agent.

There are no mode words. The only behavioural switch is `--ship`.

Without `--ship`, onepush submits a checkpoint to the relevant lane and stops:

- gadget work goes to `gadget-agents/<gizmo>/<gadget>/<agent>`
- repository work goes to `agents/<agent>`

With `--ship`, onepush submits first when a source folder is supplied, then
amalgamates and syncs.

## Gadget checkpoint

```bat
onepush-edd.bat lambda-script lambda-script ^
  "C:\path\to\projects\lambda-script" ^
  --dest "projects\lambda-script" ^
  --replace ^
  --message "Checkpoint Haskell migration"
```

## Gadget ship

Ship existing lane work:

```bat
onepush-edd.bat --ship lambda-script lambda-script
```

Submit and ship in one call:

```bat
onepush-edd.bat --ship lambda-script lambda-script ^
  "C:\path\to\projects\lambda-script" ^
  --dest "projects\lambda-script" ^
  --replace ^
  --message "Sign over Haskell migration"
```

## Repository-agent checkpoint

```bat
onepush-edd.bat --repo "C:\path\to\folder" --dest "repo/path" --replace
```

## Repository-agent ship

```bat
onepush-edd.bat --ship --repo
```

## Durability invariant

A lane head is mutable. It may be rewound by a later signover. The durable unit is
the captured submission/replay materialisation. A `onepush` checkpoint must remain
recoverable even if a later `--ship` syncs the lane back to the integration ref.

Therefore shipping must capture the lane into the submission/replay stream before
any lane sync or rewind is allowed.
