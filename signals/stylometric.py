"""Stylometric heuristics for estimating AI-generation likelihood."""

from __future__ import annotations

import math
import re
import string
from typing import TypedDict


_WORD_PATTERN = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)?")
_SENTENCE_PATTERN = re.compile(r"[^.!?]+")


class StylometricSignalResult(TypedDict):
    """Structured output returned by the stylometric signal."""

    signal: str
    score: float
    features: dict[str, float]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def stylometric_signal(text: str) -> StylometricSignalResult:
    """Estimate AI-generation likelihood from three surface-level metrics.

    The score is a transparent heuristic, not a calibrated probability. It
    combines sentence-length uniformity, type-token ratio, and punctuation
    density; calibration can replace these weights once labeled data exists.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")

    words = [word.lower() for word in _WORD_PATTERN.findall(text)]
    if not words:
        raise ValueError("text must contain at least one word")

    sentences = [
        _WORD_PATTERN.findall(sentence)
        for sentence in _SENTENCE_PATTERN.findall(text)
    ]
    sentence_lengths = [len(sentence) for sentence in sentences if sentence]
    mean_length = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((length - mean_length) ** 2 for length in sentence_lengths) / len(
        sentence_lengths
    )
    sentence_length_stddev = math.sqrt(variance)
    if len(sentence_lengths) < 2:
        sentence_uniformity = 0.5
    else:
        sentence_uniformity = 1.0 / (1.0 + sentence_length_stddev)

    type_token_ratio = len(set(words)) / len(words)
    punctuation_count = sum(character in string.punctuation for character in text)
    punctuation_density = punctuation_count / len(words)

    # These broad ranges keep the uncalibrated heuristic on the required 0-1 scale.
    ttr_ai_likelihood = _clamp((type_token_ratio - 0.35) / 0.45)
    punctuation_ai_likelihood = _clamp(punctuation_density / 0.20)
    raw_score = _clamp(
        0.45 * sentence_uniformity
        + 0.35 * ttr_ai_likelihood
        + 0.20 * punctuation_ai_likelihood
    )
    reliability = min(1.0, len(words) / 100.0)
    score = _clamp(0.5 + reliability * (raw_score - 0.5))

    return {
        "signal": "stylometric",
        "score": score,
        "features": {
            "sentence_length_stddev": sentence_length_stddev,
            "sentence_uniformity": sentence_uniformity,
            "type_token_ratio": type_token_ratio,
            "punctuation_density": punctuation_density,
            "reliability": reliability,
        },
    }
