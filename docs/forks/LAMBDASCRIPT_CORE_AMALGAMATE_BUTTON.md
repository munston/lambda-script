# LambdaScript core amalgamation button

Run this after agent JSON submissions have been landed to their own gadget-agent lanes:

```bat
amalgamate-lambdascript-core.bat
```

It performs the normal final step for the current LambdaScript core workflow:

```text
git fetch origin --prune
python scripts\forks\amalgamate_all.py --gadget lambdascript core --agents ed edd eddy guy --apply
python scripts\forks\gadget_branches.py status lambdascript core
```

The selected lanes are explicit:

```text
ed
edd
eddy
guy
```

The wrapper intentionally omits `--require-ledgers`, because `guy` is the operator/local working lane and may not always have its own replay ledger. Replay/materialisation checks still run for ledgers that exist, and strict code/tooling paths remain guarded by the amalgamation script.
