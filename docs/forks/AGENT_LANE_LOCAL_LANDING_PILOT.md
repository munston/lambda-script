# forks agent landing pilot

This note records the staged transition for agent JSON landing.

`agent_land_json.py` now supports:

```bat
python scripts\forks\agent_land_json.py --lane-local-only ed patch.json
```

Lane-local mode lands only to the hardcoded agent's gadget-agent lane:

```text
gadget-agents/<gizmo>/<gadget>/<agent>
```

It prints:

```text
scope=agent-lane-only
sync=False promote=False amalgamate=False
```

and skips:

```text
gadget integration advancement
amalgamation
promotion
all-lane sync
```

Only `ed-land-json.bat` is switched to lane-local pilot mode in this patch. The other wrappers are deliberately left unchanged until Ed's lane-local path is tested. After the pilot passes, the same wrapper change can be applied to `edd-land-json.bat`, `eddy-land-json.bat`, and `guy-land-json.bat`.
