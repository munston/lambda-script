#!/usr/bin/env python3
"""
Dependency-free scoring helper for the milk/coal/peach/toy visual-safety registers.

Input is JSON from a file path argument or stdin. The expected shape is:

{
  "features": {
    "self_possession": 0.9,
    "consent_signal": 1.0,
    "surface_auditability": 0.8,
    "whole_person_presence": 0.9,
    "private_enclosure": 0.7,
    "garment_led_threshold": 0.6,
    "guarded_feeling": 0.4,
    "bashful_pressure": 0.3,
    "hipline_warmth": 0.5,
    "idealized_simplification": 0.2,
    "plastic_vacancy": 0.0,
    "coercive_or_crude_read": 0.0
  }
}

All feature values are clamped to [0, 1]. Output is JSON containing register
scores, aggregate score, and diagnostic notes.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Tuple


FeatureMap = Mapping[str, float]


@dataclass(frozen=True)
class RegisterSpec:
    positive: Tuple[Tuple[str, float], ...]
    negative: Tuple[Tuple[str, float], ...]


REGISTER_SPECS: Dict[str, RegisterSpec] = {
    "milk": RegisterSpec(
        positive=(
            ("self_possession", 0.20),
            ("consent_signal", 0.20),
            ("surface_auditability", 0.18),
            ("whole_person_presence", 0.18),
            ("private_enclosure", 0.14),
            ("garment_led_threshold", 0.10),
        ),
        negative=(
            ("coercive_or_crude_read", 0.45),
            ("plastic_vacancy", 0.20),
        ),
    ),
    "coal": RegisterSpec(
        positive=(
            ("self_possession", 0.18),
            ("guarded_feeling", 0.22),
            ("bashful_pressure", 0.20),
            ("whole_person_presence", 0.16),
            ("surface_auditability", 0.14),
            ("private_enclosure", 0.10),
        ),
        negative=(
            ("coercive_or_crude_read", 0.45),
            ("plastic_vacancy", 0.25),
        ),
    ),
    "peach": RegisterSpec(
        positive=(
            ("self_possession", 0.16),
            ("whole_person_presence", 0.16),
            ("hipline_warmth", 0.24),
            ("garment_led_threshold", 0.16),
            ("surface_auditability", 0.14),
            ("consent_signal", 0.14),
        ),
        negative=(
            ("coercive_or_crude_read", 0.40),
            ("plastic_vacancy", 0.20),
        ),
    ),
    "toy": RegisterSpec(
        positive=(
            ("idealized_simplification", 0.24),
            ("self_possession", 0.20),
            ("whole_person_presence", 0.20),
            ("surface_auditability", 0.16),
            ("consent_signal", 0.12),
            ("private_enclosure", 0.08),
        ),
        negative=(
            ("plastic_vacancy", 0.45),
            ("coercive_or_crude_read", 0.30),
        ),
    ),
}


REQUIRED_CORE = (
    "self_possession",
    "consent_signal",
    "surface_auditability",
    "whole_person_presence",
)


def clamp01(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def feature(features: FeatureMap, name: str) -> float:
    return clamp01(features.get(name, 0.0))


def weighted_sum(features: FeatureMap, items: Iterable[Tuple[str, float]]) -> float:
    return sum(feature(features, name) * weight for name, weight in items)


def score_register(features: FeatureMap, spec: RegisterSpec) -> float:
    raw = weighted_sum(features, spec.positive) - weighted_sum(features, spec.negative)
    return round(max(0.0, min(1.0, raw)), 4)


def diagnose(features: FeatureMap, scores: Mapping[str, float]) -> List[str]:
    notes: List[str] = []
    for name in REQUIRED_CORE:
        if feature(features, name) < 0.5:
            notes.append(f"core weakness: {name}")
    if feature(features, "coercive_or_crude_read") > 0.2:
        notes.append("hard failure pressure: coercive_or_crude_read")
    if feature(features, "plastic_vacancy") > 0.35:
        notes.append("toy/cartoonisation risk: plastic_vacancy")
    strongest = max(scores, key=lambda k: scores[k]) if scores else None
    if strongest:
        notes.append(f"strongest register: {strongest}")
    return notes


def score_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    raw_features = payload.get("features", {})
    if not isinstance(raw_features, Mapping):
        raise ValueError("payload.features must be an object")
    features = {str(k): clamp01(v) for k, v in raw_features.items()}
    scores = {name: score_register(features, spec) for name, spec in REGISTER_SPECS.items()}
    aggregate = round(sum(scores.values()) / len(scores), 4)
    return {
        "scores": scores,
        "aggregate": aggregate,
        "diagnostics": diagnose(features, scores),
    }


def load_payload(argv: List[str]) -> Mapping[str, Any]:
    if len(argv) > 1:
        raise SystemExit("usage: milk_metric.py [payload.json]")
    if argv:
        with open(argv[0], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def main(argv: List[str]) -> int:
    try:
        payload = load_payload(argv)
        print(json.dumps(score_payload(payload), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
