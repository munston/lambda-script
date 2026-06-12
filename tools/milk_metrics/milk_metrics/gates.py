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
    rule-based, so it can detect only proxy signals such as crop weakness,
    public-context pressure, surface instability, or processing distortion. It
    cannot truly detect expression, consent, or personhood. Those deeper gates
    remain annotation targets until later models are added.
    """
    gates: list[GateAssessment] = []

    public_context = components.get("public_context_penalty", 0.0)
    if public_context >= 0.55:
        gates.append(GateAssessment("public_context_pressure", GateLevel.SOFT, "strong public-context proxy signal"))
    elif public_context >= 0.30:
        gates.append(GateAssessment("public_context_pressure", GateLevel.SOFT, "moderate public-context proxy signal"))
    else:
        gates.append(GateAssessment("public_context_pressure", GateLevel.NONE, "no substantial public-context proxy"))

    face_context = components.get("face_context_proxy", 0.0)
    if face_context <= 0.08:
        gates.append(GateAssessment("weak_relation_context", GateLevel.SOFT, "little upper-body or face-context proxy"))
    else:
        gates.append(GateAssessment("weak_relation_context", GateLevel.NONE, "some relation-context proxy present"))

    red_signal = components.get("red_signal_penalty", components.get("explicit_surface_penalty", 0.0))
    if red_signal >= 0.70:
        gates.append(GateAssessment("red_signal_pressure", GateLevel.SOFT, "high lower-central colour penalty proxy"))
    elif red_signal >= 0.35:
        gates.append(GateAssessment("red_signal_pressure", GateLevel.SOFT, "moderate lower-central colour penalty proxy"))
    else:
        gates.append(GateAssessment("red_signal_pressure", GateLevel.NONE, "low lower-central colour penalty proxy"))

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
