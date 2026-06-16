# Amalgamation button

There is one generic amalgamation button.

```bat
amalgamate.bat
```

With no arguments, it amalgamates every initialized configured gadget target discovered from:

```text
examples/gizmos/*.gizmo.json
```

A target is initialized when its gadget integration branch exists:

```text
origin/gadgets/<gizmo>/<gadget>/main
```

Configured but uninitialized targets are skipped by default with a visible message. This prevents a partially declared gizmo/gadget from breaking the normal operator amalgamation cycle.

A single target can still be supplied explicitly:

```bat
amalgamate.bat lambdascript core
```

For explicit single-target mode, a missing integration branch is fatal by default, because the operator has named the target directly.

The selected agents default to:

```text
ed edd eddy guy
```

A custom agent set can be supplied:

```bat
amalgamate.bat --agents ed edd eddy guy
amalgamate.bat lambdascript core --agents ed edd
```

To deliberately fail on uninitialized discovered targets, use:

```bat
amalgamate.bat --include-uninitialized
```

The default is all initialized configured gadget targets, not all declared but unprovisioned targets.
