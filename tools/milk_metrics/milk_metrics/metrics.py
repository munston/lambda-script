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


def _jpeg_block_score(gray: np.ndarray, mask: np.ndarray) -> float:
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
    """Compute the current provisional milk-oriented diagnostic metric."""
    ref = arr if ref is None else ref
    gray = arr.mean(axis=2)
    ref_gray = ref.mean(axis=2)
    masks = build_masks(arr)
    skin = masks.skin.copy()
    midriff = masks.midriff_skin.copy()
    if skin.sum() < 200:
        skin = np.ones_like(gray, dtype=bool)
    if midriff.sum() < 100:
        midriff = skin

    grad = gradient_magnitude(gray)
    ref_grad = gradient_magnitude(ref_gray)
    var = local_variance(gray, 2)
    block = _jpeg_block_score(gray, skin)
    ref_block = _jpeg_block_score(ref_gray, skin)

    skin_smoothness = 1.0 - _clip01(float(np.mean(var[skin])) / 0.018)
    midriff_smoothness = 1.0 - _clip01(float(np.mean(var[midriff])) / 0.012)
    compression_cleanliness = 1.0 - _clip01(block / 0.022)
    deblock_gain = float(np.clip((ref_block - block) / max(ref_block, 1e-6), -1.0, 1.0))
    background_softness = _clip01(float(np.mean(masks.soft_background)))
    neon_private_energy = _clip01(float(np.mean(masks.neon_pink)) * 4.0 + float(np.mean(masks.cyan_top)) * 2.0)
    garment_colour_structure = _clip01(float(np.mean(masks.cyan_top)) * 3.0 + float(np.mean(masks.dark_gloss)) * 1.4)

    skin_edge = np.abs(conv2d(skin.astype(np.float32), LAPLACIAN))
    boundary_band = skin_edge > 0.01
    garment_threshold_structure = _clip01(float(np.mean(grad[boundary_band])) / 0.18) if boundary_band.any() else 0.0
    face_context_proxy = _clip01(float(masks.face_proxy.sum()) / max(1.0, float(skin.sum())) * 3.2)
    full_body_context = 1.0
    public_context_penalty = _clip01(float(np.mean(masks.street_depth)) * 2.0 + float(np.mean(masks.sidewalk)) * 1.5)
    red_signal_penalty = _clip01(float(np.mean(masks.red_signal_proxy)) / 0.025)

    ref_edge_region = ref_grad > np.percentile(ref_grad, 80)
    edge_preservation = 1.0 - _clip01(float(np.mean(np.abs(grad[ref_edge_region] - ref_grad[ref_edge_region]))) / 0.10)
    pixel_change = float(np.mean(np.abs(arr - ref)))
    distortion_penalty = _clip01(pixel_change / 0.050)
    edge_loss = _clip01((float(np.mean(ref_grad[skin])) - float(np.mean(grad[skin]))) / max(float(np.mean(ref_grad[skin])), 1e-6))

    score = (
        0.14 * skin_smoothness
        + 0.16 * midriff_smoothness
        + 0.09 * compression_cleanliness
        + 0.08 * max(0.0, deblock_gain)
        + 0.08 * background_softness
        + 0.11 * neon_private_energy
        + 0.10 * garment_colour_structure
        + 0.10 * garment_threshold_structure
        + 0.11 * face_context_proxy
        + 0.08 * full_body_context
        + 0.09 * edge_preservation
        - 0.16 * public_context_penalty
        - 0.18 * red_signal_penalty
        - 0.14 * distortion_penalty
        - 0.06 * edge_loss
    )

    positive_map = (
        0.28 * (1.0 - np.clip(var / 0.018, 0, 1)) * skin.astype(np.float32)
        + 0.24 * (1.0 - np.clip(var / 0.012, 0, 1)) * midriff.astype(np.float32)
        + 0.13 * masks.neon_pink.astype(np.float32)
        + 0.13 * masks.cyan_top.astype(np.float32)
        + 0.10 * masks.dark_gloss.astype(np.float32)
        + 0.12 * (np.clip(grad / 0.18, 0, 1) * boundary_band.astype(np.float32))
    )
    penalty_map = (
        0.65 * masks.street_depth.astype(np.float32)
        + 0.35 * masks.sidewalk.astype(np.float32)
        + 1.00 * masks.red_signal_proxy.astype(np.float32)
    )

    components = {
        "skin_smoothness": skin_smoothness,
        "midriff_smoothness": midriff_smoothness,
        "compression_cleanliness": compression_cleanliness,
        "deblock_gain": deblock_gain,
        "background_softness": background_softness,
        "neon_private_energy": neon_private_energy,
        "garment_colour_structure": garment_colour_structure,
        "garment_threshold_structure": garment_threshold_structure,
        "face_context_proxy": face_context_proxy,
        "full_body_context": full_body_context,
        "public_context_penalty": public_context_penalty,
        "red_signal_penalty": red_signal_penalty,
        "edge_preservation": edge_preservation,
        "distortion_penalty": distortion_penalty,
        "edge_loss": edge_loss,
        "raw_score": float(score),
    }
    return MetricResult(float(score), components, positive_map.astype(np.float32), penalty_map.astype(np.float32))
