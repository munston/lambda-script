from __future__ import annotations

import numpy as np


def hsv_like(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return hue, saturation, value in [0, 1] from RGB float array in [0, 1]."""
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    diff = mx - mn + 1e-6

    sat = diff / (mx + 1e-6)
    val = mx

    hue = np.zeros_like(mx, dtype=np.float32)
    mr, mg, mb = mx == r, mx == g, mx == b

    hue[mr] = ((g[mr] - b[mr]) / diff[mr]) % 6
    hue[mg] = ((b[mg] - r[mg]) / diff[mg]) + 2
    hue[mb] = ((r[mb] - g[mb]) / diff[mb]) + 4
    hue = hue / 6.0

    return hue.astype(np.float32), sat.astype(np.float32), val.astype(np.float32)
