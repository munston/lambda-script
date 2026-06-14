# Image metrics gadget branch-only landing test

This note is deliberately distinct from the earlier main-branch test files.

It is intended to test the gadget-specific landing command after the `metrics/image-metrics` gadget branch has been synchronized to current repository `main`.

Expected landing target:

```text
gadgets/metrics/image-metrics/main
```

Expected synchronized lanes:

```text
gadget-agents/metrics/image-metrics/ed
gadget-agents/metrics/image-metrics/edd
gadget-agents/metrics/image-metrics/eddy
gadget-agents/metrics/image-metrics/guy
```

Repository `main` should not advance during this test.
