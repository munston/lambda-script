# Accelerator workflows

An accelerator is a state file for staged parallel-agent development. It sits above forks, gizmos, gadgets, replay ledgers, and amalgamation. It does not replace those tools; it controls the planning cadence so that multiple agents can work continuously without collapsing into the same local task.

## Purpose

The accelerator records a sequence of slots. Each slot has a shared objective and a per-agent track. A track records the agent's responsibility, likely path ownership, lookahead, complete plan, implementation goal, verification attempts, and accepted replay entry.

This makes three things explicit:

```text
what the agent is doing now
what the agent is preparing next
what the agent is looking ahead toward after that
```

## Three-stage cadence

For slot `n`:

```text
slot n     = implementation slot
slot n + 1 = complete plan slot
slot n + 2 = lookahead slot
```

At the start of a turn, the agent should already have partial content in `n + 1` and `n + 2` from the previous turn. During the turn:

```text
1. Complete the current slot patch.
2. If verification rejects the patch, remain in the same slot and record another attempt.
3. Once accepted, complete the plan for the next slot.
4. Refresh the plus-two lookahead.
5. Advance only when all active agents are accepted or explicitly skipped.
```

## Non-overlap

Each agent track can declare `owned_paths`. Accelerator status reports duplicated owned paths as collisions. A collision is not always wrong, but it should be visible before agents generate conflicting patches.

## Commands

Create:

```bat
forks.bat accelerator init lambdascript core lsc1 --agents ed edd eddy --slots 7 --objective "Reach the first compiler completion stage"
```

Set objective:

```bat
forks.bat accelerator set-slot lambdascript core lsc1 1 --objective "Boolean logic and backend parity"
```

Set agent plan:

```bat
forks.bat accelerator set-agent lambdascript core lsc1 edd 1 --responsibility "Boolean syntax/checking" --paths "glc/src/parser/,glc/src/core/" --plan "Implement unary boolean negation with tests"
```

Show working packet:

```bat
forks.bat accelerator packet lambdascript core lsc1 edd
```

Record failed compile loop:

```bat
forks.bat accelerator attempt lambdascript core lsc1 edd 1 --status failed --error-file err.txt
```

Record accepted patch:

```bat
forks.bat accelerator accept lambdascript core lsc1 edd 1 --ledger-path forks/replay-ledger/gadgets/lambdascript/core/edd.json --sequence 3
```

Advance:

```bat
forks.bat accelerator advance lambdascript core lsc1
```

## Relationship to amalgamation

Accelerator files do not apply code changes. They coordinate the agent path. JSON patch landing records replay history. Gadget amalgamation audits and propagates accepted replay-backed content. This separation is deliberate.
