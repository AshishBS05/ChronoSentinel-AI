import sqlite3
import time
import traceback
from pathlib import Path

from app.ml.engine import score, initialize

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "chronosentinel.db"
INTERVAL = 10

def count_unscored():
    with sqlite3.connect(DB) as con:
        return con.execute("""
            SELECT COUNT(*)
            FROM security_events e
            LEFT JOIN ml_predictions p ON p.event_id = e.id
            WHERE p.event_id IS NULL
        """).fetchone()[0]

def main():
    initialize()
    print("ChronoSentinel real-time ML worker started.", flush=True)
    print("Polling for unscored events every 10 seconds.", flush=True)
    print("Stop with Ctrl+C.", flush=True)

    while True:
        try:
            pending = count_unscored()
            if pending:
                print(f"Found {pending} unscored events; running anomaly scoring.", flush=True)
                # The existing engine scores the most recent events and upserts
                # predictions by event_id. Limit matches the engine's safe cap.
                score(min(max(pending, 50), 5000))
            else:
                print("No new events to score.", flush=True)
        except KeyboardInterrupt:
            raise
        except Exception:
            traceback.print_exc()

        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nReal-time ML worker stopped.", flush=True)
