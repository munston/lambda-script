# Gadget JSON landing

A gadget JSON landing command is a shortcut over the target-ref JSON landing path.

Instead of spelling the target ref manually:

```bat
forks.bat land-json-file --target-ref origin/gadgets/metrics/image-metrics/main eddy patch.json
forks.bat gadget-sync-all metrics image-metrics
```

use:

```bat
forks.bat gadget-land-json-file metrics image-metrics eddy patch.json
```

The command performs:

```text
resolve gadget target ref
import JSON patch onto that target
verify candidate
dry-run push
push to gadget integration branch
sync gadget agent lanes
print gadget status
```

The paste-oriented form is:

```bat
forks.bat gadget-land-json metrics image-metrics eddy
```

Paste the JSON patch, then finish input with `Ctrl+Z` followed by Enter.

By default the command uses the same quick verification as `land-json`. For language/compiler/runtime changes that need the full repository verifier, pass `--full`:

```bat
forks.bat gadget-land-json-file --full lambdascript core eddy patch.json
```

A gadget landing does not push to repository `main`. It pushes to:

```text
gadgets/<gizmo>/<gadget>/main
```

and then syncs:

```text
gadget-agents/<gizmo>/<gadget>/<agent>
```
