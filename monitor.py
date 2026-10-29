
import os
import time
from datetime import datetime

import psutil
import requests

from recovery import attempt_recovery
from incident_store import (
    init_db,
    create_incident,
    save_monitor_state,
)


# DemoApp configuration
HEALTH_URL = os.environ.get(
    "PULSEOPS_HEALTH_URL",
    "http://127.0.0.1:5001/health"
)

CHECK_INTERVAL = 5
REQUEST_TIMEOUT = 3
FAILURE_LIMIT = 3

# Resource warning thresholds (percentages)
CPU_WARNING_THRESHOLD = 85
MEMORY_WARNING_THRESHOLD = 85
DISK_WARNING_THRESHOLD = 90

consecutive_failures = 0


def timestamp():
    """Return the current local date and time."""
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def get_resource_metrics():
    """Collect CPU, RAM and disk usage."""
    disk_path = os.path.abspath(os.sep) if os.name == "nt" else "/"

    return {
        "cpu": psutil.cpu_percent(interval=0.2),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(disk_path).percent,
    }


def check_health():
    """Check DemoApp and return whether it is healthy."""
    try:
        response = requests.get(
            HEALTH_URL,
            timeout=REQUEST_TIMEOUT,
        )
        return response.status_code == 200

    except requests.RequestException:
        return False


def determine_status(healthy, metrics):
    """Determine service status and update the failure count."""
    global consecutive_failures

    if healthy:
        consecutive_failures = 0

        resource_warning = (
            metrics["cpu"] >= CPU_WARNING_THRESHOLD
            or metrics["memory"] >= MEMORY_WARNING_THRESHOLD
            or metrics["disk"] >= DISK_WARNING_THRESHOLD
        )

        return "DEGRADED" if resource_warning else "HEALTHY"

    consecutive_failures += 1

    if consecutive_failures >= FAILURE_LIMIT:
        return "DOWN"

    return "DEGRADED"


def monitor():
    """Monitor DemoApp, manage incidents and persist metrics."""

    init_db()

    previous_status = None

    print("=" * 55)
    print("PulseOps Monitoring Engine Started")
    print(f"Target: {HEALTH_URL}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print("=" * 55)

    while True:
        cycle_start = time.monotonic()

        # 1. Check application health and resource usage.
        healthy = check_health()
        metrics = get_resource_metrics()
        status = determine_status(healthy, metrics)

        # 2. Save the latest state and resource readings to SQLite.
        save_monitor_state(
            status=status,
            health="OK" if healthy else "FAILED",
            consecutive_failures=consecutive_failures,
            cpu=metrics["cpu"],
            memory=metrics["memory"],
            disk=metrics["disk"],
        )

        # 3. Print the monitoring results.
        print(
            f"[{timestamp()}] "
            f"Status: {status} | "
            f"Health: {'OK' if healthy else 'FAILED'} | "
            f"Failures: {consecutive_failures} | "
            f"CPU: {metrics['cpu']:.1f}% | "
            f"RAM: {metrics['memory']:.1f}% | "
            f"Disk: {metrics['disk']:.1f}%"
        )

        if not healthy:
            print(
                f"  WARNING: Health check failed "
                f"({consecutive_failures}/{FAILURE_LIMIT})"
            )

        # 4. Create an incident and trigger recovery on DOWN.
        if status == "DOWN":
            print("  ALERT: DemoApp is DOWN!")

            if previous_status != "DOWN":
                incident_id = create_incident(
                    service="DemoApp",
                    failure_type="Health check failed",
                    details=(
                        f"{consecutive_failures} consecutive "
                        "health checks failed."
                    ),
                )

                print(
                    f"  Created incident: INC-{incident_id:04d}"
                )
                print("  Starting automatic recovery...")

                recovered = attempt_recovery(incident_id)

                if recovered:
                    print(
                        "  PulseOps: Recovery verified successfully."
                    )
                else:
                    print(
                        "  PulseOps: Recovery unsuccessful."
                    )

        # 5. Track the previous status to prevent repeated triggers.
        previous_status = status

        # 6. Warn about high resource usage.
        if (
            metrics["cpu"] >= CPU_WARNING_THRESHOLD
            or metrics["memory"] >= MEMORY_WARNING_THRESHOLD
            or metrics["disk"] >= DISK_WARNING_THRESHOLD
        ):
            print("  WARNING: High resource usage detected.")

        elapsed = time.monotonic() - cycle_start
        time.sleep(max(0, CHECK_INTERVAL - elapsed))


if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\nPulseOps monitoring stopped.")
