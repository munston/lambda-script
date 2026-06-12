from __future__ import annotations

from dataclasses import dataclass

from .gates import GateLevel, GateReport, assess_gates


@dataclass(frozen=True)
class RegisterScores:
    """High-level register scores inferred from low-level metric components.

    These scores are not direct measurements. They are structured summaries of
    proxy evidence. The comments in this module are intentionally verbose
    because this is where the project distinguishes measurable image features
    from interpretive framework terms.
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

    The formulae here are deliberately simple and inspectable. The goal is not
    to make a convincing black box. The goal is to encode the current research
    claim: each register is a different composition of visible support, and
    gates correct the result when local proxies contradict the global directive.
    """
    gates = assess_gates(components)

    # Milk is the primary safety register. It needs surface continuity, some
    # relation context, ordinary garment/context structure, and low penalties.
    milk_raw = (
        0.18 * components.get("skin_smoothness", 0.0)
        + 0.18 * components.get("midriff_smoothness", 0.0)
        + 0.14 * components.get("background_softness", components.get("private_bg_softness", 0.0))
        + 0.14 * components.get("garment_threshold_structure", 0.0)
        + 0.14 * components.get("face_context_proxy", 0.0)
        + 0.10 * components.get("edge_preservation", 0.0)
        + 0.08 * components.get("compression_cleanliness", 0.0)
        + 0.04 * components.get("full_body_context", 0.0)
        - 0.14 * components.get("public_context_penalty", 0.0)
        - 0.14 * components.get("red_signal_penalty", components.get("explicit_surface_penalty", 0.0))
    )

    # Peach is bodily warmth integrated with personhood. The current proxy is
    # still weak: it uses midriff smoothness, garment threshold, colour/contour
    # structure, and whole-body context. Later work should add explicit contour
    # continuity and hip-line modelling.
    peach_raw = (
        0.24 * components.get("midriff_smoothness", 0.0)
        + 0.16 * components.get("skin_smoothness", 0.0)
        + 0.16 * components.get("garment_threshold_structure", 0.0)
        + 0.16 * components.get("garment_colour_structure", 0.0)
        + 0.12 * components.get("full_body_context", 0.0)
        + 0.08 * components.get("edge_preservation", 0.0)
        - 0.16 * components.get("red_signal_penalty", components.get("explicit_surface_penalty", 0.0))
    )

    # Coal is the hardest register to approximate with simple pixels. This
    # provisional score treats relation context, private/background softness,
    # guarded low-light/colour structure, and garment threshold as weak support.
    # It should be reviewed by hand whenever expression matters.
    coal_raw = (
        0.22 * components.get("face_context_proxy", 0.0)
        + 0.16 * components.get("background_softness", components.get("private_bg_softness", 0.0))
        + 0.16 * components.get("neon_private_energy", 0.0)
        + 0.12 * components.get("garment_threshold_structure", 0.0)
        + 0.12 * components.get("edge_preservation", 0.0)
        - 0.18 * components.get("public_context_penalty", 0.0)
        - 0.10 * components.get("red_signal_penalty", components.get("explicit_surface_penalty", 0.0))
    )

    # Toy/cartoonisation is only partly represented in the current code. Until
    # shape-coherence and stylisation-specific features exist, this score is a
    # technical coherence proxy: clear structure, low artifacting, and low
    # processing distortion.
    toy_raw = (
        0.24 * components.get("edge_preservation", 0.0)
        + 0.18 * components.get("compression_cleanliness", 0.0)
        + 0.18 * components.get("garment_colour_structure", 0.0)
        + 0.14 * components.get("background_softness", components.get("private_bg_softness", 0.0))
        + 0.14 * components.get("full_body_context", 0.0)
        - 0.20 * components.get("distortion_penalty", 0.0)
        - 0.12 * components.get("edge_loss", 0.0)
    )

    milk = _clamp(milk_raw)
    peach = _clamp(peach_raw)
    coal = _clamp(coal_raw)
    toy = _clamp(toy_raw)

    # Apply gate correction after positive inference. This preserves the
    # evidence while making the override visible: the report can show that an
    # image had positive support but was limited by a failure mode.
    if gates.hard_active:
        milk *= 0.35
        peach *= 0.45
        coal *= 0.35
        toy *= 0.50
    elif gates.soft_active:
        for gate in gates.gates:
            if gate.level != GateLevel.SOFT:
                continue
            if gate.name == "public_context_pressure":
                milk *= 0.82
                coal *= 0.78
            elif gate.name == "weak_relation_context":
                milk *= 0.78
                coal *= 0.70
                peach *= 0.90
            elif gate.name == "red_signal_pressure":
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
        "milk": "private safety inferred from smoothness, threshold structure, relation context, edge preservation, and low penalty pressure",
        "peach": "bodily warmth inferred from midriff/surface continuity, garment structure, and retained body context",
        "coal": "guarded-feeling proxy inferred weakly from relation context, private-context proxies, and contained structure; needs human review for expression",
        "toy": "idealisation proxy currently limited to technical coherence, artifact control, and shape-preserving restoration",
        "gate_policy": "gates are applied after positive support so the report can preserve evidence while limiting unsafe or unstable interpretations",
    }
    return RegisterScores(milk, peach, coal, toy, global_score, gates, explanation)
