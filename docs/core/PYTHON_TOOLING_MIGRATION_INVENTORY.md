# Python tooling migration inventory

Status: initial migration inventory for the native backend transition.

This document is the first actionable follow-up to `docs/core/NATIVE_BACKEND_MIGRATION.md`. It classifies the Python tooling that currently supports forks, gadget lanes, replay ledgers, verification, and related workflow operations so that the project can replace Python in dependency order rather than attempting a single high-risk rewrite.

The inventory is intentionally operational. It records what each Python component appears to do, how risky it is to port, how it should be verified, and what C++ replacement shape is expected. It does not change the LambdaScript language surface and it does not deprecate any command by itself.

## 1. Migration classes

### Class A — leaf utilities

Small tools with clear inputs and outputs, minimal side effects, and simple equivalence checks. These are the preferred first C++ migration targets.

Examples:

```text
hashing helpers
path normalization helpers
JSON shape readers
manifest readers
small status formatters
fixture decoders
```

### Class B — readers and validators

Tools that inspect repository state, payloads, manifests, replay ledgers, or toolchain availability without mutating remote branches. These should follow Class A because they establish native confidence before mutators are ported.

Examples:

```text
submission object readers
replay ledger readers
payload materialisation auditors
verify-profile selectors
toolchain availability checks
```

### Class C — mutators

Tools that write files, create submission objects, append replay ledgers, materialise candidates, or modify local worktrees. These require strict dry-run/apply separation and fixture-repository equivalence tests.

Examples:

```text
JSON patch importers
candidate materialisers
ledger appenders
main-history writers
accelerator state writers
```

### Class D — orchestration commands

Dispatchers and multi-step operators that fetch, plan, verify, submit, sync, or promote branches. These should be ported after native leaf utilities, readers, validators, and mutators exist.

Examples:

```text
forks command dispatcher
agent land command wrappers
gadget land command wrappers
gadget promotion
amalgamation
replay sync
```

### Class E — bootstrap and developer convenience scripts

Scripts used to install, scaffold, or smooth local development. These are lower priority unless they are required for normal operation.

Examples:

```text
node toolchain setup
local fixture decoding
developer-only helpers
one-off repair scripts
```

## 2. Inventory table

This table is an initial classification from the current known forks/gadget workflow. It should be extended by a native inventory walker once that exists.

| Path | Class | Current role | Inputs | Outputs | Side effects | C++ replacement shape | Verification method | Priority |
|---|---:|---|---|---|---|---|---|---:|
| `scripts/forks/submission_object.py` | B/C | Reads and writes replayable submission objects and payload metadata. | JSON patch files, file trees, content hashes. | Submission object JSON, payload references, fingerprints. | May write submission/payload artefacts when used by land/import paths. | `ls-submission-object` native library plus CLI. | Golden JSON fixtures; hash equality; malformed-payload diagnostics. | 1 |
| `scripts/forks/import_json_patch.py` | C | Imports an `LS_FORK_JSON_PATCH_V1` payload into a candidate worktree. | Patch JSON, target worktree, repository paths. | Materialised candidate tree. | Writes candidate files. | `ls-import-json-patch` CLI/library. | Apply patches in disposable fixture repos; compare tree hashes and diagnostics. | 2 |
| `scripts/forks/land_json_patch.py` | D | Lands repository-target JSON patches and connects import, verify, and submit flow. | Agent name, patch path, target branch/profile. | Advanced target branch and replay history. | Fetches/submits/updates branch state. | Native orchestration after import/submission primitives exist. | End-to-end dry-run/apply fixture repo; force-with-lease failure tests. | 6 |
| `scripts/forks/agent_land_json.py` | D | Agent-specific repository landing wrapper. | Agent name or hardcoded lane, patch path. | Delegates to landing flow. | Can advance target branch through delegated lander. | Thin native command wrapper around common lander. | Command-line compatibility tests. | 7 |
| `scripts/forks/gadget_land_json.py` | D | Lands gadget-target JSON patches, records gadget replay ledger, and leaves lane propagation to amalgamation. | Gizmo, gadget, agent, patch path, profile flags. | Advanced `gadgets/<gizmo>/<gadget>/main`, replay ledger entry. | Fetches, writes, verifies, pushes gadget integration branch. | Native gadget lander built after submission/import and replay-ledger primitives. | Fixture repo with multiple agents; non-aligning default; `--align-lanes` repair test. | 7 |
| `scripts/forks/gadget_branches.py` | B/D | Inspects and syncs gadget integration and gadget-agent lanes. | Gizmo, gadget, agent selection, branch refs. | Status reports, optional lane sync. | Read-only in status mode; mutating in sync modes. | Split into `ls-gadget-status` reader and `ls-gadget-sync` mutator. | Status golden output; sync in disposable remote fixture. | 4 |
| `scripts/forks/amalgamate_all.py` | D | Captures/replays/verifies/submits lane work; handles repository and gadget amalgamation. | Agent lanes, gadget refs, replay ledgers, payloads, flags. | Advanced integration/main target; aligned lanes. | High: fetches, rewinds lanes, replays, verifies, pushes. | Late native orchestrator using earlier native readers/mutators. | Multi-agent fixture repo; stale head refusal; missing payload refusal; strict/warn agent-doc modes. | 9 |
| `scripts/forks/gadget_promote.py` | D | Promotes a gadget integration branch into `main` with verification/history. | Gizmo, gadget, profile, source/destination refs. | Advanced `main`, synced repository agents, main-history entry. | High: verifies and pushes `main`. | Native promote orchestrator after main-history and branch primitives. | Promotion fixture repo; behind/ahead refusal; history receipt checks. | 10 |
| `scripts/forks/gadget_verify_profiles.py` | B | Defines or selects verification commands for gadget profiles. | Profile name, gadget identity. | Verification command set/status. | Usually read/dispatch only. | Native profile resolver. | Profile mapping golden tests; unknown profile diagnostics. | 2 |
| `scripts/forks/ensure_node_toolchains.py` | E/B | Ensures Node/TypeScript support for current JS/TS-based compiler checks. | Local environment, package/toolchain paths. | Toolchain availability result, install/build side effects if enabled. | Local environment mutation possible. | Defer; eventually replaced by native build/toolchain probes. | Dry-run environment probe tests. | 8 |
| `scripts/forks/main_history.py` | B/C | Reads and writes main-history replay/archive entries. | Main history index, receipt paths, commits. | `docs/forks/main-history` entries and receipts. | Writes history artefacts when promoted. | `ls-main-history` native library/CLI. | Golden index update; receipt schema validation; append-order tests. | 3 |
| `scripts/forks/forks.py` | D | Historical/top-level forks dispatcher for repository workflows. | CLI command and arguments. | Delegated command behavior. | Depends on subcommands. | Last-stage native dispatcher. | CLI compatibility matrix after subcommands are native. | 11 |
| `scripts/forks/forks_dispatch.py` | D | Current command dispatch layer for forks command routing. | CLI command and arguments. | Delegated command behavior. | Depends on subcommands. | Last-stage native dispatcher or C++ command table. | CLI compatibility matrix after subcommands are native. | 11 |
| `scripts/forks/replay_sync.py` | D | Replays pending work onto current branch state when present in the active tooling set. | Replay entries, payloads, branch refs. | Rebuilt lane/branch candidate. | Can rewrite lane state. | Native replay sync after replay readers and patch importers. | Fixture repo replay tests; conflict/refusal cases. | 8 |
| `scripts/forks/ensure_*` helpers | E/B | Local setup and environment checks. | Local toolchain paths. | Toolchain status or setup effects. | Local environment mutation possible. | Native probes, with install side effects kept explicit. | Dry-run probes; missing-tool diagnostics. | 8 |
| `tools/*/scripts/*.py` and accelerator Python helpers | A/B/C/D | Accelerator and tool-specific Python helpers outside forks. | Tool-specific state and artefacts. | Tool-specific reports or mutations. | Unknown until inventoried. | Separate native inventory pass per tool. | Tool-specific golden fixtures. | 5 |

## 3. First recommended migration target

The first C++ replacement should be a Class B reader/validator rather than a mutator or dispatcher.

Recommended target:

```text
scripts/forks/submission_object.py
```

Rationale:

```text
- It is central to the new durable-work model.
- It is below the high-risk branch mutation layer.
- It supports both repository and gadget workflows.
- It can be tested with pure JSON/hash fixtures.
- It creates useful native primitives for later lander/amalgamation ports.
```

Initial native replacement shape:

```text
native/forks/submission_object.cpp
native/forks/submission_object.hpp
native/forks/submission_object_main.cpp
```

Expected command sketch:

```text
ls-submission-object inspect <payload.json>
ls-submission-object fingerprint <payload.json>
ls-submission-object validate <payload.json>
```

The first native implementation should be read-only. It should not write payloads or mutate branches. Writing/submission generation can follow after read-only equivalence is proven.

## 4. Verification requirements for the first target

The first target should have small, deterministic fixtures:

```text
valid minimal LS_FORK_JSON_PATCH_V1 payload
valid multi-file payload
payload with missing format
payload with wrong agent field type
payload with unsupported operation
payload whose fingerprint is known
```

Verification should compare:

```text
exit code
stdout shape
stderr diagnostics
computed fingerprint/hash
accepted/rejected status
```

The first native tool should be accepted only when its output matches the Python behavior or when an intentional correction is documented.

## 5. Migration order

The recommended initial order is:

```text
1. submission object reader/validator
2. JSON patch importer in dry-run mode
3. replay-ledger reader/materialisation auditor
4. gadget branch status reader
5. main-history reader/writer
6. candidate materialiser
7. repository/gadget landers
8. replay sync
9. amalgamate-all
10. gadget promotion
11. top-level forks dispatcher
12. accelerator-specific Python helpers by the same reader-before-mutator rule
```

This order keeps branch mutation and destructive lane operations late.

## 6. Native C++ conventions

Native tools should follow a common convention:

```text
--json       emit machine-readable output
--dry-run    compute the plan without mutating
--apply      permit mutation when supported
--repo PATH  explicit repository root when needed
--strict     make warnings fatal where applicable
```

Exit code convention:

```text
0  success
1  ordinary validation failure or rejected operation
2  command-line misuse
3  environmental/toolchain failure
4  internal invariant failure
```

Diagnostic convention:

```text
stdout: intended machine output or concise human result
stderr: diagnostics, refusals, and invariant failures
```

Mutators must recheck assumptions immediately before applying changes.

## 7. LambdaScript interface implications

The compiler should expose native tooling through a narrow wrapper/control layer. Generated TypeScript should call native tools or runtime bindings; it should not reimplement forks logic.

Short-term LambdaScript needs:

```text
typed foreign/native declarations
stable primitive argument passing
stable string/void handling
predictable generated TypeScript wrappers
explicit unsupported backend errors
```

Later LambdaScript may need:

```text
tool invocation declarations
structured result envelopes
opaque resource handles
native error/result typing
```

Those later features should be admitted only after the first native C++ tools exist and the required shape is known.

## 8. Completion criteria for this inventory stage

This inventory stage is complete when:

```text
- the known forks Python tooling has a migration class
- the high-risk mutators are separated from low-risk readers
- the first C++ migration target is identified
- verification requirements for that target are stated
- agents can proceed without debating whether to rewrite the top-level dispatcher first
```

## 9. Next patch after this inventory

The next patch should create the first native C++ skeleton for the selected target:

```text
native/forks/submission_object.hpp
native/forks/submission_object.cpp
native/forks/submission_object_main.cpp
```

The first skeleton should compile as a standalone executable or library entry point and implement only:

```text
inspect
validate
fingerprint
```

against static JSON fixtures if a JSON parser dependency is already available. If no JSON dependency is available, the next patch should first add the minimal native dependency or a constrained parser strategy for the known payload format.
