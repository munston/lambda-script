from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image


def run(args: list[str], cwd: Path) -> None:
    proc = subprocess.run(args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(args))


def write_synthetic_image(path: Path) -> None:
    h, w = 96, 128
    y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]

    base = np.zeros((h, w, 3), dtype=np.float32)
    base[..., 0] = 0.72 + 0.12 * x
    base[..., 1] = 0.66 + 0.10 * y
    base[..., 2] = 0.70 + 0.08 * (1.0 - x)

    # Soft central surface with enough structure to exercise masks and components.
    cx, cy = 0.50, 0.52
    oval = (((x - cx) / 0.30) ** 2 + ((y - cy) / 0.34) ** 2) <= 1.0
    base[oval] = np.array([0.86, 0.74, 0.68], dtype=np.float32)

    # Dark detail band and a cooler corner region exercise positive/penalty maps.
    base[44:52, 36:94, :] *= np.array([0.72, 0.68, 0.74], dtype=np.float32)
    base[70:95, 0:30, :] = np.array([0.18, 0.21, 0.25], dtype=np.float32)

    # Mild deterministic texture prevents degenerate flat-image reports.
    texture = 0.015 * np.sin(2 * np.pi * (x * 7.0 + y * 3.0))
    base = np.clip(base + texture[..., None], 0.0, 1.0)

    Image.fromarray((base * 255.0).astype(np.uint8), mode="RGB").save(path)


def assert_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size <= 0:
        raise AssertionError(f"missing or empty output file: {path}")


def assert_report(path: Path, mode: str) -> None:
    assert_file(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("mode") != mode:
        raise AssertionError(f"unexpected report mode in {path}: {data.get('mode')!r}")
    if not isinstance(data.get("score"), (int, float)):
        raise AssertionError(f"missing numeric score in {path}")
    components = data.get("components")
    if not isinstance(components, dict) or "raw_score" not in components:
        raise AssertionError(f"missing components/raw_score in {path}")
    registers = data.get("registers")
    if not isinstance(registers, dict):
        raise AssertionError(f"missing registers in {path}")


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    with TemporaryDirectory(prefix="milk-metrics-smoke-") as tmp_raw:
        tmp = Path(tmp_raw)
        image = tmp / "synthetic.png"
        analyze_out = tmp / "analyze"
        penalty_out = tmp / "penalty"
        write_synthetic_image(image)

        run([sys.executable, "-m", "milk_metrics.cli", "analyze", str(image), "--out", str(analyze_out)], repo)
        for name in [
            "original.png",
            "positive_response_mask.png",
            "penalty_mask.png",
            "response_overlay.png",
            "components.png",
            "report.json",
        ]:
            assert_file(analyze_out / name)
        assert_report(analyze_out / "report.json", "analyze")

        run([sys.executable, "-m", "milk_metrics.cli", "penalty-mask", str(image), "--out", str(penalty_out)], repo)
        for name in [
            "penalty_mask.png",
            "penalty_overlay.png",
            "penalty_report.json",
        ]:
            assert_file(penalty_out / name)
        assert_report(penalty_out / "penalty_report.json", "penalty-mask")

    print("Milk metrics smoke test passed")


if __name__ == "__main__":
    main()
