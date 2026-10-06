"""Transparency label text generation."""

from __future__ import annotations

from typing import Literal


TransparencyLabel = Literal[
    "This text is highly likely AI generated.",
    "This text is highly likely to be human written.",
    "This text may contain both AI generated content and actual human writing, one or the other is uncertain.",
]


def generate_transparency_label(confidence: float) -> TransparencyLabel:
    """Map a confidence score to the transparency text from the project plan."""
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if confidence <= 0.44:
        return "This text is highly likely to be human written."
    if confidence >= 0.66:
        return "This text is highly likely AI generated."
    return (
        "This text may contain both AI generated content and actual human writing, "
        "one or the other is uncertain."
    )
