from flask import Flask, jsonify

app = Flask(__name__)

# Simulated in-memory health state for DemoApp
is_healthy = True


@app.route("/")
def index():
    """Root info endpoint for DemoApp."""
    return jsonify({
        "service": "DemoApp",
        "status": "running",
        "healthy": is_healthy,
    })


@app.route("/health")
def health():
    """Health check endpoint checked by PulseOps monitor."""
    if is_healthy:
        return jsonify({
            "service": "DemoApp",
            "status": "healthy",
        }), 200
    else:
        return jsonify({
            "service": "DemoApp",
            "status": "unhealthy",
            "error": "Simulated service failure",
        }), 500


@app.route("/simulate-failure")
@app.route("/simulate-crash")
@app.route("/crash")
def simulate_failure():
    """Simulate a service failure for DevOps recovery testing."""
    global is_healthy
    is_healthy = False
    return jsonify({
        "service": "DemoApp",
        "status": "failure_simulated",
        "healthy": False,
    }), 200


@app.route("/test-recovery")
def test_recovery():
    """Reset simulated failure, invoked by recovery.py during automated recovery."""
    global is_healthy
    is_healthy = True
    return jsonify({
        "service": "DemoApp",
        "status": "recovered",
        "healthy": True,
    }), 200


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
    )
