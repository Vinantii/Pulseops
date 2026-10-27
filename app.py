
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <h1>Welcome to PulseOps</h1>
    <p>Self-Healing Application Monitoring System</p>
    <p>Project status: Initial setup successful!</p>
    """


if __name__ == "__main__":
    app.run(debug=True)
