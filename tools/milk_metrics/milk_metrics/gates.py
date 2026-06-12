from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateLevel(str, Enum):
    """Severity level for an interpretive gate.

    Gates are deliberately separated from positive scoring. A register can have
    strong supporting evidence while still being limited by a gate. This matters
    because local image features, such as smooth surface or strong contour, can
    be attractive as primitives while the global image relation remains weak or
    unstable.

    In this visual-safety framework, gates protect the classifier from optimiser
    collapse. Without gates, the system would tend to reward whatever local
    feature increases a score: smoothness, contrast, colour, contour, or boundary
    strength. Gates force the classifier to ask whether those local features
    still belong to a coherent subject, a stable context, a non-repellent image,
    and an ordinary visible presentation.
    """

    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


@dataclass(frozen=True)
class GateAssessment:
    """A single gate decision with visible evidence attached.

    `level` says whether the gate is absent, limiting, or overriding.
    `evidence` should be a short human-readable note, because the project should
    never silently convert a moral or aesthetic judgement into an unexplained
    number.

    Gate evidence should remain visibly grounded. The current code can report
    proxy pressure such as environment, weak upper-region context, high chroma,
    or processing distortion. It should not pretend to know inner state, age, or
    affect from those proxies alone.
    """

    name: str
    level: GateLevel
    evidence: str


@dataclass(frozen=True)
class GateReport:
    """Collection of gate decisions for one image.

    The `hard_active` and `soft_active` helpers allow register inference to be
    corrected after ordinary scores are computed. This is the intended order:
    first compute low-level proxies, then infer registers, then apply gates.

    This order matters. Positive evidence should be preserved in the report even
    when a gate limits the final score. A crop may genuinely show useful surface
    smoothness while still lacking person-level context. A public setting may
    genuinely contain strong colour or garment cues while still weakening the
    private-register interpretation. The gate report records those limits
    without deleting the observation.
    """

    gates: tuple[GateAssessment, ...]

    @property
    def hard_active(self) -> bool:
        return any(g.level == GateLevel.HARD for g in self.gates)

    @property
    def soft_active(self) -> bool:
        return any(g.level == GateLevel.SOFT for g in self.gates)

    def as_dict(self) -> dict[str, dict[str, str]]:
        return {g.name: {"level": g.level.value, "evidence": g.evidence} for g in self.gates}


def assess_gates(components: dict[str, float]) -> GateReport:
    """Infer provisional gates from metric components.

    This is intentionally conservative and sparse. The current image pipeline is
    rule-based, so it can detect only proxy signals such as weak relation
    context, public/environment pressure, surface instability, or processing
    distortion. Deeper judgements remain annotation targets until later models
    are added.
    """
    gates: list[GateAssessment] = []

    environment = components.get("environment_penalty", 0.0)
    if environment >= 0.55:
        gates.append(GateAssessment("environment_pressure", GateLevel.SOFT, "strong environment/public-context proxy signal"))
    elif environment >= 0.30:
        gates.append(GateAssessment("environment_pressure", GateLevel.SOFT, "moderate environment/public-context proxy signal"))
    else:
        gates.append(GateAssessment("environment_pressure", GateLevel.NONE, "no substantial environment proxy pressure"))

    relation = components.get("upper_context_proxy", 0.0)
    if relation <= 0.08:
        gates.append(GateAssessment("weak_relation_context", GateLevel.SOFT, "little upper-region relation proxy"))
    else:
        gates.append(GateAssessment("weak_relation_context", GateLevel.NONE, "some upper-region relation proxy present"))

    chroma = components.get("chroma_penalty", 0.0)
    if chroma >= 0.70:
        gates.append(GateAssessment("chroma_pressure", GateLevel.SOFT, "high chroma penalty proxy"))
    elif chroma >= 0.35:
        gates.append(GateAssessment("chroma_pressure", GateLevel.SOFT, "moderate chroma penalty proxy"))
    else:
        gates.append(GateAssessment("chroma_pressure", GateLevel.NONE, "low chroma penalty proxy"))

    distortion = components.get("distortion_penalty", 0.0)
    if distortion >= 0.50:
        gates.append(GateAssessment("processing_distortion", GateLevel.HARD, "restoration changed the source too much"))
    elif distortion >= 0.24:
        gates.append(GateAssessment("processing_distortion", GateLevel.SOFT, "restoration change is near the allowed limit"))
    else:
        gates.append(GateAssessment("processing_distortion", GateLevel.NONE, "processing change within conservative limit"))

    edge_loss = components.get("edge_loss", 0.0)
    if edge_loss >= 0.45:
        gates.append(GateAssessment("edge_loss", GateLevel.SOFT, "smoothing removed too much structure"))
    else:
        gates.append(GateAssessment("edge_loss", GateLevel.NONE, "edge preservation acceptable"))

    return GateReport(tuple(gates))
