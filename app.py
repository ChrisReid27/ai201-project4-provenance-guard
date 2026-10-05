"""Flask application entry point for Provenance Guard."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

from signals.groq import groq_signal


load_dotenv()
_AUDIT_LOG: list[dict[str, Any]] = []


def get_log() -> list[dict[str, Any]]:
    """Return a snapshot of the structured audit entries."""
    return list(_AUDIT_LOG)


def _attribution_label(score: float) -> str:
    """Map the signal score to the current attribution categories."""
    if score >= 0.66:
        return "likely_ai"
    if score <= 0.44:
        return "likely_human"
    return "uncertain"


def create_app(groq_client: Any = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Provenance Guard is running."

    @app.post("/submit")
    def submit() -> ResponseReturnValue:
        """Classify a submission with signal one and return its initial result."""
        payload = request.get_json(silent=True)
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("text"), str)
            or not isinstance(payload.get("creator_id"), str)
        ):
            return (
                jsonify(
                    {"error": "Request JSON must include text and creator_id strings"}
                ),
                400,
            )

        content_id = str(uuid4())
        try:
            attribution = groq_signal(payload["text"], client=groq_client)
        except (RuntimeError, ValueError) as error:
            return jsonify({"error": str(error), "content_id": content_id}), 502

        confidence = 0.5
        label = "Uncertain"
        _AUDIT_LOG.append(
            {
                "content_id": content_id,
                "creator_id": payload["creator_id"],
                "timestamp": datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                "attribution": _attribution_label(attribution["score"]),
                "confidence": confidence,
                "llm_score": attribution["score"],
                "status": "classified",
            }
        )
        return (
            jsonify(
                {
                    "content_id": content_id,
                    "attribution": attribution,
                    "confidence": confidence,
                    "label": label,
                }
            ),
            200,
        )

    @app.get("/log")
    def audit_log() -> ResponseReturnValue:
        """Return the most recent structured audit entries."""
        return jsonify({"entries": get_log()})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=5000, debug=True)
