# Milk metrics smoke test

The image-metrics gadget has a fast smoke test at:

```bat
python tools\milk_metrics\test\smoke.py
```

It creates a synthetic RGB image, runs `analyze`, runs `penalty-mask`, and checks the expected masks, overlays, component plot, and JSON reports exist. It deliberately avoids the iterative `restore` command so that gadget verification stays fast.

The metrics gizmo full profile uses this smoke test:

```bat
forks.bat gadget-land-json-file --profile full metrics image-metrics eddy patch.json
```
