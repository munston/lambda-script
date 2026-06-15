# Pre-land gadget refresh

The fast gadget path saves time by skipping repository-agent and gadget-agent fan-out after each small patch. That saving must be paired with a stronger base invariant: before a new JSON patch is imported, the gadget integration branch is refreshed against `origin/main`.

The gadget branch is treated as a replay surface. It may hold accepted local work, but it should be ready to rebase onto a newer `main` whenever another agent advances the repository.

The targeted agent lander therefore uses `target.refresh`, defaulting to `true`:

```json
{
  "target": {
    "kind": "gadget",
    "gizmo": "lambdascript",
    "gadget": "core",
    "refresh": true,
    "promote": false,
    "sync": false
  }
}
```

Refresh states:

```text
even
  The gadget branch already matches main. Land the patch.

ahead-only
  The gadget branch contains local gadget work and already includes current main. Land the patch.

behind-only
  The gadget branch has no unique work and main moved forward. Move the gadget integration branch to origin/main, then land the patch.

diverged
  The gadget branch has local work and main also moved forward. Rebase the gadget branch onto origin/main, run the selected verification profile, push the refreshed integration branch, then land the patch.
```

The pre-land refresh does not force-align gadget agent lanes. Lane fan-out remains controlled by `target.sync`. Repository-agent fan-out remains controlled by promotion and `target.repository_sync`.

Use `refresh: false` only when intentionally diagnosing a stale branch or recovering a failed rebase manually.
