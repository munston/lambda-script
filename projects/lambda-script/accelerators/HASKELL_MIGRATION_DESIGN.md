# Haskell migration of the forks/gizmo/gadget build system — principled design

This document is the **comprehension artifact** for the accelerator request
[`haskell-migration.json`](haskell-migration.json). It is written once, by the
expensive planning model (Claude Opus 4.8), so that the implementing agents
(ed / edd / eddy / guy, local or remote) can carry the work without re-deriving
the architecture each time. The accelerator JSON is the *executable plan*; this
file is the *why*. Read this first, then drive from the slots.

The goal is to translate the Python distributed developmental build system
(`scripts/forks/*.py`, 22 modules / ~6.5k lines) into a principled Haskell
package under `projects/lambda-script/src/lambda-script/lib/LambdaScript/Forks/`,
and then make the Haskell tool **self-hosting** — used to drive its own
remaining migration — before the Python is decommissioned.

---

## 1. Lessons from the Python implementation

The Python works, but it grew organically and the seams show. We migrate to fix
these specifically, not to transliterate them:

1. **IO and logic are interleaved everywhere.** Every module reaches for
   `subprocess`/`git(...)` inline, so there is no layer you can test without a
   real repository, and the load-bearing invariants are scattered across call
   sites as `raise RuntimeError`.
2. **Wire formats are untyped dicts.** `LS_FORK_*_V1` payloads are built and read
   with `data.get("field", default)`. Drift between writer and reader is only
   caught at runtime, and canonical encoding is re-implemented ad hoc.
3. **Destructive and non-destructive operations are not separated by
   construction.** `amalgamate_all.py` (the only code that rewinds lanes and
   force-pushes) sits beside pure planners; nothing structurally prevents a
   planner from mutating refs.
4. **The safety invariants are conventions, not types.** "remote-first fetch →
   target is-ancestor → ahead-only" (candidate freshness) and the replay
   *materialisation audit* (fingerprint match before a destructive rewind) are
   the two things that keep agent work from being lost. In Python they are
   sequences of asserts that a refactor can quietly reorder.
5. **Entry points are duplicated.** A dozen `.bat` files and per-agent scripts
   (`agent_land_json`, `gadget_land_json`, `land_json_patch`) repeat argument
   plumbing and dispatch.

## 2. The principled Haskell architecture

### 2.1 Functional core, imperative shell
Split every module into a **pure core** (data, formats, hashing, snapshot
comparison, path safety, classification, planning) and a **thin IO shell** (Git,
process, filesystem). Logic is pure and testable; effects live only at the edge.

### 2.2 One Git capability, injected
All git access goes through a single capability instead of scattered
`subprocess` calls:

```haskell
class Monad m => MonadGit m where
  gitRun :: [String] -> m GitResult        -- exit/stdout/stderr, never throws
  gitIn  :: FilePath -> [String] -> m GitResult
```

Production uses an IO instance (`System.Process`); tests use a pure transcript
instance. Snapshot/ancestor invariants are then enforced in exactly one place.

### 2.3 Typed wire formats, one module per format
Each `LS_FORK_*_V1` becomes an explicit record with `FromJSON`/`ToJSON` and a
**single canonical encoder** (`Forks.Hash.canonicalJson`, mirroring Python's
`json.dumps(sort_keys=True, separators=(",", ":"))`) so fingerprints are stable
and byte-identical to the Python output during the parity phase. The format
string is a tag validated on decode, not a magic value sprinkled through code.

### 2.4 Invariants as types, not asserts
Make the two load-bearing guarantees impossible to bypass:

- `FreshCandidate` — a newtype with **no public constructor**; the only way to
  obtain one is `requireCandidateFresh`, which performs remote-first fetch,
  `is-ancestor`, and ahead-only checks. Functions that push require a
  `FreshCandidate`, so you cannot push an ungated candidate.
- `MaterialisedLedger` — produced only by the replay audit that verifies every
  ledger entry's content fingerprints exist in the tree. The destructive
  amalgamation step (rewind + force-with-lease) **requires** one, so a lane can
  never be rewound before its work is proven preserved in the committed ledger.

### 2.5 Errors as values
A single `ForksError` sum type carried in `ExceptT ForksError m` (or `Either`).
No exceptions-as-control-flow, no `print(..., file=sys.stderr); return 1`.

### 2.6 Destructive isolation by namespace
Pure planners (`Forks.Plan.*`, `Forks.Accelerator`, `Forks.Workflow`) are
compiled **without `MonadGit` in scope** — they cannot touch refs even by
accident. The only destructive module is `Forks.Amalgamate`, and it is gated by
`MaterialisedLedger` (§2.4).

### 2.7 One dispatcher, thin shims
A single `lambda-script forks <command> ...` CLI (`Forks.Cli`/`Forks.Dispatch`)
routes every subcommand to a pure planner + an IO runner. The `.bat` files and
per-agent scripts collapse into thin shims that call the **wires-built gadget
exe** shared bay-wide. The ledger is the source of truth; agent lanes are
disposable caches.

## 3. Module map: Python → Haskell

| Python (scripts/forks)            | Haskell (LambdaScript.Forks.*) | Status |
|-----------------------------------|--------------------------------|--------|
| `forks.py` constants/git/snapshot | `Git`, `Hash`, `Snapshot`, `Manifest`, `Types`, `Error` | partial (Git/Hash done) |
| `forks.py` CLI (diff/stage/…)     | `Cli` + subcommand planners    | pending |
| `forks_dispatch.py`               | `Dispatch`                     | pending |
| `import_json_patch.py`            | `Patch`                        | **done (faithful)** |
| `land_json_patch.py`              | `Land`                         | **done** |
| `agent_land_json.py`              | `AgentLand`                    | pending |
| `gadget_land_json.py`             | `Land` (gadget target)         | partial |
| `replay_ledger.py`                | `ReplayLedger`                 | **done (faithful)** |
| `replay_sync.py`                  | `ReplaySync`                   | pending |
| `replay_plan.py`                  | `Plan.Replay`                  | pending |
| `submission_object.py`            | `Submission`                   | stub |
| `gadget_branches.py`              | `GadgetBranches`               | pending |
| `gadget_ingest_folder.py`         | `Ingest`                       | partial (`Gadget`) |
| `gadget_creation_agent.py`        | `Gadget` (orchestrator)        | partial |
| `gadget_promote.py`               | `Promote`                      | pending |
| `gadget_verify_profiles.py`       | `VerifyProfiles`               | pending |
| `amalgamate_all.py`               | `Amalgamate`                   | sketch — needs faithful rewrite |
| `gadget_amalgamate_safe.py`       | `Amalgamate` (safe entry)      | pending |
| `amalgamate_targets.py`           | `AmalgamateTargets`            | pending |
| `main_history.py`                 | `MainHistory`                  | partial |
| `workflow_plan.py`                | `Plan.Workflow`                | pending |
| `workflow_runner.py`              | `Workflow`                     | pending |
| `accelerator.py`                  | `Accelerator`                  | pending (this request's target) |
| `ensure_node_toolchains.py`       | — (optional gate, out of core) | deferred |

## 4. The self-hosting bootstrap

The migration is ordered so the system can drive itself as early as possible:

1. Land the **foundation** (`Types`, `Error`, `Git`, `Hash`, `Snapshot`) and the
   **patch/land/ledger** pipeline (already faithful) — the Haskell tool can now
   *land* JSON patches.
2. Land **`Accelerator`** — the Haskell tool can now read/advance this very
   plan and emit per-agent packets.
3. From that point, packets generated by the Haskell accelerator task the remote
   agents with the remaining slots; Opus is reserved for comprehension/replanning
   only. The Haskell `Amalgamate` is the last destructive piece to cut over,
   under the `MaterialisedLedger` gate, after parity is proven.

## 5. How the accelerator drives the work

`haskell-migration.json` is an `LS_FORK_ACCELERATOR_V1` state. Its canonical
runtime home is `forks/accelerators/lambda-script/lambda-script/haskell-migration.json`;
it is shipped here inside the gadget tree so it travels with the package it
plans (relocate on adoption).

- **agents**: `ed`, `edd`, `eddy`, `guy` — each holds one **distinct
  responsibility track** (a disjoint module namespace, so parallel lanes never
  collide on `owned_paths`).
- **slots**: dependency-ordered stages. A slot carries a global `objective` and a
  per-agent cell (`responsibility`, `owned_paths`, `patch_goal`, `plan`,
  `lookahead`). Per the tool's rules, agents elaborate a **3-slot window**
  (current implementation, next complete plan, plus-two lookahead); far slots are
  intentionally lighter until the cursor reaches them.
- **attempt loop**: a compile/verify failure stays on the same slot and records a
  new `attempt`; it does not advance.
- **advance gate**: a slot advances only when **every** agent cell is `accepted`
  or explicitly `skipped`. Acceptance records the landed `json_patch_sha256` and
  `ledger_path` so the work is traceable to the replay ledger.

### Track ownership (collision-free partition)
- **ed** — Foundation & Git: `Types`, `Error`, `Git`, `Hash`, `Snapshot`,
  `Manifest`, and the `forks` CLI subcommands.
- **edd** — Patch/Land/Ledger pipeline: `Patch`, `Land`, `ReplayLedger`,
  `Submission`, `AgentLand`, `ReplaySync`.
- **eddy** — Gadget & Amalgamation: `Gadget`, `GadgetBranches`, `Ingest`,
  `Amalgamate`, `AmalgamateTargets`, `Promote`, `MainHistory`, `VerifyProfiles`.
- **guy** — Planning & orchestration: `Accelerator`, `Plan.*`, `Workflow`,
  `Cli`, `Dispatch`, and the `.bat`→exe shims.

## 6. Verification & parity strategy

Build checks (cabal/npm) remain **optional gates, not defaults** — transport is
language-neutral. Correctness is proven by:

1. **Golden parity** — for a fixed corpus of patches/lanes, the Haskell tool must
   produce *byte-identical* canonical JSON, *identical* ledger fingerprints, and
   *identical* snapshot/manifest hashes to the Python tool.
2. **Property tests** — canonical-JSON determinism, fingerprint stability under
   re-encode, and the smart-constructor invariants (`FreshCandidate`,
   `MaterialisedLedger`) cannot be constructed off the gated path.
3. **Self-hosting smoke** — the Haskell tool lands and amalgamates its own next
   diff before Python is removed.

Python `scripts/forks/*.py` is deleted only after parity (1) holds for the whole
core and the self-hosting smoke (3) passes.
