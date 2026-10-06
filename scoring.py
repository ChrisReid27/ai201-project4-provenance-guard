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
    """Combine calibrated signal scores using the planned thresholds.

    Scores in [0.00, 0.44] are human and scores in [0.66, 1.00] are AI
    only when disagreement is below 0.25. All other results are uncertain.
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

    combined_score = 0.6 * groq_score + 0.4 * stylometric_score
    disagreement = abs(groq_score - stylometric_score)
    if disagreement >= 0.25 - _BOUNDARY_EPSILON:
        label: Label = "Uncertain"
        confidence = 0.5
    elif combined_score <= 0.44 + _BOUNDARY_EPSILON:
        label = "High Confidence Human"
        confidence = combined_score
    elif combined_score >= 0.66 - _BOUNDARY_EPSILON:
        label = "High Confidence AI"
        confidence = combined_score
    else:
        label = "Uncertain"
        confidence = combined_score

    return {
        "combined_score": float(combined_score),
        "disagreement": float(disagreement),
        "confidence": float(confidence),
        "label": label,
    }
