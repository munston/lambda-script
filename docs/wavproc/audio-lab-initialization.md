# audio-lab/wavproc initialization and landing

`audio-lab/wavproc` is an independent audio-processing gadget. It is not part of `lambdascript`, and it should not be initialized as `lambdascript/wavproc` or registered in the LambdaScript compiler gizmo.

The required branch initialization is branch-first:

```bat
cd /d "C:\Users\guyas\Desktop\codebase\7\ollama.wires\foreign-language\lambda-script"

git fetch origin --prune

git restore --source=origin/gadgets/lambdascript/core/main -- forks.bat scripts/forks/forks_dispatch.py scripts/forks/gadget_branches.py scripts/forks/forks.py

python scripts\forks\gadget_branches.py init audio-lab wavproc
python scripts\forks\gadget_branches.py status audio-lab wavproc
```

Expected lanes:

```text
gadgets/audio-lab/wavproc/main: even
gadget-agents/audio-lab/wavproc/ed: even
gadget-agents/audio-lab/wavproc/edd: even
gadget-agents/audio-lab/wavproc/eddy: even
gadget-agents/audio-lab/wavproc/guy: even
```

The first materialisation cannot use `edd-land-json.bat`, because that button is manifest-gated and the `audio-lab` manifest does not exist before this initial patch. Use the target-ref JSON path for the first landing:

```bat
forks.bat land-json --target-ref origin/gadgets/audio-lab/wavproc/main --no-sync edd "C:\Users\guyas\Downloads\edd_audio_lab_wavproc_initial_patch.json"
```

After that, run audited gadget amalgamation so the selected lane is aligned to the gadget integration branch:

```bat
forks.bat amalgamate-all --gadget audio-lab wavproc --agents edd --apply
python scripts\forks\gadget_branches.py status audio-lab wavproc
```

For local testing, use a worktree from the gadget integration branch:

```bat
git worktree add %USERPROFILE%\audio-lab-wavproc-test gadgets/audio-lab/wavproc/main
cd %USERPROFILE%\audio-lab-wavproc-test\tools\wavproc
cabal build
cabal run wavproc -- --help
```

After the first materialisation, the branch contains `examples/gizmos/audio-lab.gizmo.json`. If a later tool invocation needs to read the manifest from the current working tree, restore that file from the gadget branch before using manifest-gated commands:

```bat
git restore --source=gadgets/audio-lab/wavproc/main -- examples/gizmos/audio-lab.gizmo.json
```
