# Patch intake

This directory is the intake bridge for changes supplied by another model or another tool.

The accepted patch format is deliberately narrow.

```text
LS_PATCH_V1
COMMIT_MESSAGE: Add parser skeleton
--- DIFF ---
diff --git a/path b/path
...
--- END DIFF ---
```

Only git-style unified diffs are accepted in v1. Full-file replacement blocks are intentionally not accepted yet.

Use from MSYS2 UCRT64:

```sh
cat > /tmp/grok.patch <<'EOF'
LS_PATCH_V1
COMMIT_MESSAGE: Add sample file
--- DIFF ---
diff --git a/sample.txt b/sample.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/sample.txt
@@ -0,0 +1 @@
+sample
--- END DIFF ---
EOF

bash scripts/patch/apply-and-ship.sh /tmp/grok.patch
```

The ship script does:

```text
pull.bat
extract COMMIT_MESSAGE
git apply --check
git apply
python scripts/test/verify-interface.py
push.bat "COMMIT_MESSAGE"
```
