"""Explainable, rule-based analysis of recorded security event sequences."""
from collections import Counter
import pandas as pd

SEVERITY_RANK = {
    "info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4
}

def analyze_source(events):
    """Analyze already-recorded events; does not perform live prediction or blocking."""
    usable = [dict(e) for e in events if e.get("source_ip")]
    for e in usable:
        e["_time"] = pd.to_datetime(e.get("timestamp"), utc=True, errors="coerce")
        e["_severity"] = str(e.get("severity") or "info").lower()
    usable = [e for e in usable if pd.notna(e["_time"])]

    usable.sort(key=lambda e: e["_time"])
    grouped = {}
    for event in usable:
        grouped.setdefault(str(event["source_ip"]), []).append(event)

    results = []
    for ip, sequence in grouped.items():
        types = Counter(
            str(e.get("event_type") or e.get("category") or "unknown")
            for e in sequence
        )
        ranks = [SEVERITY_RANK.get(e["_severity"], 0) for e in sequence]
        max_rank = max(ranks, default=0)
        high_count = sum(r >= 3 for r in ranks)
        blocked_count = sum(bool(e.get("blocked")) for e in sequence)
        repeated = [name for name, count in types.items() if count >= 3]
        escalating = len(ranks) >= 2 and ranks[-1] > ranks[0]

        signals = []
        recommendations = []
        if len(sequence) >= 5:
            signals.append("Repeated activity: 5 or more recorded events")
            recommendations.append(
                "Review the source's event timeline and consider approved rate limits."
            )
        if repeated:
            signals.append("Repeated event types: " + ", ".join(repeated[:4]))
            recommendations.append(
                "Inspect matching WAF rules and verify whether the repeated requests are legitimate."
            )
        if escalating:
            signals.append("Severity increased across the recorded sequence")
            recommendations.append(
                "Prioritize analyst review and correlate the latest event with related incidents."
            )
        if high_count:
            signals.append(f"{high_count} high/critical event(s) recorded")
            recommendations.append(
                "Review evidence and confirm the recorded WAF response before taking action."
            )
        if blocked_count:
            signals.append(f"{blocked_count} event(s) recorded as blocked")
        if not recommendations:
            recommendations.append(
                "Continue monitoring; current recorded evidence does not establish a clear escalation pattern."
            )

        results.append({
            "Source IP": ip,
            "Recorded events": len(sequence),
            "Distinct event types": len(types),
            "High/Critical": high_count,
            "Recorded blocks": blocked_count,
            "First seen": sequence[0]["_time"].isoformat(),
            "Last seen": sequence[-1]["_time"].isoformat(),
            "Signals": signals,
            "Recommendations": recommendations,
            "_sequence": sequence,
        })

    return sorted(
        results,
        key=lambda r: (
            r["High/Critical"], r["Recorded events"], r["Distinct event types"]
        ),
        reverse=True,
    )
