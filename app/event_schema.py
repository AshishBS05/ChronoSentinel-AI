
from datetime import datetime, timezone
from typing import Any


def create_event(
    source: str,
    category: str,
    event_type: str,
    severity: str,
    source_ip: str | None = None,
    target: str | None = None,
    description: str = "",
    blocked: bool = False,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a normalized ChronoSentinel AI security event."""

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "category": category,
        "event_type": event_type,
        "severity": severity.lower(),
        "source_ip": source_ip,
        "target": target,
        "description": description,
        "blocked": blocked,
        "evidence": evidence or {},
    }
