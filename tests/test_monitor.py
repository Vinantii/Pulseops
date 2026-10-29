import monitor
import requests


NORMAL_METRICS = {
    "cpu": 10.0,
    "memory": 50.0,
    "disk": 45.0,
}


def setup_function():
    monitor.consecutive_failures = 0


def test_healthy_service_is_healthy():
    status = monitor.determine_status(True, NORMAL_METRICS)

    assert status == "HEALTHY"
    assert monitor.consecutive_failures == 0


def test_high_memory_marks_service_degraded():
    metrics = {
        "cpu": 10.0,
        "memory": 85.0,
        "disk": 45.0,
    }

    assert monitor.determine_status(True, metrics) == "DEGRADED"


def test_three_consecutive_failures_mark_service_down():
    assert monitor.determine_status(False, NORMAL_METRICS) == "DEGRADED"
    assert monitor.determine_status(False, NORMAL_METRICS) == "DEGRADED"
    assert monitor.determine_status(False, NORMAL_METRICS) == "DOWN"
    assert monitor.consecutive_failures == 3


def test_success_resets_consecutive_failures():
    monitor.consecutive_failures = 2

    status = monitor.determine_status(True, NORMAL_METRICS)

    assert status == "HEALTHY"
    assert monitor.consecutive_failures == 0


def test_health_check_accepts_http_200(monkeypatch):
    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(
        monitor.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert monitor.check_health() is True


def test_health_check_rejects_http_503(monkeypatch):
    class FakeResponse:
        status_code = 503

    monkeypatch.setattr(
        monitor.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert monitor.check_health() is False


def test_health_check_handles_connection_error(monkeypatch):
    def fail_request(*args, **kwargs):
        raise requests.ConnectionError("Simulated connection failure")

    monkeypatch.setattr(monitor.requests, "get", fail_request)

    assert monitor.check_health() is False
