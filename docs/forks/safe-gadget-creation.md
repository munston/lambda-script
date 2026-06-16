# Safe gadget creation and amalgamation

`gadget-creation-<agent>.bat` now ingests a folder into the selected gadget-agent lane by default. It does not amalgamate unless `--amalgamate` is passed explicitly.

This protects lane work during bootstrap. A failed verifier should not erase the visible gadget-agent lane.

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

When ready, run safe amalgamation explicitly:

```bat
python scripts\forks\gadget_amalgamate_safe.py --gadget <gizmo> <gadget> --agents guy --apply --verify-command "cmd /c cd /d projects\<gadget> && cabal build"
```

The safe amalgamation order is:

1. Capture the gadget-agent lane diff.
2. Apply it to the gadget integration branch.
3. Run the declared verifier.
4. Push the integration branch.
5. Sync the source lane to the new integration branch.

The previous unsafe order reset the source lane before verification. That meant a failed verifier could remove the visible lane while leaving only `.forks/gadget-submissions/*.json` and `.patch` behind.
