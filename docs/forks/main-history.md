# Main history receipts

Main history receipts make each accepted push to `main` visible as a replay marker.

The Git history remains canonical. The receipt layer adds a machine-readable index under:

```text
docs/forks/main-history/index.json
docs/forks/main-history/patches/main-000001.json
docs/forks/main-history/patches/main-000002.json
```

Each receipt records the accepted source head, base commit, changed files, agent or system actor, and the kind of main update.

Supported update kinds:

```text
json_patch
gadget_promotion
```

For direct JSON patch submissions to `main`, `land_json_patch.py` appends a receipt commit after verification and before push. For gadget promotion, `gadget_promote.py` appends a receipt commit on top of the promoted gadget head before dry-run and push.

This provides a replayable sequence of accepted main updates. A future zero-initialized gizmo can use the Git commit sequence plus these receipts to discover which programs and patches were accepted, in order, without relying on operator chat history.
