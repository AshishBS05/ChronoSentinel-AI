import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "chronosentinel.db"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "chronosentinel_anomaly.joblib"
MIN_TRAINING_EVENTS = 10


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def stable_number(value, buckets=100):
    raw = str(value or "unknown").encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16) % buckets


def features(event):
    try:
        evidence = json.loads(event.get("evidence_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        evidence = {}

    severity = {
        "low": 1, "info": 1, "informational": 1,
        "medium": 2, "moderate": 2,
        "high": 3, "critical": 4,
    }.get(str(event.get("severity", "")).lower(), 0)

    description = str(event.get("description") or "")
    source_ip = str(event.get("source_ip") or "")
    target = str(event.get("target") or "")

    return [
        severity,
        int(bool(event.get("blocked"))),
        len(description),
        len(json.dumps(evidence, default=str)),
        len(source_ip),
        len(target),
        stable_number(event.get("source")),
        stable_number(event.get("category")),
        stable_number(event.get("event_type")),
        min(len(evidence), 100),
        int(bool(evidence.get("transaction_id"))),
        int(bool(evidence.get("ports"))),
        int(bool(evidence.get("rules"))),
    ]


def initialize():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ml_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL UNIQUE,
                anomaly_score REAL NOT NULL,
                anomaly INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES security_events(id)
            )
        """)


def load_events(limit=5000):
    with connect() as conn:
        return [dict(row) for row in conn.execute("""
            SELECT id, timestamp, source, category, event_type,
                   severity, source_ip, target, description,
                   blocked, evidence_json
            FROM security_events
            ORDER BY id DESC LIMIT ?
        """, (max(1, min(int(limit), 50000)),)).fetchall()]


def train(limit=5000):
    events = load_events(limit)
    if len(events) < MIN_TRAINING_EVENTS:
        print(
            f"Not enough events to train yet: {len(events)} found; "
            f"need at least {MIN_TRAINING_EVENTS}."
        )
        print("The engine is installed. Collect more genuine events, then retry.")
        return False

    X = np.asarray([features(e) for e in events], dtype=float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42,
    )
    model.fit(X_scaled)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "scaler": scaler,
        "feature_version": 1,
        "training_rows": len(events),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }, MODEL_PATH)

    print(f"Model saved: {MODEL_PATH}")
    print(f"Events used for unsupervised training: {len(events)}")
    print("This is anomaly detection, not labelled attack-classification accuracy.")
    return True


def score(limit=500):
    if not MODEL_PATH.exists():
        print("No trained model exists yet. Run: python scripts/chronosentinel_ml.py train")
        return

    bundle = joblib.load(MODEL_PATH)
    model, scaler = bundle["model"], bundle["scaler"]
    events = load_events(limit)

    if not events:
        print("No security events are available to score.")
        return

    X = scaler.transform(np.asarray([features(e) for e in events], dtype=float))
    # IsolationForest decision_function: lower values are more anomalous.
    raw_scores = model.decision_function(X)
    predictions = model.predict(X)

    now = datetime.now(timezone.utc).isoformat()
    initialize()

    with connect() as conn:
        for event, raw, pred in zip(events, raw_scores, predictions):
            # Higher displayed score means more anomalous.
            anomaly_score = float(np.clip(0.5 - raw, 0.0, 1.0))
            conn.execute("""
                INSERT INTO ml_predictions
                    (event_id, anomaly_score, anomaly, model_name, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    anomaly_score=excluded.anomaly_score,
                    anomaly=excluded.anomaly,
                    model_name=excluded.model_name,
                    created_at=excluded.created_at
            """, (
                event["id"], anomaly_score, int(pred == -1),
                "IsolationForest", now,
            ))

    anomalies = [
        (e, float(s)) for e, s, p in zip(events, raw_scores, predictions)
        if p == -1
    ]
    print(f"Events scored: {len(events)}")
    print(f"Events flagged as anomalous: {len(anomalies)}")
    print("These are anomaly flags, not proof of malicious activity.")

    for event, raw in anomalies[:20]:
        score_value = float(np.clip(0.5 - raw, 0.0, 1.0))
        print(
            f"  Event #{event['id']} | {event['severity']} | "
            f"{event['event_type']} | anomaly score={score_value:.3f}"
        )


def status():
    initialize()
    with connect() as conn:
        event_count = conn.execute(
            "SELECT COUNT(*) FROM security_events"
        ).fetchone()[0]
        prediction_count = conn.execute(
            "SELECT COUNT(*) FROM ml_predictions"
        ).fetchone()[0]
        anomaly_count = conn.execute(
            "SELECT COUNT(*) FROM ml_predictions WHERE anomaly=1"
        ).fetchone()[0]

    print(f"Security events: {event_count}")
    print(f"ML predictions stored: {prediction_count}")
    print(f"Anomalies flagged: {anomaly_count}")
    print(f"Model file exists: {MODEL_PATH.exists()}")
    if MODEL_PATH.exists():
        bundle = joblib.load(MODEL_PATH)
        print(f"Training events: {bundle['training_rows']}")
        print(f"Trained at: {bundle['trained_at']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ChronoSentinel AI ML engine")
    parser.add_argument("action", choices=["train", "score", "run", "status"])
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    initialize()
    if args.action == "train":
        train(args.limit)
    elif args.action == "score":
        score(min(args.limit, 5000))
    elif args.action == "run":
        if train(args.limit):
            score(min(args.limit, 5000))
    else:
        status()
