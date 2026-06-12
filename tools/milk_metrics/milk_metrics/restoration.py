from __future__ import annotations

from dataclasses import dataclass
import random

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from .metrics import MetricResult, compute_metric


@dataclass(frozen=True)
class RestorationParams:
    median_size: int
    smooth_radius: float
    blend: float
    sharpness: float
    contrast: float


@dataclass(frozen=True)
class RestorationRun:
    restored: np.ndarray
    result: MetricResult
    history: list[float]
    params: RestorationParams


def restore_with_params(arr: np.ndarray, params: RestorationParams) -> np.ndarray:
    """Apply conservative restoration operations only. No geometric warp."""
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), mode="RGB")
    if params.median_size >= 3:
        im = im.filter(ImageFilter.MedianFilter(size=int(params.median_size)))
    if params.smooth_radius > 0 and params.blend > 0:
        smoothed = im.filter(ImageFilter.GaussianBlur(radius=float(params.smooth_radius)))
        im = Image.blend(im, smoothed, float(params.blend))
    if params.sharpness != 1.0:
        im = ImageEnhance.Sharpness(im).enhance(float(params.sharpness))
    if params.contrast != 1.0:
        im = ImageEnhance.Contrast(im).enhance(float(params.contrast))
    return np.asarray(im).astype(np.float32) / 255.0


def search_conservative_restoration(arr: np.ndarray, *, steps: int = 360, seed: int = 41, max_distortion_penalty: float = 0.24) -> RestorationRun:
    rng = random.Random(seed)
    base_result = compute_metric(arr, arr)
    best_arr = arr.copy()
    best_result = base_result
    best_params = RestorationParams(1, 0.0, 0.0, 1.0, 1.0)
    history = [best_result.score]
    for _ in range(steps):
        params = RestorationParams(
            median_size=rng.choice([1, 1, 1, 3]),
            smooth_radius=rng.uniform(0.0, 0.55),
            blend=rng.uniform(0.0, 0.32),
            sharpness=rng.uniform(0.90, 1.08),
            contrast=rng.uniform(0.97, 1.04),
        )
        candidate = restore_with_params(arr, params)
        result = compute_metric(candidate, arr)
        if result.components["distortion_penalty"] < max_distortion_penalty and result.score > best_result.score:
            best_arr = candidate
            best_result = result
            best_params = params
        history.append(best_result.score)
    return RestorationRun(best_arr, best_result, history, best_params)
