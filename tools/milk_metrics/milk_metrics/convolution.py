from __future__ import annotations

import numpy as np

KX = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]], dtype=np.float32) / 8.0
KY = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=np.float32) / 8.0
LAPLACIAN = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32)


def conv2d(x: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Small reflected-boundary 2D convolution for diagnostic masks."""
    py, px = kernel.shape[0] // 2, kernel.shape[1] // 2
    padded = np.pad(x, ((py, py), (px, px)), mode="reflect")
    out = np.zeros_like(x, dtype=np.float32)

    for i in range(kernel.shape[0]):
        for j in range(kernel.shape[1]):
            out += kernel[i, j] * padded[i : i + x.shape[0], j : j + x.shape[1]]

    return out


def gradient_magnitude(gray: np.ndarray) -> np.ndarray:
    gx = conv2d(gray, KX)
    gy = conv2d(gray, KY)
    return np.sqrt(gx * gx + gy * gy).astype(np.float32)


def local_variance(x: np.ndarray, radius: int = 2) -> np.ndarray:
    kernel = np.ones((2 * radius + 1, 2 * radius + 1), dtype=np.float32)
    kernel /= kernel.sum()
    mean = conv2d(x, kernel)
    mean2 = conv2d(x * x, kernel)
    return np.maximum(mean2 - mean * mean, 0).astype(np.float32)
