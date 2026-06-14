# Lambda Text Metrics

Rule-based text diagnostic scaffold for prompt and prose analysis. It mirrors the proxy/register/gate separation used by the image metric toolkit, but operates on visible text evidence while also accepting a single-image bundle workflow.

```sh
npm run build
npm test
node dist/src/cli.js analyze samples/good_prompt.txt --out runs/good
node dist/src/cli.js compare samples/good_prompt.txt samples/contaminated_prompt.txt --out runs/compare
node dist/src/cli.js analyze-bundle samples/bundle_example.tar --out runs/bundle
node dist/src/cli.js corpus-summary --out runs/corpus.json
node dist/src/cli.js generate-prompt --seed "warmer bashful private bedroom" --out runs/generated_prompt.txt
```

## Bundle input

`analyze-bundle` accepts either a folder or a `.tar`, `.tar.gz`, or `.tgz` containing exactly one image plus one caption/annotation text file. An optional prompt file is accepted when its filename contains `prompt` or `initial_prompt`.

The command writes the copied image, copied caption, optional copied prompt, `bundle_manifest.json`, `bundle_report.json`, `bundle_summary.txt`, and separate analyses for caption, prompt, and combined text.

## Corpus and generation

The package now includes a small seeded corpus of prompt, repair, diagnosis, and annotation entries. The generator uses a GPT-2-style causal next-token interface — tokenize, sparse transition matrix, sample, detokenize, rescore — but it uses a deliberately tiny sparse token-transition map rather than neural weights. This keeps RAM use very small and keeps the output inspectable.

Generation is conservative. A candidate prompt is scored by the same text metric; hard-gated outputs are rejected, and weak generations fall back to a stable corpus-derived repair phrase.

The tool is deterministic by default. It is not a trained classifier, and its scores are explanation-oriented rather than authoritative.
