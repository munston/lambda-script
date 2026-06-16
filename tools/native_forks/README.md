# native_forks

Native C++ migration area for forks tooling.

This directory starts the Python-removal path described in `docs/core/NATIVE_BACKEND_MIGRATION.md` and `docs/core/PYTHON_TOOLING_MIGRATION_INVENTORY.md`.

## submission_object_inspect

`submission_object_inspect.cpp` is the first native reader/validator scaffold for `.forks/submissions/<agent>.json` objects.

It is deliberately read-only. It does not create submissions, alter branches, append ledgers, apply patches, or submit refs. Its current job is to validate the low-level submission object shape and recompute the stored patch SHA-256:

```bat
call tools\native_forks\build_submission_object_inspect.bat
tools\native_forks\bin\submission_object_inspect.exe --agent eddy
```

Supported inputs:

```bat
submission_object_inspect.exe --agent eddy
submission_object_inspect.exe --file .forks\submissions\eddy.json
```

Current checks:

```text
format == LS_FORK_SUBMISSION_V1
required string fields are present
patch_sha256 matches SHA-256(patch)
changed_files can be counted when present
```

This tool is not yet a replacement for `scripts/forks/submission_object.py`. It is the first native validation component that can later be used by replay, capture, and amalgamation tooling after equivalence tests are added.
