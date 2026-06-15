# Image Metrics path handling note

`image-metrics.bat` preserves the caller's current directory when running the compiled CLI. Relative image paths and `--out` paths are therefore resolved from the directory where the user invoked the command, not from `tools\image_metrics`.

Real file inputs must decode as image pixels. The native bridge no longer falls back to byte-derived pseudo-frames for ordinary file paths. If Windows WIC cannot decode the file, the command fails instead of writing a misleading `source.bmp`.
