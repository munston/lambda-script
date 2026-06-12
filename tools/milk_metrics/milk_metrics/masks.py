from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .color import hsv_like


@dataclass(frozen=True)
class DiagnosticMasks:
    skin: np.ndarray
    soft_background: np.ndarray
    pink_soft: np.ndarray
    white_fabric: np.ndarray
    neon_pink: np.ndarray
    cyan_top: np.ndarray
    dark_gloss: np.ndarray
    midriff_skin: np.ndarray
    face_proxy: np.ndarray
    street_depth: np.ndarray
    sidewalk: np.ndarray
    red_signal_proxy: np.ndarray


def build_masks(arr: np.ndarray) -> DiagnosticMasks:
    """Build rule-based masks from an RGB float image in [0, 1]."""
    h, w, _ = arr.shape
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue, sat, val = hsv_like(arr)
    yy, xx = np.mgrid[0:h, 0:w]

    skin = (
        (r > 0.27)
        & (g > 0.17)
        & (b > 0.12)
        & (r > b + 0.035)
        & (r >= g - 0.060)
        & (sat > 0.045)
        & ~((val > 0.88) & (sat < 0.10))
    )

    soft_background = (val > 0.45) & (sat < 0.30)
    pink_soft = ((hue < 0.04) | (hue > 0.92)) & (sat > 0.18) & (sat < 0.62) & (val > 0.38)
    white_fabric = (val > 0.68) & (sat < 0.20)
    neon_pink = ((hue < 0.05) | (hue > 0.88)) & (sat > 0.25) & (val > 0.38)
    cyan_top = (hue > 0.45) & (hue < 0.58) & (sat > 0.25) & (val > 0.30)
    dark_gloss = (val < 0.30) & (sat > 0.05)

    center_band = (yy > h * 0.27) & (yy < h * 0.62) & (xx > w * 0.20) & (xx < w * 0.68)
    midriff_skin = skin & center_band

    top_region = (yy > h * 0.05) & (yy < h * 0.36) & (xx > w * 0.12) & (xx < w * 0.58)
    face_proxy = skin & top_region

    street_depth = (xx > w * 0.54) & (yy < h * 0.65) & (val > 0.18) & (sat < 0.38)
    sidewalk = (xx > w * 0.50) & (yy > h * 0.18) & (val > 0.28) & (sat < 0.33)

    lower_center = (yy > h * 0.34) & (yy < h * 0.96) & (xx > w * 0.24) & (xx < w * 0.78)
    red_or_pink = ((hue < 0.045) | (hue > 0.91)) | ((hue > 0.78) & (hue < 0.92))
    red_signal_proxy = lower_center & red_or_pink & (sat > 0.30) & (val > 0.18) & (val < 0.88)

    return DiagnosticMasks(
        skin=skin,
        soft_background=soft_background,
        pink_soft=pink_soft,
        white_fabric=white_fabric,
        neon_pink=neon_pink,
        cyan_top=cyan_top,
        dark_gloss=dark_gloss,
        midriff_skin=midriff_skin,
        face_proxy=face_proxy,
        street_depth=street_depth,
        sidewalk=sidewalk,
        red_signal_proxy=red_signal_proxy,
    )
