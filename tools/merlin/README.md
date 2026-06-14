# Merlin

Merlin is a geared mock detector for agent-written patches. It scans source trees for evidence that a compile fix, implementation, or patch has replaced real behaviour with a placeholder, bypass, dummy result, or weakened semantic path.

Merlin is currently local tool code. It has no provisioning boundary, no external command capability model, and no import relationship to other toolchains. Integration into any surrounding orchestration system should be handled later as a separate task after extensive detector testing.

## Commands

From the repository root:

```bat
python -m py_compile tools\merlin\merlin\__init__.py tools\merlin\merlin\detector.py tools\merlin\merlin\cli.py tools\merlin\test\smoke.py
python tools\merlin\test\smoke.py
```

From `tools/merlin`:

```bat
python -m merlin.cli scan ../../scripts/forks --out report.json
python -m merlin.cli scan ../../scripts/forks --out report.json --fail-on-error
python -m merlin.cli scan ../../scripts/forks --out report.json --fail-on-issues
```

The scan report is JSON with format `LS_MERLIN_SCAN_V1`. It contains a gear summary, a pass flag, issue counts by severity, and source locations for findings.

## Current gears

`implementation-presence` checks for explicit incomplete implementation markers such as placeholder exceptions, bare `pass`, `TODO`, and `FIXME`.

`return-substance` checks for unqualified empty return paths such as `return None`, `return {}`, `return []`, and empty string returns.

`semantic-substance` records lower-confidence placeholder language such as mock, stub, dummy, fake, or placeholder. These are warnings by default because the words can appear in legitimate detector code.
