# Targeted onepush and land buttons

A target button pair is generated from one target definition:

```bat
create-targeted-onepush.bat <agent> <gizmo> <gadget> <source-dir> <dest-path>
```

The button name is derived. If `<gizmo>` and `<gadget>` match, the name is:

```text
<gadget>-<agent>
```

Otherwise the name is:

```text
<gizmo>-<gadget>-<agent>
```

For example:

```bat
create-targeted-onepush.bat edd lambda-script lambda-script ^
  "C:\Users\guyas\Desktop\codebase\7\ollama.wires\projects\lambda-script" ^
  "projects\lambda-script"
```

creates:

```bat
onepush-lambda-script-edd.bat
land-lambda-script-edd.bat
```

`onepush-<name>.bat` has two runtime controls:

```bat
--ship
--init-from-dir <directory>
```

Plain invocation submits the hardcoded source folder to the hardcoded gadget-agent lane:

```bat
onepush-lambda-script-edd.bat
```

`--ship` ships the current lane only. It does not re-submit the hardcoded folder first:

```bat
onepush-lambda-script-edd.bat --ship
```

`--init-from-dir` uses a supplied directory for first materialisation or re-materialisation:

```bat
onepush-lambda-script-edd.bat --init-from-dir "C:\path\to\folder"
```

It may be combined with `--ship`:

```bat
onepush-lambda-script-edd.bat --ship --init-from-dir "C:\path\to\folder"
```

`land-<name>.bat` lands one JSON patch to the same hardcoded lane:

```bat
land-lambda-script-edd.bat "C:\Users\guyas\Downloads\patch.json"
```

Landing a JSON patch does not ship. Shipping remains explicit:

```bat
onepush-lambda-script-edd.bat --ship
```

The mutable lane may later be aligned by a successful ship. The durable unit is the captured submission/replay result, so submitted work remains recoverable even when a lane head is later aligned to integration.
