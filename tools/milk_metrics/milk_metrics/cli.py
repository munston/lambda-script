from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from .metrics import compute_metric
from .proxies import proxy_dictionary
from .registers import infer_registers
from .render import (
    save_before_after,
    save_change_map,
    save_components_plot,
    save_gray_mask,
    save_report,
    save_response_overlay,
    save_trace,
    to_image,
)
from .restoration import search_conservative_restoration


def read_image(path: Path) -> tuple[Image.Image, np.ndarray]:
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img).astype(np.float32) / 255.0
    return img, arr


def report_payload(mode: str, score: float, components: dict[str, float]) -> dict:
    registers = infer_registers(components)
    return {
        "mode": mode,
        "score": score,
        "components": components,
        "registers": registers.as_dict(),
        "proxy_dictionary": proxy_dictionary(),
    }


def run_analyze(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    img, arr = read_image(Path(args.image))
    result = compute_metric(arr, arr)
    img.save(out / "original.png")
    save_gray_mask(out / "positive_response_mask.png", result.positive_map)
    save_gray_mask(out / "penalty_mask.png", result.penalty_map)
    save_response_overlay(out / "response_overlay.png", img, result.positive_map, result.penalty_map)
    save_components_plot(out / "components.png", result.components)
    save_report(out / "report.json", report_payload("analyze", result.score, result.components))
    print(f"score: {result.score:.6f}")
    print(out)


def run_restore(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    img, arr = read_image(Path(args.image))
    base = compute_metric(arr, arr)
    run = search_conservative_restoration(arr, steps=args.steps, seed=args.seed)
    restored_img = to_image(run.restored)
    img.save(out / "original.png")
    restored_img.save(out / "restored.png")
    save_before_after(out / "before_after.png", img, restored_img)
    save_change_map(out / "change_map.png", arr, run.restored)
    save_gray_mask(out / "positive_response_mask.png", run.result.positive_map)
    save_gray_mask(out / "penalty_mask.png", run.result.penalty_map)
    save_response_overlay(out / "response_overlay.png", restored_img, run.result.positive_map, run.result.penalty_map)
    save_components_plot(out / "components.png", run.result.components)
    save_trace(out / "score_trace.png", run.history)

    payload = report_payload("restore", run.result.score, run.result.components)
    payload.update(
        {
            "initial_score": base.score,
            "final_score": run.result.score,
            "increase": run.result.score - base.score,
            "best_params": run.params.__dict__,
            "method_note": "conservative restoration only; no geometric warp; score corrected by distortion and edge-loss penalties",
        }
    )
    save_report(out / "report.json", payload)
    print(f"initial_score: {base.score:.6f}")
    print(f"final_score:   {run.result.score:.6f}")
    print(f"increase:      {run.result.score - base.score:.6f}")
    print(out)


def run_penalty_mask(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    img, arr = read_image(Path(args.image))
    result = compute_metric(arr, arr)
    save_gray_mask(out / "penalty_mask.png", result.penalty_map)
    save_response_overlay(out / "penalty_overlay.png", img, np.zeros_like(result.penalty_map), result.penalty_map)
    payload = report_payload("penalty-mask", result.score, result.components)
    payload.update(
        {
            "chroma_penalty": result.components.get("chroma_penalty"),
            "environment_penalty": result.components.get("environment_penalty"),
        }
    )
    save_report(out / "penalty_report.json", payload)
    print(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="milk-metrics")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="score a raw image and write masks/reports")
    analyze.add_argument("image")
    analyze.add_argument("--out", default="runs/analyze")
    analyze.set_defaults(func=run_analyze)

    restore = sub.add_parser("restore", help="run conservative restoration search")
    restore.add_argument("image")
    restore.add_argument("--out", default="runs/restore")
    restore.add_argument("--steps", type=int, default=360)
    restore.add_argument("--seed", type=int, default=41)
    restore.set_defaults(func=run_restore)

    penalty = sub.add_parser("penalty-mask", help="write penalty mask and overlay only")
    penalty.add_argument("image")
    penalty.add_argument("--out", default="runs/penalty")
    penalty.set_defaults(func=run_penalty_mask)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
