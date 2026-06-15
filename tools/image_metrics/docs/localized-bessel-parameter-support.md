# Localized Bessel parameter-vector support

This stride makes the support entry itself a localized, mutable parameter vector.

Earlier sparse dictionary versions attached a seed to an entry and used it to produce a fixed matrix-like field. That was still too close to an unlocalized random matrix view. The current version treats each support entry as a localized Bessel-window atom with stochastic parameter adaptation.

Each active support entry may now perturb and then accept/reject updates to:

```text
cx, cy              local position
sigma               Gaussian window width
harmonic_order      angular harmonic order
radial_frequency    Bessel radial frequency
phase               angular phase
orientation         angular frame
channel             primary RGB channel
scale               coefficient scale
```

A trial samples a sparse active mask, proposes local perturbations for those entries, applies the resulting Gaussian-windowed Bessel atoms, scores the candidate, and accepts both the image update and the entry-parameter update when the similarity-penalized objective improves.

This turns the dictionary from "coefficient over rough support seeds" into "coefficient plus learned local wavelet parameters." The support remains localized and replayable from the seed, but its accepted trajectory is now part of the learned state.
