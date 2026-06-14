# Merlin

Merlin is a geared mock detector for agent-written patches. It scans source trees for evidence that a compile fix, implementation, or patch has replaced real behaviour with a placeholder, bypass, dummy result, or weakened semantic path.

Merlin is currently isolated as the `merlin/mock-detector` gadget. It should remain outside `lambdascript/core` until the gizmo and gadget branch model is ready to import it as a protected toolchain or promote it into the main LambdaScript gizmo.

## Commands

From the repository root:

```bat
python -m py_compile tools\merlin\merlin\__init__.py tools\merlin\merlin\detector.py tools\merlin\merlin\cli.py tools\merlin\test\smoke.py
python tools\merlin\test\smoke.py
```

From `tools/merlin`:

```bat
python -m merlin.cli scan ../../scripts/forks --out report.json
python -m merlin.cli scan ../../scripts/forks --out report.json --fail-on-issues
```

The scan report is JSON with format `LS_MERLIN_SCAN_V1`.
