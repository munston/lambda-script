# Patch intake format v1

The purpose of this format is to allow a model to return a patch that can be pasted into a file and applied by a script.

## Format

```text
LS_PATCH_V1
COMMIT_MESSAGE: Add useful change
--- DIFF ---
diff --git a/path b/path
...
--- END DIFF ---
```

## Rules

The first line must be:

```text
LS_PATCH_V1
```

There must be exactly one commit message line:

```text
COMMIT_MESSAGE: ...
```

The diff must be between:

```text
--- DIFF ---
--- END DIFF ---
```

The diff must be a git-style unified diff containing `diff --git`.

## Apply and ship

```sh
cat > /tmp/grok.patch <<'EOF'
LS_PATCH_V1
COMMIT_MESSAGE: Add useful change
--- DIFF ---
diff --git a/path b/path
...
--- END DIFF ---
EOF

bash scripts/patch/apply-and-ship.sh /tmp/grok.patch
```

## Validation

```sh
python scripts/patch/apply_patch.py --self-test
python scripts/patch/apply_patch.py --check /tmp/grok.patch
```
