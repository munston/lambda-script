# JSON submission import

The JSON submission importer lets an agent provide a patch as a pasteable JSON object instead of requiring work to live on an agent branch.

The imported JSON is converted into the normal forks submission flow:

`text
JSON patch -> submission object -> replayed candidate -> verification receipt -> submit
`

A JSON patch should use this shape:

`json
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
    },
    {
      "op": "delete",
      "path": "obsolete/file.txt"
    }
  ]
}
`

Use line-feed newlines in JSON `content` strings. Avoid Windows CRLF escape sequences in JSON patch text unless a later importer version explicitly normalises them.

Normal operator flow:

`bat
forks.bat import-json eddy eddy_patch.json
forks.bat submission-status eddy
forks.bat replay eddy --rebase-stale
forks.bat verify-submission eddy
forks.bat submit-submission eddy --dry-run
forks.bat submit-submission eddy
`

The importer rejects unsafe paths and writes the same submission object used by the branch-capture workflow, so JSON import does not bypass replay, verification, freshness checks, or receipts.
