
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


# Store the database alongside the project files.
DB_PATH = Path(__file__).resolve().parent / "incidents.db"


def current_timestamp():
    """Return the current local date and time."""
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


@contextmanager
def get_connection():
    """Open and safely close a SQLite connection."""
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    """Create all PulseOps database tables if they do not exist."""
    with get_connection() as connection:

        # Incident history
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                failure_type TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                recovery_attempts INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'OPEN',
                resolved_at TEXT,
                details TEXT
            )
        """)

        # Latest monitoring state
        connection.execute("""
            CREATE TABLE IF NOT EXISTS monitor_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                service TEXT NOT NULL,
                status TEXT NOT NULL,
                health TEXT NOT NULL,
                consecutive_failures INTEGER NOT NULL,
                cpu REAL NOT NULL,
                memory REAL NOT NULL,
                disk REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Historical resource measurements
        connection.execute("""
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                measured_at TEXT NOT NULL,
                status TEXT NOT NULL,
                cpu REAL NOT NULL,
                memory REAL NOT NULL,
                disk REAL NOT NULL
            )
        """)


def create_incident(service, failure_type, details=None):
    """Create an incident and return its database ID."""
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO incidents (
                service,
                failure_type,
                detected_at,
                recovery_attempts,
                status,
                details
            )
            VALUES (?, ?, ?, 0, 'OPEN', ?)
        """, (
            service,
            failure_type,
            current_timestamp(),
            details
        ))

        return cursor.lastrowid


def update_incident(
    incident_id,
    status,
    recovery_attempts=0,
    details=None
):
    """Update an incident with its latest recovery result."""
    allowed_statuses = {
        "OPEN",
        "RECOVERED",
        "UNRESOLVED"
    }

    if status not in allowed_statuses:
        raise ValueError(f"Invalid incident status: {status}")

    resolved_at = (
        current_timestamp()
        if status in {"RECOVERED", "UNRESOLVED"}
        else None
    )

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE incidents
            SET status = ?,
                recovery_attempts = ?,
                resolved_at = ?,
                details = COALESCE(?, details)
            WHERE id = ?
        """, (
            status,
            recovery_attempts,
            resolved_at,
            details,
            incident_id
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                f"Incident {incident_id} was not found."
            )


def get_recent_incidents(limit=10):
    """Return the most recent incidents as dictionaries."""
    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM incidents
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        incidents = [dict(row) for row in rows]

        for incident in incidents:
            incident["incident_code"] = (
                f"INC-{incident['id']:04d}"
            )

        return incidents


def save_monitor_state(
    status,
    health,
    consecutive_failures,
    cpu,
    memory,
    disk
):
    """Save the latest state and append a resource measurement."""
    measured_at = current_timestamp()

    with get_connection() as connection:
        # Insert the first state or update the existing state.
        connection.execute("""
            INSERT INTO monitor_state (
                id,
                service,
                status,
                health,
                consecutive_failures,
                cpu,
                memory,
                disk,
                updated_at
            )
            VALUES (1, 'DemoApp', ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                service = excluded.service,
                status = excluded.status,
                health = excluded.health,
                consecutive_failures =
                    excluded.consecutive_failures,
                cpu = excluded.cpu,
                memory = excluded.memory,
                disk = excluded.disk,
                updated_at = excluded.updated_at
        """, (
            status,
            health,
            consecutive_failures,
            cpu,
            memory,
            disk,
            measured_at
        ))

        # Preserve the measurement for historical charts.
        connection.execute("""
            INSERT INTO metrics_history (
                measured_at,
                status,
                cpu,
                memory,
                disk
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            measured_at,
            status,
            cpu,
            memory,
            disk
        ))


def get_monitor_state():
    """Return the latest monitoring state, or None if unavailable."""
    with get_connection() as connection:
        row = connection.execute("""
            SELECT *
            FROM monitor_state
            WHERE id = 1
        """).fetchone()

        return dict(row) if row else None


def get_recent_metrics(limit=30):
    """Return recent measurements in chronological order."""
    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT measured_at, status, cpu, memory, disk
            FROM metrics_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in reversed(rows)]
    
def get_incident_summary():
    """Return counts of all incidents by status."""
    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    SUM(CASE WHEN status = 'RECOVERED'
                        THEN 1 ELSE 0 END), 0
                ) AS recovered,
                COALESCE(
                    SUM(CASE WHEN status = 'UNRESOLVED'
                        THEN 1 ELSE 0 END), 0
                ) AS unresolved,
                COALESCE(
                    SUM(CASE WHEN status = 'OPEN'
                        THEN 1 ELSE 0 END), 0
                ) AS open
            FROM incidents
        """).fetchone()

        return dict(row)

