from flask import Flask, jsonify, render_template

from incident_store import (
    init_db,
    get_monitor_state,
    get_recent_incidents,
    get_recent_metrics,
    get_incident_summary,
)
import os
app = Flask(__name__)

# Ensure tables are initialized when the dashboard app starts
init_db()


@app.route("/")
def dashboard():
    """Render the PulseOps operations monitoring dashboard."""
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """Return the latest saved monitoring state."""
    try:
        state = get_monitor_state()
        if state is None:
            state = {
                "service": "DemoApp",
                "status": "UNKNOWN",
                "health": "UNKNOWN",
                "consecutive_failures": 0,
                "cpu": 0.0,
                "memory": 0.0,
                "disk": 0.0,
                "updated_at": None,
            }
        return jsonify(state)
    except Exception as error:
        return jsonify({
            "service": "DemoApp",
            "status": "UNKNOWN",
            "health": "UNKNOWN",
            "consecutive_failures": 0,
            "cpu": 0.0,
            "memory": 0.0,
            "disk": 0.0,
            "updated_at": None,
            "error": str(error),
        }), 500


@app.route("/api/summary")
def api_summary():
    """Return incident counts aggregated across all records."""
    try:
        summary = get_incident_summary()
        if not summary:
            summary = {
                "total": 0,
                "recovered": 0,
                "unresolved": 0,
                "open": 0,
            }
        return jsonify(summary)
    except Exception as error:
        return jsonify({
            "total": 0,
            "recovered": 0,
            "unresolved": 0,
            "open": 0,
            "error": str(error),
        }), 500


@app.route("/api/incidents")
def api_incidents():
    """Return the 10 most recent incidents."""
    try:
        incidents = get_recent_incidents(10)
        return jsonify(incidents if incidents is not None else [])
    except Exception as error:
        return jsonify([]), 500


@app.route("/api/metrics")
def api_metrics():
    """Return recent historical resource readings for the chart."""
    try:
        metrics = get_recent_metrics(30)
        return jsonify(metrics if metrics is not None else [])
    except Exception as error:
        return jsonify([]), 500


if __name__ == "__main__":
    app.run(
        host=os.environ.get("PULSEOPS_HOST", "127.0.0.1"),
        port=int(os.environ.get("PULSEOPS_PORT", "5000")),
        debug=False
    )
