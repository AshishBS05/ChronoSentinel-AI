
from collections import defaultdict
from datetime import datetime, timezone


def detect_port_scan(
    connection_records: list[dict],
    unique_port_threshold: int = 10,
) -> list[dict]:
    """Flag sources contacting many distinct destination ports.

    Expected record fields:
      source_ip, destination_port, timestamp (optional)
    """

    ports_by_source = defaultdict(set)
    latest_time = {}

    for record in connection_records:
        source_ip = record.get("source_ip")
        destination_port = record.get("destination_port")

        if not source_ip or not isinstance(destination_port, int):
            continue

        if not 1 <= destination_port <= 65535:
            continue

        ports_by_source[source_ip].add(destination_port)
        latest_time[source_ip] = record.get("timestamp") or (
            datetime.now(timezone.utc).isoformat()
        )

    alerts = []

    for source_ip, ports in ports_by_source.items():
        if len(ports) >= unique_port_threshold:
            alerts.append({
                "timestamp": latest_time[source_ip],
                "source": "network_detector",
                "category": "network_attack",
                "event_type": "possible_port_scan",
                "severity": "medium",
                "source_ip": source_ip,
                "target": None,
                "description": (
                    f"Observed connections to {len(ports)} "
                    "distinct destination ports"
                ),
                "blocked": False,
                "evidence": {
                    "unique_destination_ports": len(ports),
                    "ports": sorted(ports),
                },
            })

    return alerts
