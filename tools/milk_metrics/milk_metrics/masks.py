from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .color import hsv_like


@dataclass(frozen=True)
class DiagnosticMasks:
    surface: np.ndarray
    soft_background: np.ndarray
    accent_a: np.ndarray
    light_fabric: np.ndarray
    accent_b: np.ndarray
    accent_c: np.ndarray
    dark_detail: np.ndarray
    central_surface: np.ndarray
    upper_surface: np.ndarray
    depth_proxy: np.ndarray
    ground_proxy: np.ndarray
    chroma_proxy: np.ndarray


def build_masks(arr: np.ndarray) -> DiagnosticMasks:
    h, w, _ = arr.shape
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue, sat, val = hsv_like(arr)
    yy, xx = np.mgrid[0:h, 0:w]

    surface = (r > 0.27) & (g > 0.17) & (b > 0.12) & (r > b + 0.035) & (sat > 0.045)
    soft_background = (val > 0.45) & (sat < 0.30)
    accent_a = ((hue < 0.04) | (hue > 0.92)) & (sat > 0.18) & (sat < 0.62) & (val > 0.38)
    light_fabric = (val > 0.68) & (sat < 0.20)
    accent_b = ((hue < 0.05) | (hue > 0.88)) & (sat > 0.25) & (val > 0.38)
    accent_c = (hue > 0.45) & (hue < 0.58) & (sat > 0.25) & (val > 0.30)
    dark_detail = (val < 0.30) & (sat > 0.05)

    central_surface = surface & (yy > h * 0.27) & (yy < h * 0.62) & (xx > w * 0.20) & (xx < w * 0.68)
    upper_surface = surface & (yy > h * 0.05) & (yy < h * 0.36) & (xx > w * 0.12) & (xx < w * 0.58)
    depth_proxy = (xx > w * 0.54) & (yy < h * 0.65) & (val > 0.18) & (sat < 0.38)
    ground_proxy = (xx > w * 0.50) & (yy > h * 0.18) & (val > 0.28) & (sat < 0.33)
    chroma_proxy = ((hue < 0.045) | (hue > 0.91) | ((hue > 0.78) & (hue < 0.92))) & (sat > 0.30) & (val > 0.18) & (val < 0.88)

    return DiagnosticMasks(surface, soft_background, accent_a, light_fabric, accent_b, accent_c, dark_detail, central_surface, upper_surface, depth_proxy, ground_proxy, chroma_proxy)
