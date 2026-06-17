# Gadget and Gizmo Lifecycle Notes

This note records the current working model for gadgets, gizmos, bare detachment, reattachment, and the role of self/tooling components in the build and submission lifecycle.

## 1. Gadget identity

A gadget is the unit of continuity. It is not merely a folder, branch, or patch stream. A gadget incorporates its identity, materialised source tree, replay history, lane structure, patch target, and relationship to a gizmo.

The useful vocabulary is therefore:

```text
bare gadget
registered gadget
unregistered gadget
re-registered gadget
```

Avoid introducing a second object name for the same continuity. If a gadget is detached, exported, or maintained outside the active gizmo, it remains the gadget in bare or detached form. It should carry enough information to re-enter a managed gizmo without losing its history.

A gadget may include:

```text
gizmo/gadget identity
materialised root path
registration metadata
permission and lane structure
last replay or materialisation baseline
patch routing target
history of durable replay entries
tool exposure when inside a gizmo
portable build/diff behaviour when outside a gizmo
```

## 2. Bare gadget versus gizmo-contained gadget

A bare gadget is a portable development unit. It can have its own source tree, build files, local baseline, and local diff/patch stewarding. It may be maintained directly by agents outside the permission system of a gizmo.

A gadget inside a gizmo is the same unit placed inside a managed composition environment. The gizmo adds:

```text
permission boundaries
agent lane routing
write restrictions
shared executable provisioning
connection to other gizmos
replay/amalgamation policy
tool exposure to connected gizmos
```

The difference is not merely registration metadata. A gizmo-contained gadget is inside an authority and tooling enclosure. Agents are allowed to work on their assigned gadget or gadgets, and the gizmo should prevent them from seeing or modifying unrelated protected gadgets unless explicitly granted.

## 3. Gizmo-vended tooling

A gadgetless gizmo lacks the operational tooling required for patch application, replay, amalgamation, lane sync, and submission. Those capabilities are not inherent to the abstract idea of a gizmo; they are vended by self/tooling gadgets.

This is why the self/tooling layer matters. Items such as wires, forks, onepush, sandbox, buttons, folders, and related build/submission machinery are not ordinary project conveniences. They are the substrate that lets gizmos and gadgets operate.

There are at least two self/tooling layers:

```text
wires self/tooling
  governs project/package construction, materialisation, build layout, buttons, and folder structure

gizmo/gadget self/tooling
  governs gadget registration, patch capture, replay, onepush, sandbox access, lane routing, amalgamation, and permissioned submission
```

The tooling itself should be protected as gadgets inside a suitable self/tooling gizmo. Other gizmos may connect to that tooling gizmo and receive the executables it provides, while ordinary agents remain unable to casually modify the foundational tooling.

## 4. Permissions and visibility

A gizmo restricts access and write permissions over its gadgets. An agent assigned to one gadget should not have general write access over other gadgets in the same gizmo. If an agent can maintain several gadgets, that assignment is explicit, and those gadgets are the visible/writeable scope.

The same principle applies to self/tooling gadgets. A project agent may use the build and submission tools, but should not modify the code defining those tools unless specifically assigned to that self/tooling gadget.

This gives a hierarchy:

```text
ordinary project gadget
  editable by assigned project agents

self/tooling gadget
  executable tools exposed to projects
  write-protected except to assigned tooling agents

connected gizmo
  imports executable capabilities
  does not automatically gain write authority over the supplying self/tooling gadgets
```

## 5. Detachment forms

A gadget can leave the active gizmo environment in several forms.

### 5.1 Bare gadget

A bare gadget carries its source tree and enough local stewarding to compute a safe delta from its last managed baseline. It is lightweight and convenient where the full gizmo environment is unnecessary.

A bare gadget should preferably retain one small local program or steward capable of:

```text
identifying the gadget root
tracking the last replay/materialisation baseline
normalising paths
applying ignore rules
reporting status
computing diffs
creating a JSON patch for re-entry
```

This local steward should not try to reproduce the whole gizmo environment. It helps the gadget remain coherent while bare and produce a re-entry patch later.

### 5.2 Wires-project detached form

A gadget may also be detached into a Wires-project-like form so it remains buildable. This may include a copy of connected build substrate components such as projects/self. That is convenient but weakens write protection: agents can alter the carried self/tooling copy while maintaining the gadget.

Such changes may be legitimate. For example, the detached gadget may require backward-compatible improvements to buttons, folders, or build materialisation. But those changes are not automatically ordinary gadget changes. On return, they must be separated from the gadget delta and routed to the appropriate self/tooling gadget.

### 5.3 Minimal detached gizmo

A more controlled detached form is a minimal gizmo. It contains the target gadget plus only the required self/tooling gizmos or self components needed to build and submit it. The tooling remains separated and write-protected, rather than being copied into the ordinary editable project tree.

This form is often preferable. It preserves buildability while keeping the authority boundary intact. The detached gadget remains in a managed enclosure, and protected self/tooling components remain protected.

## 6. Reattachment and external deltas

When a bare or detached gadget returns, the system should not ingest the entire folder as opaque fresh content. The correct operation is:

```text
identify the final replay/materialisation state from when the gadget departed
compare the returning tree against that baseline
create a new patch representing only the external delta
land that patch as a new replay entry
allow normal amalgamation under gizmo policy
```

This is why the final history replay state matters. A detached gadget returning to a gizmo should present a delta from its last managed baseline, not an unexplained replacement tree.

For detached forms that include build substrate or self/tooling copies, reattachment must split the returning changes:

```text
gadget delta
  routed to the returning gadget target

self/tooling delta
  routed to the relevant self/tooling gadget target

connection or registration delta
  routed to gizmo metadata or registration handling
```

Ordinary gadget reattachment must not silently mutate protected tooling.

## 7. Unregistration and registration

Unregistration should not mean destroying the gadget. It should mean moving the gadget out of active gizmo containment into bare or detached status while preserving its identity, baseline, and history.

A minimal unregister operation should remove or disable:

```text
active gizmo membership
generated access buttons for that active membership
ordinary lane/amalgamation participation
active permission grants for the gizmo-contained form
```

It should preserve:

```text
gadget identity
materialised source tree if requested
replay history
baseline marker
detached build/diff stewarding
enough registration metadata to return
```

Registration is the reverse boundary operation. It brings a gadget into a gizmo’s permission and tooling enclosure. If the gadget has changed while detached, registration should calculate and land the delta from the final managed baseline.

It is probably unnecessary to expose separate high-level commands for “re-register” and “reincorporate-from-dir.” The meaningful operation is registration, with optional external content delta. Internally, this may split into metadata restoration and content patch creation, but the user-facing lifecycle should remain simple.

## 8. Initialisation

Initialisation exists in more than one form.

Blank initialisation creates a gadget identity and empty materialisation baseline. It gives future patches a clean starting point: delta from an empty or minimal gadget root.

Initialisation from a directory already exists in the current workflow and should be preserved. It creates or materialises a gadget from a folder and routes that folder content through the existing submission path. Future Haskell work should not reinvent this behaviour; it should port or wrap the existing semantics behind the sandbox surface.

The important lifecycle distinction is:

```text
init-blank
  create gadget identity and empty baseline

init-from-dir
  create gadget identity and first content patch from a folder

register existing detached gadget
  restore active gizmo membership, optionally with a delta from detached baseline

unregister
  leave active gizmo membership while preserving gadget continuity
```

## 9. Sandbox surface

The intended public surface should remain small. Lower-stage tooling should be hidden behind sandbox and onepush-style access points.

Current direction:

```text
cabal run sandbox -- help
cabal run sandbox -- onepush
cabal run sandbox -- onepush --ship
cabal run sandbox -- onepush --init-from-dir DIR
cabal run sandbox -- land PATCH_JSON
```

Lifecycle commands can be added later, but they should reduce internally to the same durable operations: descriptor/registration change, content delta patch, replay entry, and materialisation audit.

A future lifecycle surface may look like:

```text
cabal run sandbox -- gadget init-blank ...
cabal run sandbox -- gadget init-from-dir ...
cabal run sandbox -- gadget unregister ...
cabal run sandbox -- gadget register ...
```

The exact arguments should follow the existing target-resolution model and avoid exposing unnecessary refs, branches, or implementation details.

## 10. Design invariants

The following invariants should guide implementation:

```text
The gadget is the continuity object.
The gizmo supplies authority, visibility, and tools.
Self/tooling gadgets provide the operational substrate.
A gadgetless gizmo lacks patch/amalgamation capability until connected to tooling.
Agent lanes are disposable carriers.
Replay history and materialisation baselines are durable.
Detached gadgets re-enter by delta from final managed replay state.
Tooling changes made while detached must be routed to tooling gadgets.
Initialisation from directory already exists and should be preserved.
New lifecycle work should not introduce redundant objects or duplicate working components.
```

## 11. Practical consequence for the current migration

The immediate Haskell migration should remain conservative. It should first stabilise the sandbox command surface and typed target/config modules, then port existing working behaviours behind that surface.

Do not introduce new lifecycle object names where the word “gadget” already carries the required meaning. Do not duplicate init-from-dir. Do not treat folder ingest as opaque replacement when a replay baseline exists. Do not allow detached self/tooling edits to return as ordinary project changes.

The target state is a system where gadgets can move between contained, bare, and minimally contained forms while preserving buildability, replay continuity, and permission separation.
