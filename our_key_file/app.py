import os
from pathlib import Path
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, messaging

# Default device token; override by sending "token" in the request body if needed.
DEFAULT_DEVICE_TOKEN = (
    "d-vfm9fETqaAB0BWgLPwPa:APA91bFVEHmxTSwBPfbs30nWkMFM1AGUuZwJlPG5Wadw_6hPUGQI92R82QA4VnNfCfl0DASyh-pWslN0hd5aeejHVgrnR1e6fB8LL3uZcUgs6L9_tFqnbuo"
)

BASE_DIR = Path(__file__).parent
SERVICE_ACCOUNT_PATH = BASE_DIR / "key" / "testingflutter-7c752-firebase-adminsdk-fbsvc-407057a89c.json"

app = Flask(__name__)


def initialize_firebase() -> None:
    """Initialize Firebase app once using the service account."""
    if firebase_admin._apps:
        return
    if not SERVICE_ACCOUNT_PATH.exists():
        raise FileNotFoundError(f"Service account key not found at {SERVICE_ACCOUNT_PATH}")
    cred = credentials.Certificate(str(SERVICE_ACCOUNT_PATH))
    firebase_admin.initialize_app(cred)


initialize_firebase()


@app.route("/notify", methods=["POST"])
def send_notification():
    # Accepts JSON: {"title": "...", "body": "...", "token": "...", "data": {"k": "v"}}
    payload = request.get_json(force=True, silent=True) or {}
    title = payload.get("title") or "Hello from Flask"
    body = payload.get("body") or "Firebase push notification test"
    token = payload.get("token") or DEFAULT_DEVICE_TOKEN
    data = payload.get("data") or {}

    if not token:
        return jsonify({"error": "Missing device token"}), 400

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in data.items()},
        token=token,
    )

    try:
        response = messaging.send(message)
        return jsonify({"message_id": response}), 200
    except Exception as exc:  # Broad catch to surface FCM errors to client
        return jsonify({"error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
