
import json
import sqlite3
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_DIR / "data" / "chronosentinel.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_ip TEXT,
                target TEXT,
                description TEXT,
                blocked INTEGER NOT NULL DEFAULT 0,
                evidence_json TEXT NOT NULL DEFAULT '{}'
            )
        """)


def save_event_with_status(
    event: dict[str, Any],
) -> tuple[int, bool]:
    """Return (database ID, whether a new row was inserted)."""
    required = (
        "timestamp",
        "source",
        "category",
        "event_type",
        "severity",
    )

    missing = [key for key in required if not event.get(key)]
    if missing:
        raise ValueError(f"Missing required event fields: {missing}")

    initialize_database()

    evidence = event.get("evidence", {}) or {}
    transaction_id = evidence.get("transaction_id")

    with get_connection() as connection:
        if event.get("source") == "modsecurity" and transaction_id:
            rows = connection.execute("""
                SELECT id, evidence_json
                FROM security_events
                WHERE source = 'modsecurity'
            """).fetchall()

            for row in rows:
                try:
                    existing_evidence = json.loads(
                        row["evidence_json"] or "{}"
                    )
                except (json.JSONDecodeError, TypeError):
                    continue

                if existing_evidence.get("transaction_id") == transaction_id:
                    return int(row["id"]), False

        cursor = connection.execute("""
            INSERT INTO security_events (
                timestamp, source, category, event_type,
                severity, source_ip, target, description,
                blocked, evidence_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["timestamp"],
            event["source"],
            event["category"],
            event["event_type"],
            event["severity"],
            event.get("source_ip"),
            event.get("target"),
            event.get("description", ""),
            int(bool(event.get("blocked", False))),
            json.dumps(evidence, ensure_ascii=False),
        ))

        return int(cursor.lastrowid), True


def save_event(event: dict[str, Any]) -> int:
    """Save an event and return its database ID."""
    event_id, _is_new = save_event_with_status(event)
    return event_id


def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    initialize_database()
    limit = max(1, min(int(limit), 500))

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM security_events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    events = []
    for row in rows:
        event = dict(row)
        event["blocked"] = bool(event["blocked"])
        event["evidence"] = json.loads(
            event.pop("evidence_json") or "{}"
        )
        events.append(event)

    return events
