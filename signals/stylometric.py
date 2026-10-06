"""General stylometric features and an optional calibrated signal model."""

from __future__ import annotations

import math
import re
import string
from typing import Protocol, TypedDict


_WORD_PATTERN = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)?")
_SENTENCE_PATTERN = re.compile(r"[^.!?]+")
_FUNCTION_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


class StylometricModel(Protocol):
    """Interface for a fitted, calibrated classifier."""

    def predict_proba(self, features: list[float]) -> float:
        """Return the calibrated AI-likelihood for one feature vector."""


class StylometricSignalResult(TypedDict):
    """Structured output returned by the stylometric signal."""

    signal: str
    score: float
    features: dict[str, float]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def extract_stylometric_features(text: str) -> dict[str, float]:
    """Extract domain-independent features for calibration or inspection."""
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
    mean_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
    sentence_variance = sum(
        (length - mean_sentence_length) ** 2 for length in sentence_lengths
    ) / len(sentence_lengths)
    sentence_length_stddev = math.sqrt(sentence_variance)

    word_lengths = [len(word) for word in words]
    mean_word_length = sum(word_lengths) / len(word_lengths)
    word_length_variance = sum(
        (length - mean_word_length) ** 2 for length in word_lengths
    ) / len(word_lengths)

    punctuation_count = sum(character in string.punctuation for character in text)
    repeated_words = len(words) - len(set(words))
    uppercase_words = sum(word.isupper() for word in text.split() if word.isalpha())
    function_words = sum(word in _FUNCTION_WORDS for word in words)

    return {
        "sentence_length_mean": mean_sentence_length,
        "sentence_length_stddev": sentence_length_stddev,
        "sentence_uniformity": 1.0 / (1.0 + sentence_length_stddev),
        "word_length_mean": mean_word_length,
        "word_length_stddev": math.sqrt(word_length_variance),
        "type_token_ratio": len(set(words)) / len(words),
        "repetition_ratio": repeated_words / len(words),
        "punctuation_density": punctuation_count / len(words),
        "uppercase_ratio": uppercase_words / len(words),
        "function_word_ratio": function_words / len(words),
        "question_ratio": text.count("?") / max(1, len(sentence_lengths)),
        "exclamation_ratio": text.count("!") / max(1, len(sentence_lengths)),
    }


def _provisional_score(features: dict[str, float]) -> float:
    """Return a replaceable baseline until a labeled model is available."""
    type_token_signal = _clamp((features["type_token_ratio"] - 0.35) / 0.45)
    punctuation_signal = _clamp(features["punctuation_density"] / 0.20)
    repetition_signal = _clamp(features["repetition_ratio"] / 0.35)
    return _clamp(
        0.35 * features["sentence_uniformity"]
        + 0.30 * type_token_signal
        + 0.20 * punctuation_signal
        + 0.15 * (1.0 - repetition_signal)
    )


def stylometric_signal(
    text: str, model: StylometricModel | None = None
) -> StylometricSignalResult:
    """Return an AI-likelihood score from general stylometric features.

    A fitted calibrated model may be supplied. Without one, the result uses a
    provisional bounded heuristic; it is not a substitute for calibration.
    """
    features = extract_stylometric_features(text)
    feature_vector = list(features.values())
    score = (
        model.predict_proba(feature_vector)
        if model is not None
        else _provisional_score(features)
    )
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("stylometric model must return a numeric score")
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("stylometric score must be finite and between 0 and 1")

    return {"signal": "stylometric", "score": float(score), "features": features}
