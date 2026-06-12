from __future__ import annotations

from dataclasses import dataclass

from .gates import GateLevel, GateReport, assess_gates


@dataclass(frozen=True)
class RegisterScores:
    """High-level register scores inferred from low-level metric components.

    These scores are structured summaries of proxy evidence. They are not direct
    measurements. The role of this layer is to keep the register vocabulary above
    the pixel features: surface, boundary, environment, and restoration metrics
    can support a register only after gate correction.
    """

    milk: float
    peach: float
    coal: float
    toy: float
    global_score: float
    gates: GateReport
    explanation: dict[str, str]

    def as_dict(self) -> dict:
        return {
            "milk": self.milk,
            "peach": self.peach,
            "coal": self.coal,
            "toy": self.toy,
            "global_score": self.global_score,
            "gates": self.gates.as_dict(),
            "explanation": self.explanation,
        }


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def infer_registers(components: dict[str, float]) -> RegisterScores:
    """Infer milk, peach, coal, and toy scores from component values.

    The formulas are deliberately simple and inspectable. They encode the current
    working model: each register is a different composition of visible support,
    and gates correct the result when local proxies contradict the broader image
    relation.
    """
    gates = assess_gates(components)

    milk_raw = (
        0.18 * components.get("surface_smoothness", 0.0)
        + 0.18 * components.get("central_smoothness", 0.0)
        + 0.14 * components.get("background_softness", 0.0)
        + 0.14 * components.get("boundary_structure", 0.0)
        + 0.14 * components.get("upper_context_proxy", 0.0)
        + 0.10 * components.get("edge_preservation", 0.0)
        + 0.08 * components.get("compression_cleanliness", 0.0)
        + 0.04 * components.get("full_frame_context", 0.0)
        - 0.14 * components.get("environment_penalty", 0.0)
        - 0.14 * components.get("chroma_penalty", 0.0)
    )

    peach_raw = (
        0.24 * components.get("central_smoothness", 0.0)
        + 0.16 * components.get("surface_smoothness", 0.0)
        + 0.16 * components.get("boundary_structure", 0.0)
        + 0.16 * components.get("colour_structure", 0.0)
        + 0.12 * components.get("full_frame_context", 0.0)
        + 0.08 * components.get("edge_preservation", 0.0)
        - 0.16 * components.get("chroma_penalty", 0.0)
    )

    coal_raw = (
        0.22 * components.get("upper_context_proxy", 0.0)
        + 0.16 * components.get("background_softness", 0.0)
        + 0.16 * components.get("accent_private_energy", 0.0)
        + 0.12 * components.get("boundary_structure", 0.0)
        + 0.12 * components.get("edge_preservation", 0.0)
        - 0.18 * components.get("environment_penalty", 0.0)
        - 0.10 * components.get("chroma_penalty", 0.0)
    )

    toy_raw = (
        0.24 * components.get("edge_preservation", 0.0)
        + 0.18 * components.get("compression_cleanliness", 0.0)
        + 0.18 * components.get("colour_structure", 0.0)
        + 0.14 * components.get("background_softness", 0.0)
        + 0.14 * components.get("full_frame_context", 0.0)
        - 0.20 * components.get("distortion_penalty", 0.0)
        - 0.12 * components.get("edge_loss", 0.0)
    )

    milk = _clamp(milk_raw)
    peach = _clamp(peach_raw)
    coal = _clamp(coal_raw)
    toy = _clamp(toy_raw)

    if gates.hard_active:
        milk *= 0.35
        peach *= 0.45
        coal *= 0.35
        toy *= 0.50
    elif gates.soft_active:
        for gate in gates.gates:
            if gate.level != GateLevel.SOFT:
                continue
            if gate.name == "environment_pressure":
                milk *= 0.82
                coal *= 0.78
            elif gate.name == "weak_relation_context":
                milk *= 0.78
                coal *= 0.70
                peach *= 0.90
            elif gate.name == "chroma_pressure":
                milk *= 0.84
                peach *= 0.82
            elif gate.name == "processing_distortion":
                toy *= 0.75
                milk *= 0.92
            elif gate.name == "edge_loss":
                toy *= 0.82
                milk *= 0.90

    global_score = _clamp(0.38 * milk + 0.24 * peach + 0.20 * coal + 0.18 * toy)
    explanation = {
        "milk": "private visual safety inferred from smoothness, boundary structure, context, edge preservation, and low penalty pressure",
        "peach": "body warmth inferred from central/surface continuity, boundary structure, colour structure, and retained frame context",
        "coal": "guarded-feeling proxy inferred weakly from upper context, private-context proxies, and contained structure; human review remains important",
        "toy": "idealisation proxy currently limited to technical coherence, artifact control, and shape-preserving restoration",
        "gate_policy": "gates are applied after positive support so local evidence can be preserved while unstable interpretations are limited",
    }
    return RegisterScores(milk, peach, coal, toy, global_score, gates, explanation)
