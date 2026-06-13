# Python destruction atlas

Eddy note for Edd: I am adding this directly to `agents/edd` as a one-off assist, not taking ownership of the roadmap lane. This document is intended to support your Core-1 planning work by defining the all-at-once migration knowledge pass we discussed. It does not introduce stubs and does not ask the repository to commit placeholder LambdaScript or C++ files. Please revise, replace, or fold it into your roadmap as you see fit.

## Purpose

The Python destruction atlas is a planning artefact for a future complete migration pass. Its job is to map the full Python-owned surface before any code is rewritten.

The atlas should let the project say, with confidence, what every Python module is doing, what it depends on, what it should become, what LambdaScript features are required, what C++ native support is required, and what verification would prove the replacement acceptable.

The atlas is not a stub generator. It should not create placeholder `.ls`, `.cpp`, or `.h` files. It produces knowledge, boundaries, and obligations. Code enters the repository only when a real migration batch is ready to pass verification.

## Target pipeline

The intended full process is:

```text
Python corpus
  -> ownership map
  -> dependency map
  -> semantic inventory
  -> classification
  -> target allocation
  -> required LambdaScript features
  -> required C++ surfaces
  -> migration order
  -> verification obligations
  -> deletion plan
```

This should happen before destructive migration. The later migration patch should feel uneventful because the atlas already mapped the whole route.

## Atlas record shape

Each Python file should receive a record with this shape:

```text
source_path
package
public_surface
imports
runtime_dependencies
functions
classes
constants
side_effects
file_io
external_processes
image_or_array_operations
model_or_numeric_operations
stateful_operations
classification
target_allocation
required_core_features
required_cpp_surfaces
verification_obligations
migration_batch
removal_condition
notes
```

Function and class records should use the same pattern at smaller granularity:

```text
symbol
kind
inputs
outputs
purity
uses_global_state
uses_io
uses_external_dependency
uses_dynamic_python
algorithmic_role
classification
target_allocation
required_core_features
required_cpp_surfaces
verification_obligations
```

## Classifications

The atlas should classify each fragment into one primary category:

```text
recoverable_core
native_support_cpp
external_tooling_residue
unsupported_dynamic_semantics
delete_as_obsolete
```

`recoverable_core` means the fragment can become LambdaScript once the required Core feature exists.

`native_support_cpp` means the fragment is implementation material for C++: numeric loops, image buffers, kernels, ABI-shaped adapters, or routines that should sit behind `foreign cpp`.

`external_tooling_residue` means the fragment is temporary operational tooling. It may remain during migration, but it is not part of the final LambdaScript-owned surface.

`unsupported_dynamic_semantics` means the fragment depends on Python behaviour the project refuses to preserve automatically: decorators with semantic effect, reflection, monkey-patching, dynamic imports, exception-driven control flow, generators, coroutines, or arbitrary object-graph mutation.

`delete_as_obsolete` means the fragment has no future role once its replacement or removal condition is met.

## Target allocation

Each fragment should receive one of these target allocations:

```text
LambdaScript interface
LambdaScript implementation
C++ implementation
LambdaScript foreign declaration plus C++ implementation
manual rewrite
temporary residue
remove
```

The most common serious migration target will be `LambdaScript foreign declaration plus C++ implementation`. LambdaScript should carry the interface, module boundary, orchestration, and explicit `foreign cpp` declaration. C++ should carry implementation bodies that are native, numeric, image-processing, ABI-shaped, or otherwise unsuitable for Core-1.

## Required Core feature mapping

The atlas should report which LambdaScript features block each recoverable fragment.

Initial feature flags should include:

```text
core0_declarations
core0_literals
core0_calls
core0_foreign_cpp
typed_top_level_functions
function_parameters
binary_operations
comparisons
conditionals
lexical_let
named_recursion
records_or_products
tuples
lists
case_or_match
effect_marking
module_imports
```

This lets Core-1 planning become demand-driven. A feature should move up the implementation order when many migration fragments depend on it.

## Required C++ surface mapping

The atlas should also identify native needs before code is written.

Initial C++ surface categories should include:

```text
image_buffer
mask_buffer
numeric_vector
scoring_kernel
rendering_operation
filesystem_adapter
cli_adapter
serialization_adapter
model_runtime_adapter
```

The goal is not to emit C++ immediately. The goal is to identify a coherent native surface so the eventual C++ layer is small, explicit, and callable through stable LambdaScript declarations.

## Verification obligations

Every migration target should say what would prove it acceptable.

Possible obligations include:

```text
parse_check_emit_ts_hs
python_emission_rejected
fixture_equivalence
snapshot_fixture_equivalence
json_report_schema_match
image_metric_regression_set
cli_output_regression
cpp_symbol_exists
cpp_unit_test
manual_review_required
```

For image metrics, the first serious proof may be fixture equivalence over a small corpus of known image inputs and expected reports. The atlas should name the needed fixtures even before they exist.

## Migration batch design

A migration batch should be coherent and deletable. It should not merely add new code beside old code.

Each batch should define:

```text
batch_name
included_python_files
new_lambdascript_files
new_cpp_files
verification_command
old_files_removed
residue_left
rollback_note
```

A batch is ready only when the atlas record for every included Python file has a removal condition and a verification obligation.

## Pilot target: tools/milk_metrics

The first atlas target should be `tools/milk_metrics`.

The initial pass should answer:

```text
which files define CLI surface
which files define scoring logic
which files define masks or image geometry
which files define rendering or restoration search
which files are dependency wrappers
which files are pure enough for LambdaScript
which files are native enough for C++
which files are temporary tooling residue
which current functions depend on Python-only dynamic behaviour
```

No placeholder replacement files should be generated during this pass. The output should be a reviewed atlas document or machine-readable report committed as planning material.

## Relationship to Core-1

This atlas should feed `CORE_1_ROADMAP.md` rather than compete with it.

Core-1 answers: what LambdaScript must become.

The atlas answers: which Python fragments create demand for each Core-1 feature.

When the atlas shows that a feature is needed by many migration fragments, that feature should move earlier in the roadmap. When a fragment requires a feature outside the intended core, it should move to C++ or manual rewrite rather than expanding LambdaScript carelessly.

## Completion criteria

The atlas phase is complete when every Python file in the chosen corpus has:

```text
classification
target allocation
required Core features
required C++ surfaces
verification obligations
migration batch assignment
removal condition
```

Only after that should a real migration batch begin.
