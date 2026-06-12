from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProxyNote:
    """Named explanation of a low-level proxy.

    This module is intentionally explanatory. The project needs a clear boundary
    between things the computer can measure directly and terms from the visual
    framework. A proxy note documents that boundary.
    """

    name: str
    supports: tuple[str, ...]
    weakens: tuple[str, ...]
    explanation: str


def proxy_notes() -> tuple[ProxyNote, ...]:
    """Return the current proxy dictionary used by reports and future tests.

    These descriptions are duplicated here rather than hidden in prose docs so
    code-generated reports can include the same methodology. This also makes it
    easier to unit-test that each numerical field has an explicit interpretive
    role.
    """
    return (
        ProxyNote(
            name="skin_smoothness",
            supports=("milk", "peach"),
            weakens=("harsh_surface", "compression_noise"),
            explanation="Low local variance over skin-like regions. It supports soft surface continuity but must be balanced against edge preservation.",
        ),
        ProxyNote(
            name="midriff_smoothness",
            supports=("milk", "peach"),
            weakens=("hard_segmentation", "fitness_like_edge_dominance"),
            explanation="Low local variance in the central body band. It approximates smooth unstrained surface, not a full register judgement.",
        ),
        ProxyNote(
            name="garment_threshold_structure",
            supports=("milk", "peach"),
            weakens=("featureless_flatness",),
            explanation="Gradient energy along skin/fabric boundaries. It supports ordinary garment-led visual structure when personhood remains intact.",
        ),
        ProxyNote(
            name="face_context_proxy",
            supports=("milk", "coal"),
            weakens=("personhood_collapse", "fragment_dominance"),
            explanation="Upper-region skin/context proxy. It is a weak stand-in for relation and should be replaced by real face/expression features later.",
        ),
        ProxyNote(
            name="public_context_penalty",
            supports=(),
            weakens=("milk", "coal"),
            explanation="Street or public-context proxy. It marks possible loss of private enclosure, while allowing later human correction for secluded settings.",
        ),
        ProxyNote(
            name="red_signal_penalty",
            supports=(),
            weakens=("milk", "peach"),
            explanation="Lower-central high-saturation colour proxy. It is a crude diagnostic penalty, not a semantic detector.",
        ),
        ProxyNote(
            name="distortion_penalty",
            supports=(),
            weakens=("toy", "milk"),
            explanation="Mean pixel deviation from the raw input after restoration. It prevents optimisation from improving a score by changing the source.",
        ),
        ProxyNote(
            name="edge_loss",
            supports=(),
            weakens=("toy", "milk"),
            explanation="Loss of gradient structure after restoration. It prevents compression cleanup from becoming blur.",
        ),
    )


def proxy_dictionary() -> dict[str, dict[str, object]]:
    """Dictionary form for JSON reports."""
    return {
        note.name: {
            "supports": list(note.supports),
            "weakens": list(note.weakens),
            "explanation": note.explanation,
        }
        for note in proxy_notes()
    }


def safe_normalize(x: np.ndarray) -> np.ndarray:
    """Normalize a proxy map without amplifying a constant empty map.

    Visual masks can be empty. Returning zeros for empty maps is more honest
    than forcing an artificial high-contrast display.
    """
    span = float(x.max() - x.min())
    if span < 1e-6:
        return np.zeros_like(x, dtype=np.float32)
    return ((x - x.min()) / span).astype(np.float32)
