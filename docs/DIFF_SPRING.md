# Diff spring

The diff spring parallels the tarball spring. It accepts a single `.json` patch file in:

```text
spring/diff/drop/
```

After successful absorption, the `.json` file is moved to:

```text
spring/diff/archive/
```

## Format

```json
{
  "format": "LS_JSON_PATCH_V1",
  "commit_message": "Short commit message",
  "files": [
    {
      "path": "path/to/file",
      "action": "create",
      "content": "full file content\n"
    },
    {
      "path": "path/to/file",
      "action": "replace",
      "content": "full replacement file content\n"
    },
    {
      "path": "path/to/file",
      "action": "modify",
      "edits": [
        {
          "type": "replace_exact",
          "old": "exact old text\n",
          "new": "exact new text\n"
        }
      ]
    },
    {
      "path": "path/to/file",
      "action": "delete"
    }
  ]
}
```

## Semantics

```text
create: fails if the file already exists
replace: fails if the file does not exist
modify: exact text replacement only
delete: fails if the file does not exist
```

`replace_exact` succeeds only when the `old` text occurs exactly once.

## Safety rules

The absorber rejects:

```text
absolute paths
paths containing ..
.git paths
spring/diff self-writes
spring/tarball self-writes
private-key-like filenames
multiple json patches in the drop location
tracked dirty changes before absorption
```

## Command

```sh
bash scripts/diff_spring/absorb-and-ship.sh
```
