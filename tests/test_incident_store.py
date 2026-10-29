import incident_store
import pytest


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    database_path = tmp_path / "test_incidents.db"

    monkeypatch.setattr(
        incident_store,
        "DB_PATH",
        database_path,
    )

    incident_store.init_db()

    return database_path


def test_create_incident(test_db):
    incident_id = incident_store.create_incident(
        service="DemoApp",
        failure_type="Health check failed",
        details="Three consecutive failures",
    )

    incidents = incident_store.get_recent_incidents(10)

    assert len(incidents) == 1
    assert incidents[0]["id"] == incident_id
    assert incidents[0]["incident_code"] == f"INC-{incident_id:04d}"
    assert incidents[0]["status"] == "OPEN"


def test_update_incident_to_recovered(test_db):
    incident_id = incident_store.create_incident(
        "DemoApp",
        "Health check failed",
    )

    incident_store.update_incident(
        incident_id,
        status="RECOVERED",
        recovery_attempts=1,
        details="Recovery verified",
    )

    incident = incident_store.get_recent_incidents(1)[0]

    assert incident["status"] == "RECOVERED"
    assert incident["recovery_attempts"] == 1
    assert incident["resolved_at"] is not None


def test_incident_summary(test_db):
    incident_store.create_incident("DemoApp", "Failure")
    incident_id = incident_store.create_incident("DemoApp", "Failure")

    incident_store.update_incident(
        incident_id,
        status="UNRESOLVED",
        recovery_attempts=3,
    )

    summary = incident_store.get_incident_summary()

    assert summary["total"] == 2
    assert summary["open"] == 1
    assert summary["unresolved"] == 1


def test_incident_survives_database_reinitialization(test_db):
    incident_store.create_incident("DemoApp", "Failure")

    incident_store.init_db()

    incidents = incident_store.get_recent_incidents(10)

    assert len(incidents) == 1
    assert incidents[0]["service"] == "DemoApp"


def test_invalid_incident_status_is_rejected(test_db):
    incident_id = incident_store.create_incident(
        "DemoApp",
        "Health check failed",
    )

    with pytest.raises(ValueError):
        incident_store.update_incident(
            incident_id,
            status="INVALID",
        )
