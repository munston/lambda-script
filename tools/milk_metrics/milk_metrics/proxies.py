from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProxyNote:
    """Named explanation of a low-level proxy.

    This module documents the boundary between measurable image features and
    interpretive register terms. A proxy is visible evidence, not a final
    judgement. Smoothness, colour structure, boundary strength, or environment
    pressure may support a register only when the wider image keeps context and
    visual coherence intact.
    """

    name: str
    supports: tuple[str, ...]
    weakens: tuple[str, ...]
    explanation: str


DOCTRINE_NOTE = (
    "Visual safety is judged as a relation between visible evidence and the retained subject. "
    "The proxy layer measures surface, boundary, context, and restoration behaviour; register "
    "inference and gate correction remain above this layer."
)


def proxy_notes() -> tuple[ProxyNote, ...]:
    """Return the current proxy dictionary used by reports and tests."""
    return (
        ProxyNote(
            name="surface_smoothness",
            supports=("milk", "peach"),
            weakens=("harsh_surface", "compression_noise"),
            explanation="Low local variance over surface-like regions. It supports soft continuity, but must be balanced against edge preservation.",
        ),
        ProxyNote(
            name="central_smoothness",
            supports=("milk", "peach"),
            weakens=("hard_segmentation", "over_defined_surface"),
            explanation="Low local variance in the central image band. It is a primitive only; crop context still matters.",
        ),
        ProxyNote(
            name="boundary_structure",
            supports=("milk", "peach"),
            weakens=("featureless_flatness",),
            explanation="Gradient energy along surface/fabric boundaries. It supports ordinary threshold structure and surface auditability.",
        ),
        ProxyNote(
            name="upper_context_proxy",
            supports=("milk", "coal"),
            weakens=("context_loss", "fragment_dominance"),
            explanation="Upper-region context proxy. It weakly represents relation, upper-frame presence, or camera-aware framing.",
        ),
        ProxyNote(
            name="environment_penalty",
            supports=(),
            weakens=("milk", "coal"),
            explanation="Environment/public-context proxy. It marks possible loss of private enclosure and remains a soft gate.",
        ),
        ProxyNote(
            name="chroma_penalty",
            supports=(),
            weakens=("milk", "peach"),
            explanation="High-chroma proxy pressure. It is a crude diagnostic penalty, not a semantic detector.",
        ),
        ProxyNote(
            name="distortion_penalty",
            supports=(),
            weakens=("toy", "milk"),
            explanation="Mean pixel deviation from the raw input after restoration. It enforces source fidelity.",
        ),
        ProxyNote(
            name="edge_loss",
            supports=(),
            weakens=("toy", "milk"),
            explanation="Loss of gradient structure after restoration. It prevents cleanup from becoming blur.",
        ),
    )


def proxy_dictionary() -> dict[str, dict[str, object]]:
    """Dictionary form for JSON reports."""
    d = {
        note.name: {
            "supports": list(note.supports),
            "weakens": list(note.weakens),
            "explanation": note.explanation,
        }
        for note in proxy_notes()
    }
    d["doctrine_note"] = {"supports": [], "weakens": [], "explanation": DOCTRINE_NOTE}
    return d


def safe_normalize(x: np.ndarray) -> np.ndarray:
    """Normalize a proxy map without amplifying a constant empty map."""
    span = float(x.max() - x.min())
    if span < 1e-6:
        return np.zeros_like(x, dtype=np.float32)
    return ((x - x.min()) / span).astype(np.float32)
