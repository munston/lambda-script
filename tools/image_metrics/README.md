# Image Metrics

TypeScript command surface backed by a native C++ sparse-Gaussian image update bridge.

This is the non-Python image analyzer path. The package builds `native/image_metrics_ffi.cpp` into `bin/image_metrics_ffi.exe` and calls it from TypeScript.

```bat
cd tools\image_metrics
npm install
npm run build
npm test
```

Repository-root use:

```bat
image-metrics.bat analyze synthetic://demo --out runs\image-analyze
image-metrics.bat image-parametric-demo --out runs\image-parametric-demo synthetic://a synthetic://b
image-metrics.bat stochastic-update synthetic://demo --out runs\stochastic-update --seed 20260615 --trials 96 --support 24 --step 0.020
```

`image-parametric-demo` learns feature-space adaptation over analyzer-derived feature vectors.

`stochastic-update` is the pixel/frame update stage. It builds a deterministic sparse support dictionary from the seed. Each support coefficient indexes a deterministic Gaussian random matrix over the frame, with anchor, channel, sigma, and seed derived from that dictionary position. Each trial samples a random active mask over the sparse support, applies the weighted Gaussian addition to pixel values, re-scores the candidate, accepts score-improving candidates, and adapts the support-vector scales. It writes:

```text
source.ppm
updated.ppm
report.json
update_trace.json
support_dictionary.json
update_summary.txt
```

The current native bridge emits PPM frames and uses byte/synthetic fixtures. A later stride should replace the byte bridge with decoded PNG/JPEG pixel buffers through the supported C ABI.
