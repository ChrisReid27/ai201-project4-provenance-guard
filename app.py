"""Flask application entry point for Provenance Guard."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask.typing import ResponseReturnValue

from signals.groq import groq_signal
from signals.stylometric import stylometric_signal
from scoring import calculate_confidence
from labels import generate_transparency_label


load_dotenv()
_AUDIT_LOG: list[dict[str, Any]] = []


def get_log() -> list[dict[str, Any]]:
    """Return a snapshot of the structured audit entries."""
    return list(_AUDIT_LOG)


def create_app(groq_client: Any = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[],
        storage_uri="memory://",
    )

    @app.route("/")
    def home():
        return "Provenance Guard is running."

    @app.post("/submit")
    @limiter.limit("10 per minute;100 per day")
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
            stylometric = stylometric_signal(payload["text"])
        except (RuntimeError, ValueError) as error:
            return jsonify({"error": str(error), "content_id": content_id}), 502

        confidence_result = calculate_confidence(
            attribution["score"], stylometric["score"]
        )
        label_text = generate_transparency_label(confidence_result["confidence"])
        _AUDIT_LOG.append(
            {
                "content_id": content_id,
                "creator_id": payload["creator_id"],
                "timestamp": datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                "attribution": confidence_result["label"],
                "confidence": confidence_result["confidence"],
                "label": label_text,
                "groq_score": attribution["score"],
                "llm_score": attribution["score"],
                "stylometric_score": stylometric["score"],
                "combined_score": confidence_result["combined_score"],
                "disagreement": confidence_result["disagreement"],
                "status": "classified",
                "appeal_filed": False,
            }
        )
        return (
            jsonify(
                {
                    "content_id": content_id,
                    "attribution": attribution,
                    "stylometric": stylometric,
                    "confidence": confidence_result["confidence"],
                    "label": label_text,
                }
            ),
            200,
        )

    @app.post("/appeal")
    def appeal() -> ResponseReturnValue:
        """Record an appeal and mark the original submission under review."""
        payload = request.get_json(silent=True)
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("content_id"), str)
            or not isinstance(payload.get("creator_reasoning"), str)
            or not payload["content_id"].strip()
            or not payload["creator_reasoning"].strip()
        ):
            return (
                jsonify(
                    {
                        "error": (
                            "Request JSON must include content_id and "
                            "creator_reasoning strings"
                        )
                    }
                ),
                400,
            )

        content_id = payload["content_id"]
        original = next(
            (
                entry
                for entry in reversed(_AUDIT_LOG)
                if entry.get("content_id") == content_id
                and entry.get("status") == "classified"
            ),
            None,
        )
        if original is None:
            return jsonify({"error": "No classified submission found"}), 404

        original["status"] = "under_review"
        original["appeal_filed"] = True
        _AUDIT_LOG.append(
            {
                "content_id": content_id,
                "creator_id": original["creator_id"],
                "timestamp": datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                "appeal_reasoning": payload["creator_reasoning"],
                "status": "under_review",
                "event": "appeal",
                "appeal_filed": True,
            }
        )
        return (
            jsonify(
                {
                    "content_id": content_id,
                    "status": "under_review",
                    "message": "Appeal received",
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
