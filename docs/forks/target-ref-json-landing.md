# Target refs in JSON landing

This patch introduces target-ref support to the JSON landing path.

The default remains repository main:

```bat
forks.bat land-json-file eddy patch.json
```

which is equivalent to:

```bat
forks.bat land-json-file --target-ref origin/main eddy patch.json
```

The JSON importer can now create a candidate from another integration ref:

```bat
forks.bat import-json --target-ref origin/gadgets/metrics/image-metrics/main eddy patch.json
```

The one-shot landing path can also push to a non-main target:

```bat
forks.bat land-json-file --target-ref origin/gadgets/metrics/image-metrics/main eddy patch.json
```

When the target ref begins with `origin/`, the push destination is inferred by stripping `origin/`. For unusual refs, pass `--push-ref` explicitly:

```bat
forks.bat land-json-file --target-ref origin/gadgets/metrics/image-metrics/main --push-ref gadgets/metrics/image-metrics/main eddy patch.json
```

For non-main targets, repository-level agent sync is skipped. Gadget-specific agent lanes will be added by the later gadget branch model patch.

This is an incremental refactor. The legacy `forks stage`, `forks verify`, and `forks submit` path still targets `origin/main`; target-ref support is first enabled on the JSON path because that is already the current patch transport used by agents.
