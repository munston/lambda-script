# wavproc Haskell WAV classifier baseline

This is a Haskell-only WAV processing and learning baseline. It vendors `Data.WAVE` for PCM WAV reading/writing and adds feature extraction plus a supervised nearest-centroid classifier.

## Build

```bash
cabal build
cp dist-newstyle/build/x86_64-linux/ghc-*/wavproc-*/x/wavproc/build/wavproc/wavproc ./wavproc
```

## Audio processing

```bash
./wavproc info input.wav
./wavproc features input.wav
./wavproc gain 1.5 input.wav output.wav
./wavproc normalize input.wav output.wav
./wavproc reverse input.wav output.wav
./wavproc mono input.wav output.wav
```

## Learning and classification

Dataset format:

```csv
label,path/to/file.wav
other_label,path/to/other.wav
```

Relative paths are resolved from the dataset file directory.

```bash
./wavproc train-centroid dataset.csv model.txt
./wavproc predict model.txt input.wav
./wavproc eval model.txt dataset.csv
```

The current learner extracts fixed time/frequency summary features, standardizes them from the training set, computes one centroid per class, and predicts by nearest standardized centroid. It uses no Hackage dependencies beyond packages already bundled with the GHC installation.
