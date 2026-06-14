# Merlin model

Merlin is a mock detector for agent-written code. Its purpose is to distinguish operational progress from semantic hollowing-out. A gremlin may compile a patch by introducing a stub, dummy branch, bypass, weakened return path, or test dilution; Merlin should make that kind of apparent progress visible before it is rewarded or accepted.

## Objects

A gear is a verification routine attached to a significant code junction. The gear checks that the component continues to transmit its intended semantic work rather than merely satisfying its type, interface, or compilation surface.

A gearbox is the collection of gears across a program. Because geared components compose, a gearbox can be treated as a gear for the whole program.

A mock signal is evidence that a patch has replaced semantic work with a placeholder. Early signals include explicit mock/stub language, `NotImplementedError`, unqualified `pass`, placeholder returns, dummy values, bypassed calls, and test weakening.

A Merlin scan is an auditable report over a tree of source files. It records file hashes, evaluated gears, active findings, suppressed findings, deterministic fingerprints, and enough location data to support review by an agent or operator.

## Current scope

Merlin currently works as a local source-tree scanner. It is developed and tested as ordinary tool code. It has no provisioning boundary, no external command capability model, and no import relationship to other toolchains.

The first operational form is deliberately conservative: a finding is evidence for review, not proof of fraud. Error-grade findings represent strong placeholder patterns such as empty return paths or explicit incomplete implementation markers. Warning-grade findings represent lower-confidence language signals that may also occur in legitimate detector code.

Suppression is part of the detector, not part of external orchestration. Inline suppressions support local intentional exceptions. JSON suppressions support path, rule, gear, or fingerprint matching with an explicit reason. Suppressed findings remain visible in the receipt unless the caller asks to hide them.

## Intended development path

The next useful embodiment is stronger gear semantics inside Merlin itself: more source-language-aware detectors, better boundary-sensitive checks, explicit test-integrity rules, suppression review tooling, and receipt-compatible JSON output. After extensive testing, a separate integration task may decide how Merlin should be provisioned by the surrounding tool system. That integration task should not be encoded in Merlin's own model or documentation while the detector is still being developed.
