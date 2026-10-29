import recovery


def test_recovery_action_uses_authenticated_post(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

    def fake_post(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        recovery,
        "SIMULATED_RECOVERY_URL",
        "http://recovery-agent/restart-demo-app",
    )
    monkeypatch.setattr(
        recovery,
        "RECOVERY_TOKEN",
        "test-token",
    )
    monkeypatch.setattr(recovery.requests, "post", fake_post)

    assert recovery.perform_recovery_action() is True
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["timeout"] > 3


def test_recovery_rejects_non_200_response(monkeypatch):
    class FakeResponse:
        status_code = 403

    monkeypatch.setattr(
        recovery,
        "SIMULATED_RECOVERY_URL",
        "http://recovery-agent/restart-demo-app",
    )
    monkeypatch.setattr(recovery, "RECOVERY_TOKEN", "test-token")
    monkeypatch.setattr(
        recovery.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert recovery.perform_recovery_action() is False


def test_recovery_verifies_success(monkeypatch):
    monkeypatch.setattr(recovery, "init_db", lambda: None)
    monkeypatch.setattr(recovery, "is_healthy", lambda: False)
    monkeypatch.setattr(
        recovery,
        "perform_recovery_action",
        lambda: True,
    )
    monkeypatch.setattr(
        recovery,
        "verify_recovery",
        lambda: True,
    )
    monkeypatch.setattr(recovery, "last_recovery_time", -1000.0)

    assert recovery.attempt_recovery() is True


def test_recovery_reports_exhausted_attempts(monkeypatch):
    monkeypatch.setattr(recovery, "init_db", lambda: None)
    monkeypatch.setattr(recovery, "is_healthy", lambda: False)
    monkeypatch.setattr(
        recovery,
        "perform_recovery_action",
        lambda: False,
    )
    monkeypatch.setattr(recovery, "last_recovery_time", -1000.0)

    # Keep the test fast without waiting between retry attempts.
    monkeypatch.setattr(recovery.time, "sleep", lambda _: None)

    assert recovery.attempt_recovery() is False
