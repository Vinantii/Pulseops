
import time
from datetime import datetime

import requests

from incident_store import init_db, update_incident
import os

# DemoApp endpoints
HEALTH_URL = os.environ.get(
    "PULSEOPS_HEALTH_URL",
    "http://127.0.0.1:5001/health"
)

SIMULATED_RECOVERY_URL = os.environ.get(
    "PULSEOPS_RECOVERY_URL",
    "http://127.0.0.1:5001/test-recovery"
)

RECOVERY_TOKEN = os.environ.get(
    "PULSEOPS_RECOVERY_TOKEN",
    ""
)

# Local testing only; this resets the simulated failure.
# We will replace this with a controlled service restart on AWS.


REQUEST_TIMEOUT = 3
MAX_RECOVERY_ATTEMPTS = 3
VERIFY_RETRIES = 5
VERIFY_INTERVAL = 1
RETRY_DELAY = 2
COOLDOWN_SECONDS = 15

last_recovery_time = 0.0
AGENT_REQUEST_TIMEOUT = 35

def log(message):
    """Print a timestamped recovery event."""
    current_time = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    print(f"[{current_time}] {message}")


def is_healthy():
    """Return True only when DemoApp responds with HTTP 200."""
    try:
        response = requests.get(
            HEALTH_URL,
            timeout=REQUEST_TIMEOUT
        )
        return response.status_code == 200

    except requests.RequestException:
        return False

def perform_recovery_action():
    """Request a restricted restart of the DemoApp container."""

    if not RECOVERY_TOKEN:
        log("Recovery failed: token is not configured.")
        return False

    try:
        response = requests.post(
            SIMULATED_RECOVERY_URL,
            headers={
                "Authorization": f"Bearer {RECOVERY_TOKEN}"
            },
            timeout=AGENT_REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            log("Host recovery agent accepted the restart request.")
            return True

        log(
            f"Recovery agent returned HTTP "
            f"{response.status_code}."
        )
        return False

    except requests.RequestException as error:
        log(f"Recovery agent request failed: {error}")

        # A restart may have succeeded even if the response was delayed.
        # Verify actual application health before declaring failure.
        for check_number in range(5):
            if is_healthy():
                log(
                    "DemoApp is healthy after the recovery request. "
                    "Treating recovery as successful."
                )
                return True

            if check_number < 4:
                time.sleep(1)

        return False


def verify_recovery():
    """Check whether DemoApp becomes healthy after recovery."""
    for check_number in range(1, VERIFY_RETRIES + 1):
        time.sleep(VERIFY_INTERVAL)

        if is_healthy():
            log(
                f"Health verification passed "
                f"({check_number}/{VERIFY_RETRIES})."
            )
            return True

        log(
            f"Health verification failed "
            f"({check_number}/{VERIFY_RETRIES})."
        )

    return False


def attempt_recovery(incident_id=None):
    """Attempt recovery and persist the result when an ID is provided."""
    global last_recovery_time

    init_db()

    # The service may have recovered before we started this function.
    if is_healthy():
        log("DemoApp is already healthy.")

        if incident_id is not None:
            update_incident(
                incident_id,
                "RECOVERED",
                recovery_attempts=0,
                details="Service was healthy before a recovery action."
            )

        return True

    current_time = time.monotonic()

    if current_time - last_recovery_time < COOLDOWN_SECONDS:
        log("Recovery skipped: cooldown is still active.")

        if incident_id is not None:
            update_incident(
                incident_id,
                "UNRESOLVED",
                recovery_attempts=0,
                details="Recovery was skipped because cooldown was active."
            )

        return False

    for attempt in range(1, MAX_RECOVERY_ATTEMPTS + 1):
        last_recovery_time = time.monotonic()

        log(
            f"Recovery attempt {attempt}/"
            f"{MAX_RECOVERY_ATTEMPTS}."
        )

        if incident_id is not None:
            update_incident(
                incident_id,
                "OPEN",
                recovery_attempts=attempt,
                details=f"Recovery attempt {attempt} started."
            )

        action_succeeded = perform_recovery_action()

        if action_succeeded and verify_recovery():
            log("RECOVERED: DemoApp is healthy again.")

            if incident_id is not None:
                update_incident(
                    incident_id,
                    "RECOVERED",
                    recovery_attempts=attempt,
                    details="Recovery succeeded and health was verified."
                )

            return True

        log(f"Recovery attempt {attempt} was unsuccessful.")

        if attempt < MAX_RECOVERY_ATTEMPTS:
            time.sleep(RETRY_DELAY)

    log(
        "UNRESOLVED: Recovery attempts exhausted. "
        "Manual investigation is required."
    )

    if incident_id is not None:
        update_incident(
            incident_id,
            "UNRESOLVED",
            recovery_attempts=MAX_RECOVERY_ATTEMPTS,
            details="All recovery attempts failed."
        )

    return False


if __name__ == "__main__":
    attempt_recovery()
