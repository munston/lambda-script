# Automatic rebase before one-call promotion

Targeted JSON buttons now perform the missing pre-promotion rebase step internally.

When a patch target contains:

```json
{
  "promote": true,
  "sync": true,
  "history": true
}
```

the agent button performs this transaction:

```text
land patch to the target gadget branch
align gadget-agent lanes to the accepted gadget head
inspect gadget branch against origin/main
if diverged, rebase the gadget branch onto origin/main in a disposable worktree
verify the rebased gadget
force-with-lease update the gadget branch
align gadget-agent lanes again
promote to main
record main-history unless history=false
sync repository agent lanes through promotion
normalize the promoted gadget branch and gadget-agent lanes to origin/main
print final status
```

The intended operator command remains:

```bat
guy-land-json.bat C:\Users\guyas\Downloads\patch.json
```

The older `gadget-promote`, `gadget-status`, and direct Git commands remain implementation/debug primitives rather than normal operator steps.
