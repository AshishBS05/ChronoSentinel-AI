from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parent
# When this file is copied to ~/ChronoSentinel-AI/app/dashboard.py, this resolves
# to ~/ChronoSentinel-AI/data/chronosentinel.db.
DB_PATH = PROJECT_DIR.parent / "data" / "chronosentinel.db"

st.set_page_config(page_title="ChronoSentinel AI | Security Operations", page_icon="🛡️", layout="wide")

CSS = """
<style>
:root { --bg:#0b1220; --panel:#111b2b; --panel2:#0e1726; --line:#26354a; --muted:#9aabc0; --text:#e7eef8; }
.stApp { background: #0a111d; color: var(--text); }
[data-testid="stHeader"] { background: rgba(10,17,29,.96); }
[data-testid="stSidebar"] { background:#0d1624; border-right:1px solid #26354a; }
[data-testid="stSidebar"] * { color:#dbe6f5; }
.block-container { padding-top:.55rem; padding-bottom:1rem; max-width:1800px; }
h1,h2,h3 { letter-spacing:-.02em; }
.small-muted { color:#9aabc0; font-size:.82rem; }
.topline { display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #26354a; padding:0 0 14px 0; margin-bottom:16px; }
.brand { font-size:1.35rem; font-weight:700; color:#f1f6ff; }
.brand-sub { color:#9aabc0; font-size:.78rem; margin-top:2px; }
.status { display:inline-block; padding:5px 9px; border:1px solid #285a50; border-radius:16px; color:#75e0b1; background:#0e2927; font-size:.78rem; margin-left:6px; }
.panel { background:#101a29; border:1px solid #26354a; border-radius:7px; padding:10px 12px; margin-bottom:8px; }
.alert-panel { background:linear-gradient(100deg,#32171e,#171725); border:1px solid #963744; border-radius:8px; padding:16px 18px; margin:8px 0 16px 0; }
.alert-title { color:#ff7a86; font-size:.76rem; font-weight:700; letter-spacing:.06em; }
.alert-main { font-size:1.08rem; font-weight:650; margin-top:5px; }
.metric { background:#101a29; border:1px solid #26354a; border-radius:7px; padding:10px 12px; min-height:88px; }
.metric-label { color:#9aabc0; font-size:.82rem; }
.metric-value { color:#eef5ff; font-size:1.8rem; font-weight:700; line-height:1.5; }
.metric-note { color:#9aabc0; font-size:.76rem; }
.sev { display:inline-block; padding:3px 8px; border-radius:4px; font-size:.75rem; font-weight:700; border:1px solid transparent; }
.sev-critical { background:#4b1720; color:#ff9aa5; border-color:#8e2b3b; }
.sev-high { background:#4a2020; color:#ffb0a5; border-color:#8d3b35; }
.sev-medium { background:#4a3518; color:#ffd08a; border-color:#85602b; }
.sev-low { background:#173a31; color:#8fe0be; border-color:#286e59; }
hr { border-color:#26354a; }
[data-testid="stDataFrame"] { border:1px solid #26354a; border-radius:6px; }
button[kind="primary"] { background:#1769d2; border:1px solid #287ee5; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_case_tables():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incident_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'Open',
                assigned_to TEXT,
                analyst_notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES security_events(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS action_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                outcome TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                actor TEXT NOT NULL DEFAULT 'Analyst',
                timestamp TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES security_events(id)
            )
        """)


def load_events(limit=1000):
    try:
        with connect() as conn:
            rows = conn.execute("""
                SELECT id, timestamp, source, category, event_type, severity,
                       source_ip, target, description, blocked, evidence_json
                FROM security_events ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
        data = []
        for row in rows:
            item = dict(row)
            item["blocked"] = bool(item.get("blocked"))
            try:
                item["evidence"] = json.loads(item.pop("evidence_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                item["evidence"] = {}
                item.pop("evidence_json", None)
            data.append(item)
        return data, None
    except sqlite3.Error as exc:
        return [], str(exc)


def load_cases():
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT c.*, e.timestamp, e.source, e.category, e.event_type, e.severity,
                   e.source_ip, e.target, e.description, e.blocked, e.evidence_json
            FROM incident_cases c JOIN security_events e ON e.id=c.event_id
            ORDER BY c.updated_at DESC
        """).fetchall()]


def load_audit():
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM action_audit ORDER BY id DESC LIMIT 500").fetchall()]


def severity_name(value):
    value = str(value or "low").lower()
    return {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low", "info": "Low"}.get(value, value.title())


def recommendations(event):
    category = str(event.get("category", "")).lower()
    etype = str(event.get("event_type", "")).lower()
    blocked = bool(event.get("blocked"))
    recs = []
    if "web_attack" in category or any(x in etype for x in ("xss", "sql", "injection", "traversal")):
        recs += ["Review the matched WAF rule and preserve the raw request evidence.",
                 "Keep OWASP CRS and the WAF image updated; verify rules in a staging environment.",
                 "Validate input and apply context-appropriate output encoding in the protected application."]
    elif "network" in category or "port_scan" in etype:
        recs += ["Correlate with firewall or flow telemetry before attributing the source.",
                 "Check whether the destination ports are expected; review nearby events from the same source.",
                 "Apply network ACLs or rate controls only after validating the source and business impact."]
    else:
        recs += ["Review surrounding events and source context before escalating.",
                 "Confirm the relevant service, account or asset owner and preserve supporting logs."]
    if blocked:
        recs.insert(0, "WAF block is recorded for this event; verify the response code and rule evidence.")
    else:
        recs.insert(0, "No successful block is recorded for this event. Treat it as detected/observed, not contained.")
    recs.append("Do not block an IP automatically based on a single alert; validate attribution and operational impact first.")
    return recs


def create_case(event_id):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO incident_cases(event_id,status,created_at,updated_at) VALUES(?,?,?,?)",
                     (event_id, "Open", now, now))


def update_case(case_id, status, notes):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("UPDATE incident_cases SET status=?, analyst_notes=?, updated_at=? WHERE id=?",
                     (status, notes, now, case_id))


def record_audit(event_id, action, outcome, notes):
    with connect() as conn:
        conn.execute("INSERT INTO action_audit(event_id,action,outcome,notes,actor,timestamp) VALUES(?,?,?,?,?,?)",
                     (event_id, action, outcome, notes, "Analyst", datetime.now(timezone.utc).isoformat()))


init_case_tables()
events, db_error = load_events()
# Build a consistent dataframe for dashboard tables and analytics.
df = pd.DataFrame(events)
if df.empty:
    df = pd.DataFrame(columns=[
        "id", "timestamp", "source", "category", "event_type",
        "severity", "source_ip", "target", "description", "blocked"
    ])
df["severity_display"] = df["severity"].apply(severity_name) if "severity" in df.columns else pd.Series(dtype=str)
cases = load_cases()
audit = load_audit()

with st.sidebar:
    st.markdown("## 🛡️ ChronoSentinel AI")
    st.caption("Security Operations Center")
    page = st.radio("Navigation", ["Dashboard", "Live Monitoring", "Incidents", "Threat Investigation", "Attack Analytics", "Logs & Events", "Actions & Audit", "Reports"], label_visibility="collapsed")
    st.divider()
    st.caption("DATA SOURCES")
    st.write("WAF · ModSecurity CRS")
    st.write("SQLite event store")
    st.caption(f"Database: {'Connected' if not db_error else 'Unavailable'}")
    st.caption(f"Events loaded: {len(events)}")
    if st.button("Refresh data", use_container_width=True):
        st.rerun()

st.markdown(f"""<div class="topline"><div><div class="brand">ChronoSentinel AI</div><div class="brand-sub">Security Operations Center · {page}</div></div><div><span class="status">● WAF telemetry configured</span><span class="status">● Database {'connected' if not db_error else 'error'}</span></div></div>""", unsafe_allow_html=True)
if page == "Dashboard":
    attacks = [e for e in events if e.get("category") in ("web_attack", "network_attack") or any(
        word in str(e.get("event_type", "")).lower()
        for word in ("attack", "scan", "injection", "xss", "brute")
    )]
    blocked_events = [e for e in events if e.get("blocked")]
    high_critical = [e for e in events if severity_name(e.get("severity")) in ("Critical", "High")]
    source_ips = {e.get("source_ip") for e in events if e.get("source_ip")}
    latest_alert = next((e for e in events if e.get("blocked") or e.get("category") in ("web_attack", "network_attack")), None)

    # Alert banner uses the latest relevant recorded event; no synthetic alert data.
    if latest_alert:
        title = str(latest_alert.get("event_type") or "Security event").replace("_", " ").title()
        status = "BLOCKED BY WAF" if latest_alert.get("blocked") else "NOT CONFIRMED BLOCKED"
        st.markdown(
            f"""<div class="alert-panel">
            <div class="alert-title">LATEST SECURITY ALERT · RECORDED EVENT #{latest_alert.get('id')}</div>
            <div class="alert-main">{title}</div>
            <div style="margin-top:7px;color:#d4deeb">
            Source: <b>{latest_alert.get('source_ip') or 'Not recorded'}</b>
            &nbsp; | &nbsp; Severity: <b>{severity_name(latest_alert.get('severity'))}</b>
            &nbsp; | &nbsp; Response: <b>{status}</b></div>
            <div class="small-muted" style="margin-top:6px">{latest_alert.get('description') or 'No description recorded'} · {latest_alert.get('timestamp') or 'Timestamp unavailable'}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("No attack-related event has been recorded yet. The dashboard will display an alert here when telemetry is stored.")

    # Compact operational KPI row, all derived from SQLite.
    metric_cols = st.columns(5)
    metrics = [
        ("Total events", len(events), "Stored in event database"),
        ("Attack-related", len(attacks), "Classified from recorded events"),
        ("Blocked", len(blocked_events), "blocked=true in stored event"),
        ("High / Critical", len(high_critical), "Stored severity values"),
        ("Observed sources", len(source_ips), "Distinct source IP values"),
    ]
    for col, (label, value, note) in zip(metric_cols, metrics):
        with col:
            st.markdown(
                f'<div class="metric"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### Security operations")
    left, right = st.columns([1.6, 1], gap="medium")
    with left:
        st.markdown('<div class="panel"><strong>Active alerts & recent events</strong><div class="small-muted">Newest recorded events first · select an event to investigate below</div></div>', unsafe_allow_html=True)
        if not df.empty:
            alert_rows = []
            for e in events[:12]:
                alert_rows.append({
                    "ID": e.get("id"),
                    "Time (UTC)": str(e.get("timestamp") or "")[:19].replace("T", " "),
                    "Severity": severity_name(e.get("severity")),
                    "Alert / event": str(e.get("event_type") or "event").replace("_", " ").title(),
                    "Source IP": e.get("source_ip") or "—",
                    "Response": "BLOCKED" if e.get("blocked") else "OBSERVED",
                })
            st.dataframe(pd.DataFrame(alert_rows), use_container_width=True, hide_index=True, height=345)
            event_choices = {
                f"#{e['id']} · {severity_name(e.get('severity'))} · {str(e.get('event_type') or 'event').replace('_',' ')} · {e.get('source_ip') or 'source unknown'}": e
                for e in events
            }
            chosen_label = st.selectbox("Investigate recorded event", list(event_choices.keys()), key="dashboard_investigate_event")
            chosen_event = event_choices[chosen_label]
            with st.expander("Selected event · evidence and recommended response", expanded=True):
                detail_left, detail_right = st.columns([1.2, 1])
                with detail_left:
                    st.write(f"**Event:** {str(chosen_event.get('event_type') or 'Unknown').replace('_',' ').title()}")
                    st.write(f"**Severity:** {severity_name(chosen_event.get('severity'))}")
                    st.write(f"**Source IP:** {chosen_event.get('source_ip') or 'Not recorded'}")
                    st.write(f"**Target:** `{chosen_event.get('target') or 'Not recorded'}`")
                    st.write(f"**Response:** {'Blocked by WAF (stored evidence)' if chosen_event.get('blocked') else 'Not confirmed blocked'}")
                    st.write(chosen_event.get("description") or "No description recorded.")
                with detail_right:
                    st.markdown("**Recommended analyst actions**")
                    for recommendation in recommendations(chosen_event)[:4]:
                        st.markdown(f"- {recommendation}")
                with st.expander("Raw recorded evidence"):
                    st.json(chosen_event.get("evidence") or {})
        else:
            st.caption("Waiting for recorded events. Start the collector and send requests through the WAF.")

    with right:
        st.markdown('<div class="panel"><strong>Alert severity</strong><div class="small-muted">Distribution of stored events</div></div>', unsafe_allow_html=True)
        if not df.empty:
            severity_counts = df["severity_display"].value_counts().reindex(["Critical", "High", "Medium", "Low"], fill_value=0)
            severity_counts = severity_counts[severity_counts > 0]
            if not severity_counts.empty:
                st.bar_chart(severity_counts, height=180)
        else:
            st.caption("No severity data yet.")

        st.markdown('<div class="panel"><strong>Event sources</strong><div class="small-muted">Recorded telemetry source</div></div>', unsafe_allow_html=True)
        if not df.empty:
            source_counts = df["source"].fillna("unknown").value_counts()
            st.bar_chart(source_counts, height=160)
        else:
            st.caption("No source data yet.")

        st.markdown('<div class="panel"><strong>Incident workflow</strong></div>', unsafe_allow_html=True)
        st.write(f"**Open cases:** {sum(1 for c in cases if c.get('status') in ('Open', 'Investigating'))}")
        st.write(f"**All cases:** {len(cases)}")
        st.write(f"**Analyst audit actions:** {len(audit)}")
        st.caption("Cases and analyst actions are stored locally. WAF/network response actions are not executed from this dashboard.")

    st.caption("All metrics and visualizations use stored events. Source IPs identify observed network endpoints, not necessarily individual people.")

elif page == "Live Monitoring":
    st.subheader("Live monitoring")
    st.caption("This page refreshes when you select Refresh data. Continuous auto-refresh depends on the installed Streamlit refresh component.")
    c1, c2, c3 = st.columns(3)
    with c1: sev_filter = st.multiselect("Severity", ["Critical", "High", "Medium", "Low"], default=["Critical", "High", "Medium", "Low"])
    with c2: status_filter = st.selectbox("Response", ["All", "Blocked", "Observed / not confirmed blocked"])
    with c3: search = st.text_input("Search source, target or description")
    filtered = [e for e in events if severity_name(e.get("severity")) in sev_filter]
    if status_filter == "Blocked": filtered = [e for e in filtered if e.get("blocked")]
    if status_filter == "Observed / not confirmed blocked": filtered = [e for e in filtered if not e.get("blocked")]
    if search:
        q = search.lower(); filtered = [e for e in filtered if q in " ".join(str(e.get(k) or "") for k in ("source_ip", "target", "description", "event_type")).lower()]
    st.dataframe(pd.DataFrame([{"ID":e.get("id"),"Timestamp":e.get("timestamp"),"Severity":severity_name(e.get("severity")),"Type":e.get("event_type"),"Source IP":e.get("source_ip"),"Target":e.get("target"),"Status":"BLOCKED" if e.get("blocked") else "OBSERVED / NOT CONFIRMED BLOCKED","Description":e.get("description")} for e in filtered]), use_container_width=True, hide_index=True)

elif page in ("Incidents", "Threat Investigation"):
    st.subheader("Incident investigation" if page == "Threat Investigation" else "Incident queue")
    st.caption("An incident case is an analyst-managed record linked to a stored event. Creating a case does not mean the source has been attributed to a person.")
    if not events:
        st.info("No events available to investigate yet.")
    else:
        options = {f"#{e['id']} · {severity_name(e.get('severity'))} · {e.get('event_type')} · {e.get('source_ip') or 'IP unknown'}": e for e in events}
        selected_label = st.selectbox("Select recorded event", list(options.keys()))
        event = options[selected_label]
        event_id = int(event["id"])
        case = next((c for c in cases if int(c["event_id"]) == event_id), None)
        a, b, c = st.columns([1, 1, 1])
        a.metric("Severity", severity_name(event.get("severity")))
        b.metric("WAF response recorded", "Blocked" if event.get("blocked") else "Not confirmed")
        c.metric("Source IP", event.get("source_ip") or "Not recorded")
        st.markdown("### Trigger and evidence")
        st.write(f"**Event:** {str(event.get('event_type') or 'Unknown').replace('_',' ').title()}")
        st.write(f"**Category:** {event.get('category') or 'Not classified'} · **Source system:** {event.get('source') or 'Unknown'}")
        st.write(f"**Timestamp:** {event.get('timestamp') or 'Not recorded'}")
        st.write(f"**Target/request:** `{event.get('target') or 'Not recorded'}`")
        st.write(f"**Description:** {event.get('description') or 'No description recorded'}")
        with st.expander("Matched rules and raw evidence", expanded=True):
            st.json(event.get("evidence") or {})
        st.markdown("### Recommended analyst actions")
        for i, rec in enumerate(recommendations(event), 1):
            st.write(f"{i}. {rec}")
        st.warning("Attribution, geolocation, reputation, and MITRE ATT&CK mapping are not inferred unless supporting telemetry is available. No automatic IP blocking is performed by this dashboard.")
        if not case:
            if st.button("Create incident case for this event", type="primary"):
                create_case(event_id)
                record_audit(event_id, "Create incident case", "Recorded", "Analyst created a case linked to this event.")
                st.success("Incident case created.")
                st.rerun()
        else:
            st.markdown("### Case management")
            with st.form(f"case_form_{case['id']}"):
                status = st.selectbox("Status", ["Open", "Investigating", "Contained", "Resolved", "Closed"], index=["Open", "Investigating", "Contained", "Resolved", "Closed"].index(case["status"]) if case["status"] in ["Open", "Investigating", "Contained", "Resolved", "Closed"] else 0)
                notes = st.text_area("Analyst notes", value=case.get("analyst_notes", ""), height=100)
                save = st.form_submit_button("Save case update", type="primary")
            if save:
                update_case(case["id"], status, notes)
                record_audit(event_id, "Update incident case", "Recorded", f"Status set to {status}; analyst notes updated.")
                st.success("Case update saved to the audit log.")
                st.rerun()
    if page == "Incidents":
        st.markdown("### Existing cases")
        cases = load_cases()
        if cases:
            st.dataframe(pd.DataFrame([{"Case ID":c["id"],"Event ID":c["event_id"],"Status":c["status"],"Severity":severity_name(c["severity"]),"Event":c["event_type"],"Source IP":c["source_ip"],"Updated":c["updated_at"]} for c in cases]), use_container_width=True, hide_index=True)
        else:
            st.caption("No incident cases have been created yet.")

elif page == "Attack Analytics":
    st.subheader("Attack analytics")
    st.caption("Analytics are calculated from the events currently stored. They are not a full network-wide view unless network telemetry is connected.")
    if not df.empty:
        left, right = st.columns(2)
        with left:
            st.markdown("#### Event types")
            st.bar_chart(df["event_type"].fillna("unknown").value_counts())
        with right:
            st.markdown("#### Observed source IPs")
            src = df["source_ip"].fillna("not recorded").value_counts().head(10)
            st.bar_chart(src)
        st.markdown("#### Event timeline")
        timeline = df.copy()
        timeline["parsed_time"] = pd.to_datetime(timeline["timestamp"], errors="coerce", utc=True)
        timeline = timeline.dropna(subset=["parsed_time"]).set_index("parsed_time").resample("h").size().rename("Events")
        if not timeline.empty: st.line_chart(timeline)
    else:
        st.info("No data to analyze yet.")

elif page == "Logs & Events":
    st.subheader("Logs & events")
    st.caption("Stored normalized event records. Raw evidence is available by selecting a row below.")
    q = st.text_input("Search all visible event fields")
    view = events
    if q:
        needle = q.lower()
        view = [e for e in events if needle in json.dumps(e, ensure_ascii=False).lower()]
    st.dataframe(pd.DataFrame([{"ID":e.get("id"),"Timestamp":e.get("timestamp"),"Source":e.get("source"),"Category":e.get("category"),"Type":e.get("event_type"),"Severity":severity_name(e.get("severity")),"Source IP":e.get("source_ip"),"Target":e.get("target"),"Blocked":e.get("blocked"),"Description":e.get("description")} for e in view]), use_container_width=True, hide_index=True)
    if view:
        chosen_id = st.selectbox("Inspect event ID", [e["id"] for e in view])
        chosen = next(e for e in view if e["id"] == chosen_id)
        st.json(chosen)
        st.download_button("Export selected event JSON", json.dumps(chosen, indent=2, ensure_ascii=False), file_name=f"chronosentinel_event_{chosen_id}.json", mime="application/json")

elif page == "Actions & Audit":
    st.subheader("Actions and audit history")
    st.caption("This log records analyst case-management actions in this dashboard. It does not claim to have blocked an IP or changed a firewall unless an external response integration confirms that action.")
    if audit:
        st.dataframe(pd.DataFrame([{"Audit ID":a["id"],"Event ID":a["event_id"],"Action":a["action"],"Outcome":a["outcome"],"Notes":a["notes"],"Actor":a["actor"],"Timestamp":a["timestamp"]} for a in audit]), use_container_width=True, hide_index=True)
    else:
        st.info("No analyst actions recorded yet. Create or update an incident case to create an audit entry.")

elif page == "Reports":
    st.subheader("Reports")
    st.caption("Export data from the current local event store. Counts represent stored events only.")
    st.write(f"**Events:** {len(events)} · **Incident cases:** {len(cases)} · **Audit actions:** {len(audit)}")
    if events:
        export = [{k:v for k,v in e.items()} for e in events]
        st.download_button("Export events as JSON", json.dumps(export, indent=2, ensure_ascii=False), file_name="chronosentinel_events.json", mime="application/json", type="primary")
        export_df = pd.DataFrame([{k:e.get(k) for k in ["id","timestamp","source","category","event_type","severity","source_ip","target","description","blocked"]} for e in events])
        st.download_button("Export events as CSV", export_df.to_csv(index=False), file_name="chronosentinel_events.csv", mime="text/csv")
    else:
        st.info("No events are available to export.")

st.markdown("<div class='small-muted' style='border-top:1px solid #26354a;padding-top:12px;margin-top:22px'>ChronoSentinel AI · Local lab build · Decisions and attribution require evidence · Dashboard actions are audited</div>", unsafe_allow_html=True)
