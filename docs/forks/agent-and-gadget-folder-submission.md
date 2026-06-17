# Agent and gadget lane folder submission

This note records the intended operator-facing routes for large diffs.

## Gadget folder submission

Use gadget creation wrappers when a folder belongs to a gadget integration branch:

```bat
gadget-creation-edd.bat <gizmo> <gadget> "C:\path\to\folder" --dest "repo/path" --replace --allow-existing-lane-work --message "..."
```

This is transport-only by default. It pushes to:

```text
gadget-agents/<gizmo>/<gadget>/<agent>
```

It does not amalgamate unless `--amalgamate` is passed.

Amalgamate explicitly at signover:

```bat
gadget-amalgamate-edd.bat <gizmo> <gadget>
```

The wrapper expands to `gadget_amalgamate_safe.py --gadget <gizmo> <gadget> --agents edd --apply`.
It requires the gizmo and gadget on the command line so the wrong gadget cannot be amalgamated by an accidental default.

## Repository agent folder submission

Use agent submission wrappers when the target is the repository agent lane:

```bat
agent-submit-edd.bat "C:\path\to\folder" --dest "repo/path" --replace --allow-existing-lane-work --message "..."
```

This pushes to:

```text
agents/edd
```

It does not amalgamate. It is suitable for large, generated, or broad refactor diffs when the work should remain on the repository agent lane until signover.

Amalgamate the repository agent lane explicitly:

```bat
agent-amalgamate-edd.bat
```

The repository-agent amalgamation wrapper is transport-only by default. It passes a no-op verifier to `amalgamate_all.py` so arbitrary code transport is uniform and does not accidentally run `verify.bat`, Cabal, npm, Python tests, or another language-specific verifier.

Use an explicit verifier only when signover is meant to be build-gated:

```bat
agent-amalgamate-edd.bat --verify-command "verify.bat"
agent-amalgamate-edd.bat --verify-command "cmd /c cd /d projects\lambda-script && cabal build"
```

## Rule

Submission and transport are language-neutral. Build tools are optional signover gates, not default transport requirements.
