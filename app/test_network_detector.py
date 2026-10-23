from app.detectors.network_detector import detect_port_scan
from app.storage.event_store import save_event, get_recent_events
# Synthetic test data only; this is not live network traffic.
records = [
    {
        "source_ip": "192.0.2.10",
        "destination_port": port,
    }
    for port in range(20, 32)
]

alerts = detect_port_scan(records)

if not alerts:
    raise SystemExit("No alert generated; check detector threshold.")

for alert in alerts:
    event_id = save_event(alert)
    print(f"Saved network alert with database ID: {event_id}")
    print("Event:", alert)

print("\nLatest database events:")
for event in get_recent_events(5):
    print(event)
