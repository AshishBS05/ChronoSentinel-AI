
import json
import re
import subprocess
from pathlib import Path

from event_schema import create_event
from storage.event_store import save_event_with_status

PROJECT_DIR = Path(__file__).resolve().parent.parent
EVENT_LOG = PROJECT_DIR / "logs" / "security_events.jsonl"
CONTAINER_NAME = "chronosentinel-waf"

ACCESS_LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<target>.*?) HTTP/(?P<version>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\S+) '
    r'"(?P<referer>[^"]*)" "(?P<agent>[^"]*)"'
)


def extract_modsecurity_event(record):
    transaction = record.get("transaction", {})
    request = transaction.get("request", {})
    response = transaction.get("response", {})
    messages = transaction.get("messages", [])

    rules = []
    for message in messages:
        details = message.get("details", {})
        rules.append({
            "rule_id": details.get("ruleId"),
            "message": message.get(
                "message", "Security rule matched"
            ),
            "severity": details.get("severity"),
        })

    blocked = bool(transaction.get("is_interrupted", False))
    status = response.get("http_code")

    return create_event(
        source="modsecurity",
        category="web_attack" if rules else "web_request",
        event_type="rule_match" if rules else "web_request",
        severity=(
            "high" if blocked
            else "medium" if rules
            else "low"
        ),
        source_ip=transaction.get("client_ip"),
        target=request.get("uri", ""),
        description="; ".join(
            rule["message"] for rule in rules
        ) or "ModSecurity transaction",
        blocked=blocked,
        evidence={
            "method": request.get("method"),
            "http_status": status,
            "rules": rules,
            "transaction_id": transaction.get("unique_id"),
        },
    )


def extract_access_event(line):
    match = ACCESS_LOG_PATTERN.match(line.strip())
    if not match:
        return None

    data = match.groupdict()
    status = int(data["status"])

    # ModSecurity audit records represent HTTP 403 blocks.
    if status == 403:
        return None

    return create_event(
        source="nginx_access",
        category="web_request",
        event_type="http_request_observed",
        severity="medium" if status >= 500 else "low",
        source_ip=data["ip"],
        target=data["target"],
        description=f"HTTP request observed with status {status}",
        blocked=False,
        evidence={
            "method": data["method"],
            "http_status": status,
            "response_bytes": data["size"],
            "user_agent": data["agent"],
            "referer": data["referer"],
            "access_log_timestamp": data["time"],
            "block_attribution": (
                "Not established by the access log alone"
            ),
        },
    )


def save_normalized_event(event):
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)

    # save_event returns (database ID, whether a new row was inserted).
    event_id, is_new = save_event_with_status(event)

    if not is_new:
        print(
            json.dumps({
                "database_id": event_id,
                "duplicate": True,
                "source": event.get("source"),
                "transaction_id": (
                    event.get("evidence", {}) or {}
                ).get("transaction_id"),
            }),
            flush=True,
        )
        return event_id

    # Write to JSONL only when SQLite inserted a new event.
    with EVENT_LOG.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {"database_id": event_id, **event},
            ensure_ascii=False,
        ),
        flush=True,
    )

    return event_id


def main():
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "docker",
        "logs",
        "--follow",
        "--since",
        "1s",
        CONTAINER_NAME,
    ]

    print("ChronoSentinel AI collector started.")
    print(f"Container: {CONTAINER_NAME}")
    print(f"JSONL log: {EVENT_LOG}")
    print("Collecting ModSecurity and normal HTTP requests.")
    print("Press Ctrl+C to stop.")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        bufsize=1,
    )

    try:
        for line in process.stdout:
            start = line.find('{"transaction":')

            if start != -1:
                try:
                    record = json.loads(line[start:])

                    if "transaction" in record:
                        event = extract_modsecurity_event(record)
                        save_normalized_event(event)

                except (
                    json.JSONDecodeError,
                    TypeError,
                    ValueError,
                ) as error:
                    print(
                        f"Could not parse audit event: {error}",
                        flush=True,
                    )

                continue

            event = extract_access_event(line)
            if event is not None:
                save_normalized_event(event)

    except KeyboardInterrupt:
        print("\nCollector stopped.")

    finally:
        if process.stdout:
            process.stdout.close()

        if process.poll() is None:
            process.terminate()

        process.wait()


if __name__ == "__main__":
    main()
