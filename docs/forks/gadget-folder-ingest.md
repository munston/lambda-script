# Gadget folder ingestion

`gadget-ingest-folder` copies a local folder into a gadget-agent lane and pushes that lane for the normal forks amalgamation path. It is intended for large source trees that should be represented by Git's own `diff --binary` machinery rather than by a large `LS_FORK_JSON_PATCH_V1` file.

## Basic shape

Run from the repository root:

```bat
cd /d "C:\Users\guyas\Desktop\codebase\7\ollama.wires\foreign-language\lambda-script"

git fetch origin --prune

git restore --source=origin/gadgets/lambdascript/core/main -- forks.bat scripts/forks/forks_dispatch.py scripts/forks/gadget_branches.py scripts/forks/gadget_ingest_folder.py scripts/forks/forks.py
```

Then ingest a local folder into the selected independent gizmo/gadget:

```bat
forks.bat gadget-ingest-folder <gizmo> <gadget> <agent> ^
  --init-if-missing ^
  --source C:\path\to\local-folder ^
  --dest tools\<package> ^
  --message "Materialise <package> folder"
```

Example:

```bat
forks.bat gadget-ingest-folder audio-lab wavproc edd ^
  --init-if-missing ^
  --source C:\Users\guyas\staging\wavproc ^
  --dest tools\wavproc ^
  --message "Materialise wavproc folder"
```

This command will:

1. Fetch `origin`.
2. Initialise `gadgets/<gizmo>/<gadget>/main` and the configured agent lanes when `--init-if-missing` is provided and the gadget branch set is absent.
3. Prepare `gadget-agents/<gizmo>/<gadget>/<agent>` from `origin/gadgets/<gizmo>/<gadget>/main` when the lane is safe to sync.
4. Copy the local folder into a temporary worktree at the requested destination.
5. Stage and commit the resulting tree delta on the gadget-agent lane.
6. Push the gadget-agent lane to `origin`.

It does not need to translate every file into JSON. Once the lane has a commit, the existing `amalgamate-all` gadget mode captures the lane delta with Git's binary diff support.

## Excludes

The command skips common transient folders and binary build products by default, including `.git`, `node_modules`, `dist-newstyle`, `.stack-work`, virtual environments, Python caches, and compiled object files. Add project-specific exclusions with repeated `--exclude` flags:

```bat
forks.bat gadget-ingest-folder audio-lab wavproc edd ^
  --source C:\Users\guyas\staging\wavproc ^
  --dest tools\wavproc ^
  --exclude tmp ^
  --exclude "*.log"
```

Use `--no-default-excludes` only when the folder is already curated and every file is intended for version control.

## Replace mode

By default, the source folder is merged into the destination and existing destination files that are absent from the source are left in place. Use `--replace` when the destination should exactly match the source tree, subject to exclusions:

```bat
forks.bat gadget-ingest-folder audio-lab wavproc edd ^
  --source C:\Users\guyas\staging\wavproc ^
  --dest tools\wavproc ^
  --replace ^
  --message "Replace wavproc folder"
```

## Amalgamation

After the lane has been pushed, inspect status and amalgamate through the normal gadget path:

```bat
python scripts\forks\gadget_branches.py status audio-lab wavproc

forks.bat amalgamate-all --gadget audio-lab wavproc --agents edd --apply
```

The ingest command also prints the exact amalgamation command after a successful lane push.

For a single-command local run, pass `--amalgamate` and provide an appropriate verification command for the gadget:

```bat
forks.bat gadget-ingest-folder audio-lab wavproc edd ^
  --source C:\Users\guyas\staging\wavproc ^
  --dest tools\wavproc ^
  --message "Materialise wavproc folder" ^
  --amalgamate ^
  --verify-command "cd tools\wavproc && cabal build"
```

## Safety rules

The command refuses to overwrite an agent lane that already has unique work unless `--allow-existing-lane-work` is provided. This prevents accidental loss of another staged folder submission.

The command refuses forbidden paths unless `--allow-forbidden` is provided.

Symlinks are skipped by default. Use `--follow-symlinks` only when the source folder has been audited and copying symlink targets is desired.
