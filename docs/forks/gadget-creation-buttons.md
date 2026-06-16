# Gadget creation batch wrappers

The root batch wrappers provide a short path for submitting a local folder as a new or existing independent gadget.

```bat
gadget-creation-<agent>.bat <gizmo> <gadget> <path-to-folder>
```

The supported wrappers are:

```text
gadget-creation-ed.bat
gadget-creation-edd.bat
gadget-creation-eddy.bat
gadget-creation-guy.bat
```

The wrapper initializes the gadget branches if required, copies the supplied folder into the selected gadget-agent lane, commits and pushes that lane, and runs audited gadget amalgamation by default.

Example:

```bat
gadget-creation-guy.bat moving-pictures centrifuge "C:\Users\guyas\Desktop\codebase\7\ollama.wires\projects\centrifuge"
```

If the source folder is inside the repository root, the destination defaults to the same repository-relative path. If the source folder is outside the repository root, the destination defaults to:

```text
projects/<gadget>
```

You can override the destination:

```bat
gadget-creation-guy.bat moving-pictures centrifuge "C:\path\to\centrifuge" --dest projects\centrifuge
```

The default amalgamation verifier checks that the destination exists in the replayed gadget worktree. For a stronger project-specific verifier, pass `--verify-command`:

```bat
gadget-creation-guy.bat moving-pictures centrifuge "C:\path\to\centrifuge" --verify-command "cd projects\centrifuge && cabal build"
```

Use `--replace` when the destination should be removed before copying the source folder.

Use `--no-amalgamate` when the lane should only be populated and pushed; amalgamation can then be run manually:

```bat
forks.bat amalgamate-all --gadget <gizmo> <gadget> --agents <agent> --apply --verify-command "<command>"
```
