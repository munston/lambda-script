# Targeted onepush

`create-targeted-onepush.bat` creates project-specific onepush buttons.

A generated `onepush-<name>.bat` hardcodes:

- agent
- gizmo
- gadget
- normal source directory
- destination path in the gadget branch

The generated button accepts only two runtime controls:

```bat
--ship
--init-from-dir <directory>
```

No target, destination, verifier, replace flag, or message flag is supplied during normal use.

## Create a button

```bat
create-targeted-onepush.bat lambda-script-edd edd lambda-script lambda-script ^
  "C:\Users\guyas\Desktop\codebase\7\ollama.wires\projects\lambda-script" ^
  "projects\lambda-script"
```

This writes:

```bat
onepush-lambda-script-edd.bat
```

## Use the button

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

The mutable lane may later be rewound by a successful ship. The durable unit is the captured submission/replay result, so prior onepush submissions must remain recoverable even when a later ship aligns lanes.
