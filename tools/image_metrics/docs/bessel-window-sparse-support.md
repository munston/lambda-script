# Bessel-window sparse support dictionary

The image update support dictionary now uses Gaussian-windowed Bessel harmonics rather than smoothed random Gaussian lobes.

Each support entry is a short vector of deterministic parameters:

```text
center:            cx, cy
window:            sigma
channel:           primary RGB channel
harmonic_order:    integer angular order m
radial_frequency:  radial Bessel frequency
phase:             angular phase
orientation:       angular frame rotation
scale:             learned/adapted coefficient scale
```

The support value applied to the image is:

```text
exp(-rho^2 / 2) * J_m(k rho) * cos(m(theta - orientation) + phase)
```

with RGB channel mixing applied per channel. This keeps the sparse update deterministic from the support entry seed, while allowing directional or circularly symmetric wavelet-like structures. The scalar coefficient is still updated per support entry, but the dictionary entry now contains a vector of harmonic parameters rather than a single point/intensity slot.
