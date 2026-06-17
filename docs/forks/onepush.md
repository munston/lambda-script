# Targeted onepush

`create-targeted-onepush.bat` creates a target-specific button pair from one target definition.

```bat
create-targeted-onepush.bat <agent> <gizmo> <gadget> <source-dir> <dest-path>
```

For `edd lambda-script lambda-script`, the derived target name is `lambda-script-edd`, and the generated buttons are:

```bat
onepush-lambda-script-edd.bat
land-lambda-script-edd.bat
```

The onepush button has two runtime controls:

```bat
--ship
--init-from-dir <directory>
```

No target, destination, verifier, replace flag, or message flag is supplied during ordinary use.

`onepush-<target>.bat` submits the hardcoded source folder to the hardcoded lane and prints one success line.

`onepush-<target>.bat --ship` ships the existing lane. It does not re-submit the hardcoded source folder first. This prevents a stale local source directory from overwriting work already landed to the lane by a targeted JSON patch.

`onepush-<target>.bat --init-from-dir <directory>` performs first materialisation from the supplied directory.

`onepush-<target>.bat --ship --init-from-dir <directory>` performs first materialisation and then ships.

`land-<target>.bat <patch.json>` lands a JSON patch to the same hardcoded lane and prints one success line.

Failure output is button-level and pruned. It names the failed stage and gives a short root-cause summary. The durable unit is the captured submission/replay result; a lane may later be aligned by a successful ship without destroying already captured work.
