# Targeted onepush and land buttons

`create-targeted-onepush.bat` creates a matched button pair from one target definition.

```bat
create-targeted-onepush.bat <agent> <gizmo> <gadget> <source-dir> <dest-path>
```

The button name is derived. For `edd lambda-script lambda-script`, the generated target name is:

```text
lambda-script-edd
```

so the generator writes:

```text
onepush-lambda-script-edd.bat
land-lambda-script-edd.bat
```

For a distinct gizmo/gadget pair, the generated name includes both. For example `guy metrics text-metrics` produces:

```text
onepush-metrics-text-metrics-guy.bat
land-metrics-text-metrics-guy.bat
```

## Create a target button pair

```bat
create-targeted-onepush.bat edd lambda-script lambda-script ^
  "C:\Users\guyas\Desktop\codebase\7\ollama.wires\projects\lambda-script" ^
  "projects\lambda-script"
```

This hardcodes the agent, gizmo, gadget, normal source directory, and destination path into the generated buttons.

## Use the folder button

Submit the hardcoded source folder to the hardcoded gadget-agent lane:

```bat
onepush-lambda-script-edd.bat
```

Submit and ship:

```bat
onepush-lambda-script-edd.bat --ship
```

First materialisation from a directory:

```bat
onepush-lambda-script-edd.bat --init-from-dir "C:\path\to\folder"
```

First materialisation and ship:

```bat
onepush-lambda-script-edd.bat --ship --init-from-dir "C:\path\to\folder"
```

The generated onepush button accepts only:

```text
--ship
--init-from-dir <directory>
```

## Use the JSON landing button

Land a JSON patch to the same hardcoded gadget-agent lane:

```bat
land-lambda-script-edd.bat "C:\Users\guyas\Downloads\patch.json"
```

The landing button does not ship. Shipping remains:

```bat
onepush-lambda-script-edd.bat --ship
```

This keeps folder checkpointing, JSON patch landing, and amalgamation distinct while sharing one target definition.

The mutable lane may later be rewound by a successful ship. The durable unit is the captured submission/replay result, so prior onepush or land submissions must remain recoverable even when a later ship aligns lanes.
