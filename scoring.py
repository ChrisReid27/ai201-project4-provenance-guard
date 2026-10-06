"""Confidence scoring and transparency labels for detection signals."""

from __future__ import annotations

import math
from typing import Literal, TypedDict


Label = Literal["High Confidence Human", "Uncertain", "High Confidence AI"]
_BOUNDARY_EPSILON = 1e-12


class ConfidenceResult(TypedDict):
    """Combined scores and label produced by the confidence calculator."""

    combined_score: float
    disagreement: float
    confidence: float
    label: Label


def calculate_confidence(groq_score: float, stylometric_score: float) -> ConfidenceResult:
    """Combine prototype signal scores with a soft disagreement penalty.

    Groq has a 0.75 weight and stylometrics has a 0.25 weight while the
    stylometric signal remains an uncalibrated prototype. Disagreement reduces
    confidence but no longer overrides the combined classification.
    """
    scores = (groq_score, stylometric_score)
    if any(
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
        or not 0.0 <= score <= 1.0
        for score in scores
    ):
        raise ValueError("signal scores must be finite numbers between 0 and 1")

    combined_score = 0.75 * groq_score + 0.25 * stylometric_score
    disagreement = abs(groq_score - stylometric_score)
    confidence = combined_score + (0.5 - combined_score) * 0.5 * disagreement
    if confidence <= 0.44 + _BOUNDARY_EPSILON:
        label: Label = "High Confidence Human"
    elif confidence >= 0.66 - _BOUNDARY_EPSILON:
        label = "High Confidence AI"
    else:
        label = "Uncertain"

    return {
        "combined_score": float(combined_score),
        "disagreement": float(disagreement),
        "confidence": float(confidence),
        "label": label,
    }
