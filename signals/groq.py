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
    explanation: str


def groq_signal(text: str, client: Groq | None = None) -> GroqSignalResult:
    """Return the model's estimated probability that ``text`` is AI-generated.

    The model is required to return JSON with an ``ai_probability`` number from
    0.00 to 1.00, and an optional ``explanation``. A client can be supplied to make
    the signal straightforward to test without making a network request.
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
                    "Assess whether the submitted text is AI-generated. "
                    "Use 0.00 for clearly human writing, 1.00 for clearly "
                    "AI-generated writing, and values near 0.50 for borderline "
                    "or mixed cases. Consider personal specificity, casualness, "
                    "formal or technical style, repetition, and editing. "
                    "Return only JSON with ai_probability, a number from 0.00 "
                    "to 1.00, and explanation, a concise string."
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
        explanation = result.get("explanation", "")
    except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Groq returned invalid classification JSON") from error

    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("Groq ai_probability must be a number")
    if not 0.00 <= score <= 1.00:
        raise ValueError("Groq ai_probability must be between 0.00 and 1.00")
    if not isinstance(explanation, str):
        raise ValueError("Groq explanation must be a string")

    return {
        "signal": "groq",
        "score": float(score),
        "explanation": explanation,
    }
