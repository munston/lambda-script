# Amalgamation button

There is one generic amalgamation button.

```bat
amalgamate.bat
```

With no arguments, it amalgamates every configured gadget target discovered from:

```text
examples/gizmos/*.gizmo.json
```

For the current repository this includes:

```text
lambdascript/core
```

A single target can still be supplied explicitly:

```bat
amalgamate.bat lambdascript core
```

The selected agents default to:

```text
ed edd eddy guy
```

A custom agent set can be supplied:

```bat
amalgamate.bat --agents ed edd eddy guy
amalgamate.bat lambdascript core --agents ed edd
```

The wrapper delegates to:

```text
python scripts/forks/amalgamate_targets.py
```

which fetches, runs `amalgamate_all.py --gadget <gizmo> <gadget> --agents ... --apply` for each selected target, and prints gadget status after each target.

The default is all configured gadget targets, not a project-specific subbranch.
