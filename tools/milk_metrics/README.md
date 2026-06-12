# Milk Metrics

Small local image-analysis toolkit for the experimental milk-metric work.

The package scores raw images or crops with a conservative diagnostic metric. It can also run a constrained restoration search that tries to reduce compression artefacts while preserving the source geometry. The restoration step is not a generative edit and should not be treated as increasing the underlying image quality by itself; the useful outputs are the raw score, component report, masks, overlays, and before/after diagnostics.

## Install

From this directory:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On MSYS2 / Linux / macOS:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Analyze an image

```sh
python -m milk_metrics.cli analyze path/to/image.png --out runs/example
```

This writes `original.png`, `positive_response_mask.png`, `penalty_mask.png`, `response_overlay.png`, `components.png`, and `report.json`.

## Run conservative restoration search

```sh
python -m milk_metrics.cli restore path/to/image.png --out runs/example --steps 360 --seed 41
```

This writes the analysis outputs plus `restored.png`, `before_after.png`, `change_map.png`, and `score_trace.png`.

The search is deliberately constrained. It uses median filtering, partial Gaussian smoothing, small sharpness adjustments, and small contrast adjustments. It does not apply geometric warps.

## Penalty mask only

```sh
python -m milk_metrics.cli penalty-mask path/to/image.png --out runs/example
```

The penalty mask is a crude diagnostic proxy. It marks high-chroma warm or magenta signal and public-context proxies where enabled by the metric. It is not a semantic detector.

## Metric intent

The provisional score rewards smooth surface regions, compression cleanliness, private-room or soft substrate cues, garment-boundary structure, whole-person or upper-region context proxies, and edge preservation under restoration.

The provisional score penalizes distortion introduced by processing, edge loss from over-smoothing, public-context proxy signal, and high-chroma proxy signal.

The code is intentionally inspectable and rule-based. It should be treated as a research scaffold, not a trained classifier.
