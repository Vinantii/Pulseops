
import time
from datetime import datetime

import requests

from incident_store import init_db, update_incident


# DemoApp endpoints
HEALTH_URL = "http://127.0.0.1:5001/health"

# Local testing only; this resets the simulated failure.
# We will replace this with a controlled service restart on AWS.
SIMULATED_RECOVERY_URL = (
    "http://127.0.0.1:5001/test-recovery"
)

REQUEST_TIMEOUT = 3
MAX_RECOVERY_ATTEMPTS = 3
VERIFY_RETRIES = 5
VERIFY_INTERVAL = 1
RETRY_DELAY = 2
COOLDOWN_SECONDS = 15

last_recovery_time = 0.0


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
    """Reset the simulated failure during local development."""
    try:
        response = requests.get(
            SIMULATED_RECOVERY_URL,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            log("Local simulated recovery action completed.")
            return True

        log(
            f"Recovery action failed with HTTP "
            f"{response.status_code}."
        )
        return False

    except requests.RequestException as error:
        log(f"Recovery action failed: {error}")
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
