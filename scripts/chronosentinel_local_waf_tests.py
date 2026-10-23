#!/usr/bin/env python3
"""
ChronoSentinel AI — local WAF validation harness.

Safety guard:
- Sends test requests ONLY to localhost:8080 (the user's local Docker WAF).
- Does not exploit a real target, write files, execute commands, or access databases.
- A test is considered blocked only when the HTTP response status is 403.
- Other statuses are reported as observed, not automatically called a detection.
"""

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import csv
import os

BASE_URL = "http://localhost:8080"
OUTPUT_CSV = "local_waf_test_results.csv"

TESTS = [
    {
        "category": "XSS",
        "name": "XSS script-tag pattern",
        "path": "/",
        "params": {"testparam": "<script>alert(1)</script>"},
        "headers": {},
    },
    {
        "category": "SQL injection",
        "name": "SQLi boolean-pattern probe",
        "path": "/",
        "params": {"id": "1' OR '1'='1"},
        "headers": {},
    },
    {
        "category": "Path traversal",
        "name": "Traversal path pattern",
        "path": "/",
        "params": {"file": "../../etc/passwd"},
        "headers": {},
    },
    {
        "category": "Command injection",
        "name": "Shell metacharacter pattern",
        "path": "/",
        "params": {"cmd": "127.0.0.1; id"},
        "headers": {},
    },
    {
        "category": "File inclusion",
        "name": "Local file inclusion pattern",
        "path": "/",
        "params": {"page": "file:///etc/passwd"},
        "headers": {},
    },
    {
        "category": "Scanner-like request",
        "name": "Common sensitive-path probe",
        "path": "/.env",
        "params": {},
        "headers": {"User-Agent": "ChronoSentinel-Local-Test/1.0"},
    },
    {
        "category": "Scanner-like request",
        "name": "Common admin-path probe",
        "path": "/wp-admin/",
        "params": {},
        "headers": {"User-Agent": "ChronoSentinel-Local-Test/1.0"},
    },
    {
        "category": "Request anomaly",
        "name": "Unusual encoded traversal pattern",
        "path": "/",
        "params": {"path": "%2e%2e/%2e%2e/etc/passwd"},
        "headers": {},
    },
]


def send_test(test):
    query = urlencode(test["params"])
    url = BASE_URL + test["path"]
    if query:
        url += "?" + query

    request = Request(url, headers=test["headers"], method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            status = response.status
            result = "BLOCKED" if status == 403 else (
                "SERVER_ERROR" if status >= 500 else "NOT_BLOCKED"
            )
            return status, result, ""
    except HTTPError as exc:
        status = exc.code
        result = "BLOCKED" if status == 403 else (
            "SERVER_ERROR" if status >= 500 else "HTTP_ERROR_NOT_403"
        )
        return status, result, ""
    except URLError as exc:
        return "", "CONNECTION_ERROR", str(exc.reason)
    except TimeoutError:
        return "", "TIMEOUT", "Request timed out"


def main():
    # Hard safety guard: do not allow a command-line or environment override.
    if BASE_URL != "http://localhost:8080":
        raise SystemExit("Safety check failed: target must be the local WAF.")

    rows = []
    print("ChronoSentinel AI — local WAF validation")
    print(f"Target: {BASE_URL}")
    print("Only requests to the local Docker WAF will be sent.\n")

    for index, test in enumerate(TESTS, start=1):
        status, result, note = send_test(test)
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "category": test["category"],
            "test_name": test["name"],
            "http_status": status,
            "result": result,
            "note": note,
        }
        rows.append(row)
        status_text = status if status != "" else "no response"
        print(
            f"{index:02d}. [{test['category']}] {test['name']}: "
            f"HTTP {status_text} — {result}"
        )
        if note:
            print(f"    Note: {note}")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    blocked = sum(row["result"] == "BLOCKED" for row in rows)
    print(f"\nFinished: {len(rows)} tests; {blocked} returned HTTP 403.")
    print(f"Results saved to: {os.path.abspath(OUTPUT_CSV)}")
    print(
        "Interpretation: HTTP 403 means the WAF blocked that request. "
        "Other responses are not counted as blocked. Check the WAF audit "
        "logs and ChronoSentinel event store to verify which requests were "
        "actually logged and ingested."
    )


if __name__ == "__main__":
    main()


