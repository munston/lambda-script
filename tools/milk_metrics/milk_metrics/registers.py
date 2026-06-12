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

    The register layer is where sexual visual safety is made explicit. A body
    cue, crop cue, colour cue, or garment cue has no final meaning in isolation.
    The register layer asks whether the visible evidence preserves a coherent
    adult subject, a stable relation to the camera/viewer, ordinary surface
    explanation, and non-repellent visual form.

    The four register scores therefore describe different safety functions:

    * milk: private charge stabilised by composure and surface auditability.
    * peach: bodily warmth integrated with whole-person presence.
    * coal: pressured inward feeling that remains self-possessed rather than
      fearful or helpless.
    * toy: idealised simplification that remains alive rather than plastic,
      uncanny, vacant, or object-like.

    The global score is not a beauty score and not an explicitness score. It is
    a coherence score for this framework's adult non-explicit visual-safety
    interpretation.
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

    Methodologically, this function is the first place where the code tries to
    behave like the theory rather than like a generic image-quality metric. It
    takes low-level primitives -- smoothness, garment boundary, relation context,
    public context, colour pressure, edge preservation -- and translates them
    into a cohesive measure set. That translation must remain commented because
    the formulas are provisional and because future improvements should change
    the right layer: proxies for measurable evidence, registers for interpretive
    synthesis, gates for hard safety correction.
    """
    gates = assess_gates(components)

    # Milk is the primary safety register. It is not just softness and it is not
    # just attractiveness. It asks whether a charged image remains privately
    # coherent, surface-auditable, and person-retaining. The current proxy mix
    # rewards calm surface, ordinary garment boundary, private/background support,
    # relation context, compression cleanliness, and edge preservation. It then
    # subtracts public-context and lower-central colour pressure. This mirrors the
    # doctrine: safe charge comes from composed visible presentation, not from
    # local inspection or crude signal concentration.
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
    # continuity and hip-line modelling. The key doctrine constraint is that
    # peach should not become detached body access. It is a warmth register, not
    # an anatomical reduction register. That is why red-signal pressure and weak
    # relation context later limit the score.
    peach_raw = (
        0.24 * components.get("midriff_smoothness", 0.0)
        + 0.16 * components.get("skin_smoothness", 0.0)
        + 0.16 * components.get("garment_threshold_structure", 0.0)
        + 0.16 * components.get("garment_colour_structure", 0.0)
        + 0.12 * components.get("full_body_context", 0.0)
        + 0.08 * components.get("edge_preservation", 0.0)
        - 0.16 * components.get("red_signal_penalty", components.get("explicit_surface_penalty", 0.0))
    )

    # Coal is the hardest register to approximate with simple pixels. Coal is an
    # affective and relational register: guarded disclosure, bashful resolve,
    # contained embarrassment, inward pressure, and self-possession. It should
    # never be inferred from fear, distress, helplessness, or loss of agency. The
    # current score only uses weak supports: relation context, private/background
    # softness, guarded colour/lighting proxies, edge preservation, and threshold
    # structure. Reports should mark coal as requiring human review whenever the
    # expression or posture is central.
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
    # processing distortion. The doctrine is stronger than the formula: positive
    # toy means alive idealised form; failed toy means plastic, vacant, uncanny,
    # malformed, or passive. Future work should add eye liveliness, limb
    # continuity, face coherence, and stylisation consistency.
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
    # image had positive support but was limited by a failure mode. This is a
    # critical sexual-visual-safety rule. The system should not erase positive
    # observations, but it also should not let local positives overwhelm loss of
    # personhood, context instability, processing distortion, or other gates.
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
        "milk": "private sexual visual safety inferred from smoothness, threshold structure, relation context, edge preservation, private-context support, and low penalty pressure",
        "peach": "bodily warmth inferred from midriff/surface continuity, garment structure, retained body context, and contour-adjacent proxies; limited whenever body warmth detaches from personhood",
        "coal": "guarded-feeling proxy inferred weakly from relation context, private-context proxies, and contained structure; expression, fear, embarrassment, and agency require human review",
        "toy": "idealisation proxy currently limited to technical coherence, artifact control, and shape-preserving restoration; future work should distinguish alive stylisation from plastic vacancy",
        "gate_policy": "gates are applied after positive support so the report can preserve evidence while limiting unsafe, unstable, fragmentary, or non-person-retaining interpretations",
        "scope": "adult, non-explicit, surface-auditable image classification; local body primitives are never sufficient for full register judgement without context",
    }
    return RegisterScores(milk, peach, coal, toy, global_score, gates, explanation)
