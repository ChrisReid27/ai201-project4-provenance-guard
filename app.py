"""Flask application entry point for Provenance Guard."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue

from signals.groq import groq_signal


load_dotenv()


def create_app(groq_client: Any = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["AUDIT_LOG"] = []

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
        app.config["AUDIT_LOG"].append(
            {
                "content_id": content_id,
                "creator_id": payload["creator_id"],
                "text": payload["text"],
                "attribution": attribution,
                "confidence": confidence,
                "label": label,
                "timestamp": datetime.now(timezone.utc).isoformat(),
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

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=5000, debug=True)
