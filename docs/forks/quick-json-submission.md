# Quick JSON submission test

This file was added through the `forks.bat land-json` REPL path.

The purpose of this patch is to confirm that a pasted JSON patch can be imported, checked, dry-run submitted, submitted to `main`, and followed by agent-lane sync without requiring the older manual import, replay, verify, and submit sequence.

For ordinary documentation and forks-tooling patches, the JSON landing path should use quick verification. Full LambdaScript compiler verification should be reserved for compiler, parser, checker, emitter, runtime, and language-fixture changes.
