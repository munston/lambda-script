# land-json workflow

`forks.bat land-json <agent>` is the paste-oriented submission path for agent patches. It reads a JSON patch from standard input, imports it into a candidate worktree, verifies the candidate, performs a dry-run push, advances `main` if the dry-run succeeds, then syncs the agent lanes.

On Windows, start the REPL-style command with:

```bat
forks.bat land-json eddy
```

Paste the JSON patch, then finish input with `Ctrl+Z` followed by Enter.

For non-interactive agent use, write the patch to a file and run:

```bat
forks.bat land-json-file eddy patch.json
```

The JSON patch format is:

```json
{
  "format": "LS_FORK_JSON_PATCH_V1",
  "agent": "eddy",
  "title": "Short description",
  "files": [
    {
      "op": "upsert",
      "path": "relative/path.txt",
      "encoding": "utf-8",
      "content": "file contents\n"
    }
  ]
}
```

This route is intentionally receipt-gated. A patch reaches `main` only after import, candidate freshness checks, verification, and dry-run submit all succeed.
