# Diff spring

The diff spring is a chronological intake device for text-only JSON patches.

Location:

```text
spring/diff/drop/
```

Rules:

```text
0 json patches: nothing to absorb
1 json patch: absorb it
more than 1 json patch: refuse
```

Accepted patch format:

```json
{
  "format": "LS_JSON_PATCH_V1",
  "commit_message": "Add useful change",
  "files": [
    {
      "path": "example.txt",
      "action": "create",
      "content": "hello\n"
    }
  ]
}
```

Run from MSYS2 UCRT64:

```sh
bash scripts/diff_spring/absorb-and-ship.sh
```

The script performs:

```text
pull.bat
inspect exactly one json patch
reject unsafe paths
apply create/replace/modify/delete operations
archive the json patch chronologically
verify interface
push.bat with the patch commit message
```
