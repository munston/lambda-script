from __future__ import annotations

from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def to_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), mode="RGB")


def norm01(x: np.ndarray) -> np.ndarray:
    return (x - x.min()) / (x.max() - x.min() + 1e-6)


def save_gray_mask(path: Path, mask: np.ndarray) -> None:
    n = norm01(mask)
    Image.fromarray((n * 255).astype(np.uint8), mode="L").save(path)


def save_response_overlay(path: Path, image: Image.Image, positive_map: np.ndarray, penalty_map: np.ndarray) -> None:
    h, w = positive_map.shape
    pos = norm01(positive_map)
    pen = norm01(penalty_map)

    pos_layer = np.zeros((h, w, 4), dtype=np.uint8)
    pos_layer[..., 0] = 0
    pos_layer[..., 1] = 210
    pos_layer[..., 2] = 255
    pos_layer[..., 3] = np.clip(pos * 125, 0, 125).astype(np.uint8)

    pen_layer = np.zeros((h, w, 4), dtype=np.uint8)
    pen_layer[..., 0] = 255
    pen_layer[..., 1] = 50
    pen_layer[..., 2] = 40
    pen_layer[..., 3] = np.clip(pen * 140, 0, 140).astype(np.uint8)

    overlay = Image.alpha_composite(image.convert("RGBA"), Image.fromarray(pos_layer, mode="RGBA"))
    overlay = Image.alpha_composite(overlay, Image.fromarray(pen_layer, mode="RGBA"))
    overlay.save(path)


def save_before_after(path: Path, before: Image.Image, after: Image.Image) -> None:
    w, h = before.size
    comparison = Image.new("RGB", (w * 2, h), "white")
    comparison.paste(before.convert("RGB"), (0, 0))
    comparison.paste(after.convert("RGB"), (w, 0))
    comparison.save(path)


def save_change_map(path: Path, before: np.ndarray, after: np.ndarray) -> None:
    diff = np.mean(np.abs(after - before), axis=2)
    save_gray_mask(path, diff)


def save_components_plot(path: Path, components: dict[str, float]) -> None:
    names = [
        "midriff_smoothness",
        "skin_smoothness",
        "neon_private_energy",
        "garment_colour_structure",
        "garment_threshold_structure",
        "face_context_proxy",
        "full_body_context",
        "public_context_penalty",
        "red_signal_penalty",
        "distortion_penalty",
    ]
    names = [name for name in names if name in components]
    values = [components[name] for name in names]
    plt.figure(figsize=(9.5, 4.8))
    plt.bar(range(len(values)), values)
    plt.xticks(range(len(values)), names, rotation=50, ha="right")
    plt.ylim(0, 1.05)
    plt.ylabel("component value")
    plt.title("Milk-oriented diagnostic components")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def save_trace(path: Path, history: list[float]) -> None:
    plt.figure(figsize=(7.0, 3.8))
    plt.plot(history)
    plt.xlabel("stochastic step")
    plt.ylabel("best diagnostic score")
    plt.title("Constrained restoration score trace")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def save_report(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
