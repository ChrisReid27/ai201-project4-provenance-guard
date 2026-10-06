"""Groq-based AI-generation classification signal."""

from __future__ import annotations

import json
import os
from typing import Any, TypedDict

from groq import Groq


MODEL = "openai/gpt-oss-120b"


class GroqSignalResult(TypedDict):
    """Structured output returned by the Groq signal."""

    signal: str
    score: float


def groq_signal(text: str, client: Groq | None = None) -> GroqSignalResult:
    """Return the model's estimated probability that ``text`` is AI-generated.

    The model is required to return JSON with only an ``ai_probability`` number
    from 0.00 to 1.00. A client can be supplied to make the signal
    straightforward to test without making a network request.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")

    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required to run the Groq signal")
        client = Groq(api_key=api_key)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Assess whether the submitted text is AI-generated and "
                    "return only JSON in this exact shape: "
                    '{"ai_probability": 0.00}. '
                    "Use these score anchors: 0.00-0.20 strongly human, "
                    "0.21-0.40 probably human, 0.41-0.59 borderline, "
                    "0.60-0.79 probably AI, and 0.80-1.00 strongly AI. "
                    "Evaluate personal specificity, conversational language, "
                    "generic or formulaic phrasing, repetition, sentence "
                    "organization, and signs of editing or mixed authorship. "
                    "Do not treat formal, technical, academic, or promotional "
                    "writing as AI by itself."
                ),
            },
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("Groq returned an empty classification")

    try:
        result: Any = json.loads(content)
        score = result["ai_probability"]
    except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Groq returned invalid classification JSON") from error

    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("Groq ai_probability must be a number")
    if not 0.00 <= score <= 1.00:
        raise ValueError("Groq ai_probability must be between 0.00 and 1.00")
    return {
        "signal": "groq",
        "score": float(score),
    }
