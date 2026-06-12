from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .convolution import LAPLACIAN, conv2d, gradient_magnitude, local_variance
from .masks import build_masks


@dataclass(frozen=True)
class MetricResult:
    score: float
    components: dict[str, float]
    positive_map: np.ndarray
    penalty_map: np.ndarray


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def _block_score(gray: np.ndarray, mask: np.ndarray) -> float:
    vals: list[float] = []
    for x in range(8, gray.shape[1], 8):
        m = mask[:, x - 1] & mask[:, x]
        if m.any():
            vals.append(float(np.mean(np.abs(gray[:, x][m] - gray[:, x - 1][m]))))
    for y in range(8, gray.shape[0], 8):
        m = mask[y - 1, :] & mask[y, :]
        if m.any():
            vals.append(float(np.mean(np.abs(gray[y, :][m] - gray[y - 1, :][m]))))
    return float(np.mean(vals)) if vals else 0.0


def compute_metric(arr: np.ndarray, ref: np.ndarray | None = None) -> MetricResult:
    """Compute the current provisional image diagnostic metric."""
    ref = arr if ref is None else ref
    gray = arr.mean(axis=2)
    ref_gray = ref.mean(axis=2)
    masks = build_masks(arr)
    surface = masks.surface.copy()
    central = masks.central_surface.copy()
    if surface.sum() < 200:
        surface = np.ones_like(gray, dtype=bool)
    if central.sum() < 100:
        central = surface

    grad = gradient_magnitude(gray)
    ref_grad = gradient_magnitude(ref_gray)
    var = local_variance(gray, 2)
    block = _block_score(gray, surface)
    ref_block = _block_score(ref_gray, surface)

    surface_smoothness = 1.0 - _clip01(float(np.mean(var[surface])) / 0.018)
    central_smoothness = 1.0 - _clip01(float(np.mean(var[central])) / 0.012)
    compression_cleanliness = 1.0 - _clip01(block / 0.022)
    deblock_gain = float(np.clip((ref_block - block) / max(ref_block, 1e-6), -1.0, 1.0))
    background_softness = _clip01(float(np.mean(masks.soft_background)))
    accent_private_energy = _clip01(float(np.mean(masks.accent_b)) * 4.0 + float(np.mean(masks.accent_c)) * 2.0)
    colour_structure = _clip01(float(np.mean(masks.accent_c)) * 3.0 + float(np.mean(masks.dark_detail)) * 1.4)

    surface_edge = np.abs(conv2d(surface.astype(np.float32), LAPLACIAN))
    boundary_band = surface_edge > 0.01
    boundary_structure = _clip01(float(np.mean(grad[boundary_band])) / 0.18) if boundary_band.any() else 0.0
    upper_context_proxy = _clip01(float(masks.upper_surface.sum()) / max(1.0, float(surface.sum())) * 3.2)
    full_frame_context = 1.0
    environment_penalty = _clip01(float(np.mean(masks.depth_proxy)) * 2.0 + float(np.mean(masks.ground_proxy)) * 1.5)
    chroma_penalty = _clip01(float(np.mean(masks.chroma_proxy)) / 0.025)

    ref_edge_region = ref_grad > np.percentile(ref_grad, 80)
    edge_preservation = 1.0 - _clip01(float(np.mean(np.abs(grad[ref_edge_region] - ref_grad[ref_edge_region]))) / 0.10)
    pixel_change = float(np.mean(np.abs(arr - ref)))
    distortion_penalty = _clip01(pixel_change / 0.050)
    edge_loss = _clip01((float(np.mean(ref_grad[surface])) - float(np.mean(grad[surface]))) / max(float(np.mean(ref_grad[surface])), 1e-6))

    score = (
        0.14 * surface_smoothness
        + 0.16 * central_smoothness
        + 0.09 * compression_cleanliness
        + 0.08 * max(0.0, deblock_gain)
        + 0.08 * background_softness
        + 0.11 * accent_private_energy
        + 0.10 * colour_structure
        + 0.10 * boundary_structure
        + 0.11 * upper_context_proxy
        + 0.08 * full_frame_context
        + 0.09 * edge_preservation
        - 0.16 * environment_penalty
        - 0.18 * chroma_penalty
        - 0.14 * distortion_penalty
        - 0.06 * edge_loss
    )

    positive_map = (
        0.28 * (1.0 - np.clip(var / 0.018, 0, 1)) * surface.astype(np.float32)
        + 0.24 * (1.0 - np.clip(var / 0.012, 0, 1)) * central.astype(np.float32)
        + 0.13 * masks.accent_b.astype(np.float32)
        + 0.13 * masks.accent_c.astype(np.float32)
        + 0.10 * masks.dark_detail.astype(np.float32)
        + 0.12 * (np.clip(grad / 0.18, 0, 1) * boundary_band.astype(np.float32))
    )
    penalty_map = 0.65 * masks.depth_proxy.astype(np.float32) + 0.35 * masks.ground_proxy.astype(np.float32) + 1.00 * masks.chroma_proxy.astype(np.float32)

    components = {
        "surface_smoothness": surface_smoothness,
        "central_smoothness": central_smoothness,
        "compression_cleanliness": compression_cleanliness,
        "deblock_gain": deblock_gain,
        "background_softness": background_softness,
        "accent_private_energy": accent_private_energy,
        "colour_structure": colour_structure,
        "boundary_structure": boundary_structure,
        "upper_context_proxy": upper_context_proxy,
        "full_frame_context": full_frame_context,
        "environment_penalty": environment_penalty,
        "chroma_penalty": chroma_penalty,
        "edge_preservation": edge_preservation,
        "distortion_penalty": distortion_penalty,
        "edge_loss": edge_loss,
        "raw_score": float(score),
    }
    return MetricResult(float(score), components, positive_map.astype(np.float32), penalty_map.astype(np.float32))
