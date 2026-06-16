# LambdaScript Haskell rewrite — prioritized completion plan

Completing grok's Haskell port of `foreign-language/lambda-script` into `projects/lambda-script`
(a Wires package, registered in `wire.project`). Priority: **build tools first, image-generation tools later** (user directive 2026-06-16).

## Confirmed state

DONE (build tools, in Haskell, in `lib/LambdaScript/`):
- glc compiler: `Parser/Parser`, `Core/{Ast,Check,Program,Diagnostic}`, `Compiler`, `Codegen/{Haskell,TypeScript}`, `Runtime/CppForeign`, `Bridge/{Bridge,Endpoint}`.
- gizmo host: `Gizmo/{Types,Manifest,Runner}` — wired into `LambdaScript.go` as `gizmo validate|status|provision-plan|call`.
- dispatcher `LambdaScript.go`: `--list/--describe/--self-test/parse/check/emit/gizmo`.

MISSING:
- **forks** (no `LambdaScript/Forks/`) — the remaining build tool. Critical path.
- tools parity, examples corpus, package bridge — minor build-side.
- image-generation/metrics tools — deferred.

## P0 — build tools (do first)

### P0.1 Forks port  ✅ DONE (2026-06-16) — compiles clean, wired into `LambdaScript.go` as `forks`
Modules: `Forks.Git` (origin-agnostic git layer + `gitInput`), `Forks.Patch` (LS_JSON_PATCH_V1),
`Forks.Land` (3× freshness-gate engine), `Forks.Gadget` (gadget land + ahead-only promote + receipt),
`Forks.MainHistory` (LS_MAIN_HISTORY_V1 receipts), `Forks.Amalgamate` (per-lane capture/apply/rewind
with expected-OID guards). Surface: `forks land-json|gadget-land|gadget-promote|amalgamate [--apply]`.
Thin follow-ups (non-blocking): auto-resolve verification-profile commands from the gizmo manifest
(currently a `[String]` hook, defaults to skip); the replay-materialisation fingerprint audit in
amalgamate is reduced to the OID-guard path; promotion receipts are written locally post-push
(not committed into the pushed tree as the Python does).

### (original) P0.1 Forks port
Port `scripts/forks/*.py` → `lib/LambdaScript/Forks/`, against the spec in
`foreign-language/lambda-script/docs/forks/AMALGAMATION_STATE_MACHINE.md`. Sequence (bottom-up):
1. `Forks.Git` ← `forks.py` git wrappers: `fetch/refExists/commit/aheadBehind/classify/mergeBaseIsAncestor`, `MAIN_REF`. **Keep the remote abstract** (origin-agnostic) — this is the foxhub seam.
2. `Forks.Submission` ← `submission_object.py` + `import_json_patch.py`: load `LS_JSON_PATCH_V1`, build submission (`changed_files/ahead/behind/patch_sha256/base_commit`), materialise candidate worktree.
3. `Forks.MainHistory` ← `main_history.py`: `LS_MAIN_HISTORY_V1` receipts.
4. `Forks.Land` ← `land_json_patch.cmd_land`: the core engine — **3× `requireCandidateFresh` (ahead-only, behind==0)**, verify, receipt, dry-run+push, optional agent sync.
5. `Forks.Gadget.Land` ← `gadget_land_json.cmd_land`: target = `origin/gadgets/<gizmo>/<gadget>/main`, manifest verification profile, deferred lane sync.
6. `Forks.Gadget.Promote` ← `gadget_promote.cmd_promote`: ahead-only gate, promotion worktree, receipt (gadget_promotion), push to main, sync repo agent lanes.
7. `Forks.Amalgamate` ← `amalgamate_all.py`: replay-materialisation audit (per-file fingerprints on integration) → per-lane capture/apply/rewind with **expected-OID guards**.
Then: add the modules to `package.garrage` `exposes`, and route `forks`/`amalgamate` verbs in `LambdaScript.go`. Build-verify each module before moving on.

### P0.2 Tools/CLI parity
Confirm `forks`/`glc`/`gizmo` command surfaces from the lambdascript gizmo manifest resolve through the Haskell exe (so `lambdascript.gizmo.json` is self-hosting in Wires form).

### P0.3 Examples corpus + package bridge
Port the `.ls` examples + the package-bridge mapping (see `docs/WIRES_PACKAGE_BRIDGE_PLAN.md`).

**P0 acceptance:** the built `lambda-script.exe` can land a JSON patch, amalgamate agent lanes, and promote a gadget to main against a local/offline `origin` (foxhub) — no Python, no TypeScript.

## P1 — image-generation tools (later)
- `tools/milk_metrics` (image metric toolkit) → Haskell.
- `metrics` gizmo / `image-metrics` gadget.
- image-processing endpoints in the web API; centrifuge.
Defer until P0 closes (build self-hosting loop in Haskell first).

## Invariants (from the spec — must hold in the port)
remote-first fetch before decisions · ahead-only freshness (3×/land) · content-bound receipts (patch_sha256 + changed_files + source head/tree) · two-stage isolation (agent→gadget-integration→main) · expected-OID guards on destructive ops · verification gate before push · lanes ephemeral, integration is truth · git/remote boundary kept abstract for foxhub.
