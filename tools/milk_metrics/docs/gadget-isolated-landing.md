# Image metrics gadget isolated landing

This file is intended to exist first on the `metrics/image-metrics` gadget integration branch.

It tests the gadget-specific landing path:

```bat
forks.bat gadget-land-json-file metrics image-metrics eddy image_metrics_gadget_isolated_patch.json
```

A successful run should advance:

```text
gadgets/metrics/image-metrics/main
```

and then sync:

```text
gadget-agents/metrics/image-metrics/ed
gadget-agents/metrics/image-metrics/edd
gadget-agents/metrics/image-metrics/eddy
gadget-agents/metrics/image-metrics/guy
```

It should not advance repository `main`.
