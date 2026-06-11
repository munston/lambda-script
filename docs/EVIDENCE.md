# Evidence transcript

Executed in the generated package directory.

```text
$ python -S scripts/test/verify-interface.py
OK two-bat interface verified
root bat files: pull.bat, push.bat
targets: lambda-script
safe git subset: status, fetch, pull --ff-only, add -A, diff --cached --quiet, commit -m, push HEAD:branch
```
