"""
Flask webhook receiver. Alertmanager POSTs here (see monitoring/alertmanager
config, receiver "remediation-engine"). Each firing alert is run through
remediation_engine.remediate() and the outcome is logged and returned.
"""
import logging
import sys

from flask import Flask, request, jsonify

from config import WEBHOOK_SECRET, LOG_LEVEL, MAX_ATTEMPTS
from remediation_engine import remediate

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("remediation.app")

app = Flask(__name__)

# In-memory history of the most recent remediation results, exposed at
# /history purely so the failure-testing scripts and a human demoing the
# project can see "what did the engine do" without grepping pod logs.
_recent_results = []
_MAX_HISTORY = 100


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/history")
def history():
    return jsonify(_recent_results[-_MAX_HISTORY:]), 200


@app.post("/webhook")
def webhook():
    if WEBHOOK_SECRET:
        provided = request.headers.get("X-Webhook-Secret", "")
        if provided != WEBHOOK_SECRET:
            log.warning("Rejected webhook call with invalid secret")
            return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    alerts = payload.get("alerts", [])
    if not alerts:
        return jsonify({"error": "no alerts in payload"}), 400

    results = []
    for alert in alerts:
        # Only act on alerts that are actively firing; resolved notifications
        # are logged but never trigger a remediation action.
        if alert.get("status") != "firing":
            log.info("Ignoring non-firing alert: %s", alert.get("labels", {}).get("alertname"))
            continue

        result = remediate(alert)
        log.info("Remediation result: %s", result.to_dict())
        _recent_results.append(result.to_dict())
        results.append(result.to_dict())

    return jsonify({"processed": len(results), "max_attempts": MAX_ATTEMPTS, "results": results}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
