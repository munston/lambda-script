# Image Metrics

TypeScript command surface backed by a native C++ byte-processing bridge.

This is the non-Python image analyzer path. The package builds `native/image_metrics_ffi.cpp` into `bin/image_metrics_ffi.exe` and calls it from TypeScript. If a C++ compiler is unavailable, the TypeScript byte fallback remains available.

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
```

The current native bridge uses byte-level analysis and synthetic fixtures. A later stride should replace the byte bridge with decoded pixel buffers through the supported C ABI.
