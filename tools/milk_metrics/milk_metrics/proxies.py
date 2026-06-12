from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProxyNote:
    """Named explanation of a low-level proxy.

    This module is intentionally explanatory. The project needs a clear boundary
    between things the computer can measure directly and terms from the visual
    framework. A proxy note documents that boundary.

    The important methodological point is that proxies are not erotic meanings.
    They are measurable traces that may support or weaken a safety-relevant
    interpretation. For example, smooth surface continuity may support milk or
    peach, but only when personhood and context remain stable. The same smooth
    region in an anonymous crop cannot carry the full register by itself.

    This class therefore records three facts for each proxy: what it can support,
    what failure pressure it can indicate, and why the interpretation remains
    limited. Future classifiers should keep this discipline so that a numerical
    optimiser cannot silently convert a local body cue into a global sexual
    visual safety judgement.
    """

    name: str
    supports: tuple[str, ...]
    weakens: tuple[str, ...]
    explanation: str


DOCTRINE_NOTE = (
    "Sexual visual safety is judged as a relation between visible evidence and "
    "the retained person. The proxy layer measures surface, boundary, context, "
    "and restoration behaviour; it does not decide consent, agency, age stability, "
    "or affect by itself. Register inference and gate correction must remain above "
    "this layer."
)


def proxy_notes() -> tuple[ProxyNote, ...]:
    """Return the current proxy dictionary used by reports and future tests.

    These descriptions are duplicated here rather than hidden in prose docs so
    code-generated reports can include the same methodology. This also makes it
    easier to unit-test that each numerical field has an explicit interpretive
    role.

    The list below encodes the current understanding of the metric set as a
    sexual visual safety scaffold:

    * Some proxies support charged safety by preserving surface calm, garment
      legibility, private context, or subject relation.
    * Some proxies weaken safety by signalling public exposure, fragmentary crop
      pressure, colour pressure, processing distortion, or lost structure.
    * Every proxy is provisional. A human-readable report must explain how it was
      used and which gate limited it.
    """
    return (
        ProxyNote(
            name="skin_smoothness",
            supports=("milk", "peach"),
            weakens=("harsh_surface", "compression_noise"),
            explanation=(
                "Low local variance over skin-like regions. In the doctrine this supports soft surface continuity: "
                "a calm, non-abrasive surface that can help charged imagery feel visually safe. It must be balanced "
                "against edge preservation because blur, plastic smoothing, or wax-like skin harms toy/cartoonisation "
                "and can make the subject less alive."
            ),
        ),
        ProxyNote(
            name="midriff_smoothness",
            supports=("milk", "peach"),
            weakens=("hard_segmentation", "fitness_like_edge_dominance"),
            explanation=(
                "Low local variance in the central body band. It approximates smooth unstrained body surface rather "
                "than abdominal hardness or fitness-like segmentation. It is only a surface primitive: it can help "
                "peach warmth or milk softness when integrated with personhood, but a close crop alone cannot establish "
                "a complete safe adult register."
            ),
        ),
        ProxyNote(
            name="garment_threshold_structure",
            supports=("milk", "peach"),
            weakens=("featureless_flatness",),
            explanation=(
                "Gradient energy along skin/fabric boundaries. This is the main surface-auditability proxy: ordinary "
                "garment edges can carry visual implication without requiring explicit depiction. It supports milk when "
                "the boundary remains part of a coherent person-level image; it weakens if the crop becomes local inspection."
            ),
        ),
        ProxyNote(
            name="face_context_proxy",
            supports=("milk", "coal"),
            weakens=("personhood_collapse", "fragment_dominance"),
            explanation=(
                "Upper-region skin/context proxy. It is a weak stand-in for relation: face, upper-body context, gaze, "
                "or camera-aware presence. It cannot detect self-authorship directly, but it guards against treating a "
                "detached body surface as a complete sexual visual safety judgement."
            ),
        ),
        ProxyNote(
            name="public_context_penalty",
            supports=(),
            weakens=("milk", "coal"),
            explanation=(
                "Street or public-context proxy. It marks possible loss of private enclosure, which can lower milk and coal. "
                "It remains a soft gate because outdoor scenes can still be private when secluded and personally directed."
            ),
        ),
        ProxyNote(
            name="red_signal_penalty",
            supports=(),
            weakens=("milk", "peach"),
            explanation=(
                "Lower-central high-saturation colour proxy. It is a crude diagnostic pressure signal, not a semantic detector. "
                "Its role is to prevent the scoring system from mistaking aggressive local colour concentration for safe charge."
            ),
        ),
        ProxyNote(
            name="distortion_penalty",
            supports=(),
            weakens=("toy", "milk"),
            explanation=(
                "Mean pixel deviation from the raw input after restoration. It enforces source fidelity: restoration may clean "
                "compression artefacts, but it must not invent a more favourable body, contour, expression, or context."
            ),
        ),
        ProxyNote(
            name="edge_loss",
            supports=(),
            weakens=("toy", "milk"),
            explanation=(
                "Loss of gradient structure after restoration. It prevents compression cleanup from becoming blur. This is "
                "important because visual safety depends on alive coherence, not merely smoothness."
            ),
        ),
    )


def proxy_dictionary() -> dict[str, dict[str, object]]:
    """Dictionary form for JSON reports.

    Reports include the proxy dictionary so that a saved run can be read without
    reconstructing the whole chat context. The output should tell the user not
    just what scored, but why that score was allowed to matter.
    """
    return {
        note.name: {
            "supports": list(note.supports),
            "weakens": list(note.weakens),
            "explanation": note.explanation,
        }
        for note in proxy_notes()
    } | {"doctrine_note": {"supports": [], "weakens": [], "explanation": DOCTRINE_NOTE}}


def safe_normalize(x: np.ndarray) -> np.ndarray:
    """Normalize a proxy map without amplifying a constant empty map.

    Visual masks can be empty. Returning zeros for empty maps is more honest
    than forcing an artificial high-contrast display. This matters because mask
    visualisation itself can become misleading: a blank or weak signal should
    remain blank or weak rather than being inflated into apparent evidence.
    """
    span = float(x.max() - x.min())
    if span < 1e-6:
        return np.zeros_like(x, dtype=np.float32)
    return ((x - x.min()) / span).astype(np.float32)
