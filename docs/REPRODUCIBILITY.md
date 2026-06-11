# Reproducibility

## Static verification

From the repository root:

```bat
python scripts\test\verify-interface.py
```

Expected output:

```text
OK two-bat interface verified
root bat files: pull.bat, push.bat
targets: lambda-script
safe git subset: status, fetch, pull --ff-only, add -A, diff --cached --quiet, commit -m, push HEAD:branch
```

This verifies:

1. The only top-level `.bat` files are `pull.bat` and `push.bat`.
2. `pull.bat` delegates to `scripts\git\pull-all.bat`.
3. `push.bat` delegates to `scripts\git\push-all.bat`.
4. `git.config` parses as a maintained-target list.
5. Configured target test scripts exist.
6. Internal `.bat` scripts avoid destructive Git commands.
7. Push order is status, fetch, test, add, commit, push.

## Windows execution proof

From a clean local clone:

```bat
pull.bat
python scripts\test\verify-interface.py
push.bat "Verify two-bat git interface"
```

If there are no local changes, `push.bat` may report no staged changes and still attempt to publish existing local commits. That is expected.

## Why this is the maintained interface

The GitHub connector can inspect repository state, but direct API file writes are not a dependable development loop. The maintained loop is plain Git through `pull.bat` and `push.bat`.
