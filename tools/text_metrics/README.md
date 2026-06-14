# Lambda Text Metrics — portable parametric stride

This package is intentionally Windows-portable. The current backend is a pure TypeScript shim that preserves the public image-metric interface and the parametric train/test behaviour while avoiding native build dependencies.

There is no runtime dependency on `node-gyp`, C/C++ compilation, platform-specific headers, downloaded Node headers, ImageMagick, absolute Unix paths, or native addons. The shim derives deterministic, numerically plausible feature vectors from RGB buffers, ordinary file bytes, or synthetic fixture identifiers. This is deliberate: it lets the `metrics/text-metrics` gadget land, build, and verify on a normal Windows checkout. A native or real analyser integration can be added later as an optional backend.

## Verification

```bat
npm install
npm run build
npm test
node dist\src\cli.js parametric-demo --out runs\parametric-demo
node dist\src\cli.js image-parametric-demo --out runs\image-parametric-demo
```

## Commands

```bat
node dist\src\cli.js parametric-demo --out <dir>
node dist\src\cli.js image-parametric-demo --out <dir>
```

`parametric-demo` exercises the seeded short-support Gaussian-mask expansion, sparse coefficient field, zero-mean additive control default, Monte Carlo mutual-training loop, base classifier training, and learned per-control scale vector.

`image-parametric-demo` exercises the same parametric loop against deterministic image-feature records. With no image paths supplied, it generates synthetic fallback feature records. With image paths supplied, it reads file bytes and derives stable byte-statistical feature vectors. It never shells out and never decodes images through external tools.

## Generated outputs

`parametric-demo` writes:

- `parametric_demo_report.json`
- `parametric_demo_summary.txt`

`image-parametric-demo` writes:

- `analysis_XX/report.json`
- `analysis_XX/summary.txt`
- `image_parametric_report.json`
- `image_parametric_summary.txt`
