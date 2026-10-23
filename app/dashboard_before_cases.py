import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "chronosentinel.db"

st.set_page_config(
    page_title="ChronoSentinel AI | Security Operations Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #0a111d; color: #e7eef8; }
    [data-testid="stSidebar"] { background: #0d1725; border-right: 1px solid #243348; }
    [data-testid="stSidebar"] * { color: #dbe7f6; }
    .block-container { padding-top: 1rem; padding-bottom: 1.5rem; max-width: 1750px; }
    .topbar { display:flex; align-items:center; justify-content:space-between; gap:1rem;
              padding: 0.25rem 0 1rem; border-bottom:1px solid #243348; margin-bottom:1rem; }
    .brand { font-size:1.45rem; font-weight:750; color:#eef5ff; letter-spacing:.1px; }
    .muted { color:#93a8c2; font-size:.86rem; }
    .status { display:inline-block; border:1px solid #275b4a; color:#80e0b4; background:#10271f;
              border-radius:18px; padding:5px 10px; font-size:.78rem; margin-left:5px; }
    .alert { border:1px solid #8c3544; border-radius:9px; padding:16px 18px; margin: 0 0 14px;
             background:linear-gradient(110deg,#2b1822,#171827); }
    .alert-label { color:#ff7e8b; font-weight:750; font-size:.76rem; letter-spacing:.6px; }
    .alert-title { color:#f4f7fb; font-size:1.2rem; font-weight:750; margin-top:6px; }
    .panel { background:#101b2a; border:1px solid #25364b; border-radius:8px; padding:12px 14px; margin-bottom:9px; }
    .panel-title { font-size:1rem; font-weight:700; color:#e7eef8; }
    .panel-sub { color:#93a8c2; font-size:.82rem; margin-top:3px; }
    .metric { background:#101b2a; border:1px solid #25364b; border-radius:8px; padding:12px 14px; min-height:92px; }
    .metric-label { color:#9cb3ce; font-size:.8rem; }
    .metric-value { color:#f1f6ff; font-size:1.85rem; font-weight:750; line-height:1.4; }
    .severity { display:inline-block; border-radius:4px; padding:2px 7px; font-size:.78rem; font-weight:700; }
    div[data-testid="stDataFrame"] { border:1px solid #25364b; border-radius:7px; }
    hr { border-color:#25364b; }
    </style>
    """,
    unsafe_allow_html=True,
)


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_case_tables():
    with connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS incident_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS analyst_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                action TEXT NOT NULL,
                outcome TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL
            )
            """
        )


def load_events(limit=1000):
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM security_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for row in rows:
        event = dict(row)
        event["blocked"] = bool(event.get("blocked"))
        try:
            event["evidence"] = json.loads(event.pop("evidence_json", "{}") or "{}")
        except (TypeError, json.JSONDecodeError):
            event["evidence"] = {}
            event.pop("evidence_json", None)
        result.append(event)
    return result


def load_cases():
    with connect() as con:
        rows = con.execute("SELECT * FROM incident_cases ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def load_audit():
    with connect() as con:
        rows = con.execute("SELECT * FROM analyst_audit ORDER BY id DESC LIMIT 500").fetchall()
    return [dict(r) for r in rows]


def log_audit(event_id, action, outcome, notes=""):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        con.execute(
            "INSERT INTO analyst_audit(event_id, action, outcome, notes, timestamp) VALUES(?,?,?,?,?)",
            (event_id, action, outcome, notes, now),
        )


def severity_name(value):
    value = str(value or "unknown").strip().lower()
    return {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low", "info": "Info"}.get(value, value.title())


def event_title(event):
    return str(event.get("event_type") or "Security event").replace("_", " ").title()


def is_attack(event):
    text = " ".join(
        str(event.get(k) or "") for k in ("category", "event_type", "description")
    ).lower()
    return (
        event.get("category") in ("web_attack", "network_attack")
        or any(term in text for term in ("attack", "scan", "injection", "xss", "brute", "rule_match"))
    )


def recommendations(event):
    category = str(event.get("category") or "").lower()
    title = str(event.get("event_type") or "").lower()
    blocked = bool(event.get("blocked"))
    advice = []
    if blocked:
        advice.append("The stored event records a block. Verify the response status and review nearby events for repeat attempts.")
    else:
        advice.append("No successful block is recorded for this event. Treat it as detected/observed, not contained.")
    if "web" in category or "xss" in title or "injection" in title or "rule_match" in title:
        advice += [
            "Review the matched WAF rule and request evidence; validate server-side input handling and output encoding.",
            "Keep OWASP CRS rules updated and test any rule exclusions before deploying them.",
        ]
    elif "network" in category or "scan" in title:
        advice += [
            "Correlate with firewall or flow telemetry before attributing the source.",
            "Check whether the destination ports are expected and review nearby events from the same source.",
            "Consider network ACLs or rate controls only after validating the source and business impact.",
        ]
    else:
        advice.append("Correlate this event with related logs before taking containment action.")
    return advice


def make_case(event_id):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        existing = con.execute(
            "SELECT id FROM incident_cases WHERE event_id=? AND status IN ('Open','Investigating')",
            (event_id,),
        ).fetchone()
        if existing:
            return False
        con.execute(
            "INSERT INTO incident_cases(event_id,status,notes,created_at,updated_at) VALUES(?,?,?,?,?)",
            (event_id, "Open", "", now, now),
        )
    log_audit(event_id, "Create incident case", "Recorded", "Case linked to stored event.")
    return True


def update_case(case_id, status, notes):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        con.execute(
            "UPDATE incident_cases SET status=?, notes=?, updated_at=? WHERE id=?",
            (status, notes, now, case_id),
        )
        row = con.execute("SELECT event_id FROM incident_cases WHERE id=?", (case_id,)).fetchone()
    log_audit(row["event_id"] if row else None, "Update incident case", "Recorded", f"Status set to {status}.")


def panel(title, subtitle=""):
    st.markdown(
        f'<div class="panel"><div class="panel-title">{title}</div><div class="panel-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


ensure_case_tables()
db_error = False
try:
    events = load_events()
    cases = load_cases()
    audit = load_audit()
except sqlite3.Error as exc:
    db_error = True
    events, cases, audit = [], [], []
    st.error(f"Database could not be read: {exc}")

df = pd.DataFrame(events)
if df.empty:
    df = pd.DataFrame(columns=[
        "id", "timestamp", "source", "category", "event_type", "severity",
        "source_ip", "target", "description", "blocked",
    ])
df["severity_display"] = df["severity"].apply(severity_name) if "severity" in df.columns else pd.Series(dtype=str)

with st.sidebar:
    st.markdown("## 🛡️ ChronoSentinel AI")
    st.caption("SECURITY OPERATIONS CENTER")
    page = st.radio(
        "Navigation",
        ["Dashboard", "Live Monitoring", "Incidents", "Threat Investigation", "Attack Analytics", "Logs & Events", "Actions & Audit", "Reports"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("DATA SOURCES")
    st.write("WAF · ModSecurity CRS")
    st.write("SQLite event store")
    st.caption(f"Database: {'Unavailable' if db_error else 'Connected'}")
    st.caption(f"Events loaded: {len(events)}")
    if st.button("Refresh data", use_container_width=True):
        st.rerun()

st.markdown(
    f"""
    <div class="topbar">
      <div><div class="brand">ChronoSentinel AI</div>
      <div class="muted">Security Operations Center · {page}</div></div>
      <div><span class="status">● WAF telemetry configured</span>
      <span class="status">● Database {'error' if db_error else 'connected'}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if page == "Dashboard":
    attacks = [e for e in events if is_attack(e)]
    blocked = [e for e in events if e.get("blocked")]
    serious = [e for e in events if severity_name(e.get("severity")) in ("High", "Critical")]
    open_cases = [c for c in cases if c.get("status") in ("Open", "Investigating")]
    alert = next((e for e in events if is_attack(e) or e.get("blocked")), None)

    if alert:
        response = "BLOCKED BY WAF" if alert.get("blocked") else "BLOCK NOT CONFIRMED"
        st.markdown(
            f"""
            <div class="alert">
              <div class="alert-label">LATEST RECORDED SECURITY ALERT · EVENT #{alert.get('id')}</div>
              <div class="alert-title">{event_title(alert)}</div>
              <div style="margin-top:8px;color:#d4deeb">
                Source: <b>{alert.get('source_ip') or 'Not recorded'}</b>
                &nbsp; | &nbsp; Severity: <b>{severity_name(alert.get('severity'))}</b>
                &nbsp; | &nbsp; Response: <b>{response}</b>
              </div>
              <div class="muted" style="margin-top:6px">{alert.get('description') or 'No description recorded'} · {alert.get('timestamp') or 'Timestamp unavailable'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No attack-related event has been recorded yet.")

    metrics = [
        ("TOTAL EVENTS", len(events)),
        ("ATTACK-RELATED", len(attacks)),
        ("BLOCKED", len(blocked)),
        ("HIGH / CRITICAL", len(serious)),
        ("OPEN CASES", len(open_cases)),
    ]
    cols = st.columns(5)
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### Security operations")
    left, right = st.columns([1.7, 1], gap="medium")
    with left:
        panel("Active alerts & recent events", "Newest recorded events first · select an event to investigate")
        if events:
            table = [{
                "ID": e.get("id"),
                "Time (UTC)": str(e.get("timestamp") or "")[:19].replace("T", " "),
                "Severity": severity_name(e.get("severity")),
                "Event": event_title(e),
                "Source IP": e.get("source_ip") or "—",
                "Status": "BLOCKED" if e.get("blocked") else "OBSERVED",
            } for e in events[:12]]
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True, height=270)
            choices = {
                f"#{e.get('id')} · {severity_name(e.get('severity'))} · {event_title(e)} · {e.get('source_ip') or 'IP unknown'}": e
                for e in events
            }
            selected_label = st.selectbox("Investigate event", list(choices.keys()), key="dashboard_event_choice")
            selected = choices[selected_label]
            with st.expander("Selected event · evidence and recommended response", expanded=True):
                a, b = st.columns(2)
                with a:
                    st.write(f"**Event:** {event_title(selected)}")
                    st.write(f"**Severity:** {severity_name(selected.get('severity'))}")
                    st.write(f"**Source IP:** {selected.get('source_ip') or 'Not recorded'}")
                    st.write(f"**Target:** {selected.get('target') or 'Not recorded'}")
                    st.write(f"**Response:** {'Blocked by WAF (recorded)' if selected.get('blocked') else 'Blocking not confirmed'}")
                    st.write(f"**Detection source:** {selected.get('source') or 'Unknown'}")
                with b:
                    st.markdown("**Recommended analyst actions**")
                    for rec in recommendations(selected):
                        st.markdown(f"- {rec}")
                with st.expander("Raw recorded evidence"):
                    st.json(selected.get("evidence") or {})
        else:
            st.info("No stored events yet. Start the collector and send a request through the local WAF.")
    with right:
        panel("Severity distribution", "Based on stored events")
        if not df.empty:
            counts = df["severity_display"].value_counts().reindex(["Critical", "High", "Medium", "Low", "Info"], fill_value=0)
            counts = counts[counts > 0].rename_axis("Severity").reset_index(name="Events")
            st.dataframe(counts, use_container_width=True, hide_index=True, height=190)
        else:
            st.caption("No severity data recorded.")
        panel("Event sources", "Recorded telemetry sources")
        if not df.empty:
            source_counts = df["source"].fillna("unknown").value_counts().rename_axis("Event source").reset_index(name="Events")
            st.dataframe(source_counts, use_container_width=True, hide_index=True, height=170)
        else:
            st.caption("No source data recorded.")
        panel("Incident workflow", "Local case and audit records")
        st.metric("Open / investigating cases", len(open_cases))
        st.metric("Total incident cases", len(cases))
        st.metric("Analyst audit actions", len(audit))
        st.caption("Dashboard actions are logged locally. Automatic IP blocking is not enabled.")

elif page == "Live Monitoring":
    st.subheader("Live monitoring")
    st.caption("This view displays recorded events. Use Refresh data to reload SQLite; continuous telemetry depends on the collector.")
    c1, c2, c3 = st.columns(3)
    with c1:
        severities = st.multiselect("Severity", ["Critical", "High", "Medium", "Low", "Info"], default=["Critical", "High", "Medium", "Low", "Info"])
    with c2:
        response_filter = st.selectbox("Response status", ["All", "Blocked", "Observed / not confirmed blocked"])
    with c3:
        search = st.text_input("Search event, source IP, target")
    filtered = [e for e in events if severity_name(e.get("severity")) in severities]
    if response_filter == "Blocked":
        filtered = [e for e in filtered if e.get("blocked")]
    elif response_filter == "Observed / not confirmed blocked":
        filtered = [e for e in filtered if not e.get("blocked")]
    if search:
        query = search.lower()
        filtered = [e for e in filtered if query in " ".join(str(e.get(k) or "") for k in ("source_ip", "target", "description", "event_type", "source")).lower()]
    st.dataframe(pd.DataFrame([{
        "ID": e.get("id"), "Timestamp": e.get("timestamp"), "Severity": severity_name(e.get("severity")),
        "Event": event_title(e), "Source IP": e.get("source_ip"), "Target": e.get("target"),
        "Status": "BLOCKED" if e.get("blocked") else "OBSERVED / NOT CONFIRMED BLOCKED",
        "Description": e.get("description"),
    } for e in filtered]), use_container_width=True, hide_index=True)

elif page in ("Incidents", "Threat Investigation"):
    st.subheader("Incident queue" if page == "Incidents" else "Threat investigation")
    st.caption("Cases are analyst-managed records. An observed IP does not establish a person's identity.")
    if not events:
        st.info("No events available to investigate.")
    else:
        choices = {f"#{e.get('id')} · {severity_name(e.get('severity'))} · {event_title(e)} · {e.get('source_ip') or 'IP unknown'}": e for e in events}
        label = st.selectbox("Select recorded event", list(choices.keys()), key="investigation_event_choice")
        event = choices[label]
        case = next((c for c in cases if int(c["event_id"]) == int(event["id"]) and c.get("status") in ("Open", "Investigating")), None)
        a, b, c = st.columns(3)
        a.metric("Severity", severity_name(event.get("severity")))
        b.metric("WAF response recorded", "Blocked" if event.get("blocked") else "Not confirmed")
        c.metric("Source IP", event.get("source_ip") or "Not recorded")
        panel("Trigger & event details", "Recorded telemetry only")
        st.write(f"**Event:** {event_title(event)}")
        st.write(f"**Category:** {event.get('category') or 'Not classified'} · **Source system:** {event.get('source') or 'Unknown'}")
        st.write(f"**Timestamp:** {event.get('timestamp') or 'Not recorded'}")
        st.write(f"**Target/request:** `{event.get('target') or 'Not recorded'}`")
        st.write(f"**Description:** {event.get('description') or 'No description recorded'}")
        with st.expander("Matched rules and raw evidence", expanded=True):
            st.json(event.get("evidence") or {})
        panel("Recommended analyst actions", "Suggestions only; no automatic remediation is executed")
        for rec in recommendations(event):
            st.markdown(f"- {rec}")
        if not case:
            if st.button("Create incident case", type="primary"):
                if make_case(int(event["id"])):
                    st.success("Incident case created and audit entry recorded.")
                else:
                    st.info("An open case already exists for this event.")
                st.rerun()
        else:
            st.success(f"Open case #{case['id']} · Status: {case['status']}")
            new_status = st.selectbox("Case status", ["Open", "Investigating", "Resolved"], index=["Open", "Investigating", "Resolved"].index(case["status"]) if case["status"] in ["Open", "Investigating", "Resolved"] else 0)
            notes = st.text_area("Analyst notes", value=case.get("notes", ""))
            if st.button("Save case updates"):
                update_case(case["id"], new_status, notes)
                st.success("Case updated and audit entry recorded.")
                st.rerun()
        st.warning("Attribution, geolocation, reputation, and MITRE ATT&CK mapping are not inferred without supporting telemetry.")

elif page == "Attack Analytics":
    st.subheader("Attack analytics")
    st.caption("Charts summarize recorded events only; these counts are not a forecast of all network traffic.")
    if df.empty:
        st.info("No events available for analytics.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            panel("Events by severity")
            s = df["severity_display"].value_counts().rename_axis("Severity").reset_index(name="Events")
            st.bar_chart(s.set_index("Severity"))
        with c2:
            panel("Events by source")
            s = df["source"].fillna("unknown").value_counts().rename_axis("Source").reset_index(name="Events")
            st.bar_chart(s.set_index("Source"))
        st.write("**Event categories**")
        st.dataframe(df["category"].fillna("unknown").value_counts().rename_axis("Category").reset_index(name="Events"), use_container_width=True, hide_index=True)

elif page == "Logs & Events":
    st.subheader("Logs & events")
    c1, c2, c3 = st.columns(3)
    with c1:
        sev = st.multiselect("Severity filter", ["Critical", "High", "Medium", "Low", "Info"], default=["Critical", "High", "Medium", "Low", "Info"])
    with c2:
        source = st.selectbox("Source filter", ["All"] + sorted({str(e.get("source") or "unknown") for e in events}))
    with c3:
        query = st.text_input("Search logs")
    filtered = [e for e in events if severity_name(e.get("severity")) in sev]
    if source != "All":
        filtered = [e for e in filtered if str(e.get("source") or "unknown") == source]
    if query:
        q = query.lower()
        filtered = [e for e in filtered if q in json.dumps(e, default=str).lower()]
    st.dataframe(pd.DataFrame([{
        "ID": e.get("id"), "Timestamp": e.get("timestamp"), "Source": e.get("source"),
        "Category": e.get("category"), "Event": event_title(e), "Severity": severity_name(e.get("severity")),
        "Source IP": e.get("source_ip"), "Target": e.get("target"), "Blocked": e.get("blocked"),
        "Description": e.get("description"),
    } for e in filtered]), use_container_width=True, hide_index=True)
    if filtered:
        event = st.selectbox("Inspect raw event", filtered, format_func=lambda e: f"#{e.get('id')} · {event_title(e)}")
        with st.expander("Raw event JSON", expanded=True):
            st.json(event)

elif page == "Actions & Audit":
    st.subheader("Actions & audit")
    st.caption("Audit records show dashboard case-management actions; they do not mean a firewall block occurred.")
    if audit:
        st.dataframe(pd.DataFrame(audit), use_container_width=True, hide_index=True)
    else:
        st.info("No analyst audit actions recorded yet.")
    st.markdown("### Incident cases")
    if cases:
        st.dataframe(pd.DataFrame(cases), use_container_width=True, hide_index=True)
    else:
        st.info("No incident cases created yet.")

elif page == "Reports":
    st.subheader("Logs & reports")
    st.caption("Exports contain records currently stored in the local SQLite database.")
    if events:
        export_df = pd.DataFrame([{
            "id": e.get("id"), "timestamp": e.get("timestamp"), "source": e.get("source"),
            "category": e.get("category"), "event_type": e.get("event_type"),
            "severity": severity_name(e.get("severity")), "source_ip": e.get("source_ip"),
            "target": e.get("target"), "description": e.get("description"),
            "blocked": e.get("blocked"), "evidence": json.dumps(e.get("evidence") or {}),
        } for e in events])
        st.download_button("Export events as CSV", export_df.to_csv(index=False), "chronosentinel_events.csv", "text/csv")
        st.download_button("Export events as JSON", json.dumps(events, indent=2, default=str), "chronosentinel_events.json", "application/json")
    else:
        st.info("No events available to export.")
    if cases:
        st.download_button("Export incident cases as CSV", pd.DataFrame(cases).to_csv(index=False), "chronosentinel_cases.csv", "text/csv")
