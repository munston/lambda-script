# Image Metrics

TypeScript image metric command surface backed by a native C++ byte-processing bridge.

This package replaces the previous Python operator path. It builds a small C++ executable and calls it from TypeScript. If no C++ compiler is available, the TypeScript portable byte backend remains available so the package can still build and run smoke tests.

## Build

```bat
cd tools\image_metrics
npm install
npm run build
npm test
```

The native backend is compiled from:

```text
native/image_metrics_ffi.cpp
```

and written to:

```text
bin/image_metrics_ffi.exe
```

## Analyze

```bat
cd tools\image_metrics
npm run image-metrics -- analyze synthetic://demo --out runs\analyze
```

For a real file, pass the file path. The current native bridge uses byte-level analysis and synthetic fixtures; it does not yet decode PNG pixels through stb/libpng.

## Parametric adaptation

```bat
cd tools\image_metrics
npm run image-metrics -- image-parametric-demo --out runs\image-parametric-demo synthetic://a synthetic://b
```

This runs stochastic metric adaptation over analyzer-derived feature vectors using the TypeScript parametric trainer and the C++ image metric bridge.

This is not Python. It is TypeScript orchestration plus a native C++ processing executable.
