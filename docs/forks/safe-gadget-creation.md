# Safe gadget creation and amalgamation

`gadget-creation-<agent>.bat` ingests a folder into the selected gadget-agent lane by default. It does not amalgamate unless `--amalgamate` is passed explicitly.

Amalgamation is transport-oriented by default. It checks that the captured lane diff applies to the gadget integration branch, commits the candidate, checks the integration ref has not moved, pushes the integration branch, and then syncs the source lane. It does not run Haskell, Node, Python, Cabal, npm, or any project-specific build command unless `--verify-command` is supplied explicitly.

Default flow:

```bat
gadget-creation-guy.bat <gizmo> <gadget> <path-to-folder> --dest projects\<gadget>
```

This initializes the gadget branches if needed, copies the folder into the `guy` lane, commits the lane, and pushes it. It then stops.

Inspect the lane:

```bat
git fetch origin --prune
git ls-tree -r --name-only origin/gadget-agents/<gizmo>/<gadget>/guy
```

When ready, run transport-only safe amalgamation:

```bat
python scripts\forks\gadget_amalgamate_safe.py --gadget <gizmo> <gadget> --agents guy --apply
```

Optional project verification is a separate explicit choice:

```bat
python scripts\forks\gadget_amalgamate_safe.py --gadget <gizmo> <gadget> --agents guy --apply --verify-command "cmd /c cd /d projects\<gadget> && cabal build"
```

The safe amalgamation order is:

1. Capture the gadget-agent lane diff.
2. Apply it to the gadget integration branch.
3. Run an explicit verifier only if one was supplied.
4. Push the integration branch.
5. Sync the source lane to the new integration branch.

The previous unsafe order reset the source lane before verification. That meant a failed verifier could remove the visible lane while leaving only `.forks/gadget-submissions/*.json` and `.patch` behind. The current route preserves lane work until transport has succeeded.
