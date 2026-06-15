# Image Metrics diagnostics

The stochastic update command writes both the ordinary updated frame and amplified diagnostics:

```text
updated.bmp          accepted best frame
delta.bmp            neutral grey + amplified signed pixel difference
delta_overlay.bmp    source image with amplified change magnitude highlighted
report.json          score, acceptance, and pixel-delta statistics
update_summary.txt   compact run summary
```

If `updated.bmp` looks visually identical to `source.bmp`, inspect `delta_overlay.bmp` and the `mean_abs_pixel_delta`, `max_abs_pixel_delta`, and `rms_pixel_delta` fields. Use a larger `--step`, more `--trials`, or more `--support` only after confirming the update is present but visually too small.
