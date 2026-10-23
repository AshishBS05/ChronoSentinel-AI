import re
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
:root {
    --cs-bg: #0b0f17;
    --cs-sidebar: #0d121c;
    --cs-panel: #111925;
    --cs-panel-hover: #151f2e;
    --cs-border: #202b3b;
    --cs-text: #e7edf7;
    --cs-muted: #8794a8;
    --cs-blue: #4f83f1;
    --cs-blue-soft: #172744;
    --cs-cyan: #58c7e8;
}

.stApp {
    background: var(--cs-bg) !important;
    color: var(--cs-text);
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: var(--cs-bg) !important;
}

[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 1540px !important;
    padding: 2.2rem 2.6rem 3rem !important;
    overflow: visible !important;
}

[data-testid="stHeader"] {
    background: rgba(11, 15, 23, 0.92) !important;
    height: 0 !important;
    min-height: 0 !important;
}

#MainMenu, footer {
    visibility: hidden;
}

/* ---------------- SIDEBAR ---------------- */

[data-testid="stSidebar"] {
    background: var(--cs-sidebar) !important;
    border-right: 1px solid #1d2736 !important;
    min-width: 238px !important;
    max-width: 238px !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 1.15rem 0.85rem 1rem !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    margin-bottom: 0.25rem;
}

.cs-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 7px 19px;
}

.cs-logo-mark {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 9px;
    background: #315ce8;
    color: #fff;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: -0.5px;
    box-shadow: 0 3px 12px rgba(49, 92, 232, 0.20);
}

.cs-logo-name {
    color: #f0f4fb;
    font-size: 13px;
    font-weight: 650;
    letter-spacing: -0.25px;
}

.cs-logo-sub {
    color: #748197;
    font-size: 8px;
    letter-spacing: 1.35px;
    margin-top: 3px;
}

.cs-section-label {
    color: #77849a;
    font-size: 9px;
    font-weight: 650;
    letter-spacing: 1.15px;
    padding: 13px 9px 6px;
}

[data-testid="stSidebar"] [data-testid="stButton"] {
    margin: 0 !important;
    padding: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] button {
    min-height: 34px !important;
    height: 34px !important;
    padding: 0 10px !important;
    margin: 1px 0 !important;
    border: 1px solid transparent !important;
    border-radius: 7px !important;
    background: transparent !important;
    color: #aab5c6 !important;
    box-shadow: none !important;
    font-size: 12px !important;
    font-weight: 450 !important;
    text-align: left !important;
    transition: background 120ms ease, color 120ms ease !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] button > div {
    justify-content: flex-start !important;
    gap: 9px !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] button p {
    font-size: 12px !important;
    line-height: 1.1 !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] button [data-testid="stIconMaterial"] {
    color: #8d9bb0 !important;
    font-size: 16px !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: #151e2b !important;
    color: #f2f6fc !important;
    border-color: #202d40 !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] button:focus:not(:active) {
    box-shadow: none !important;
}

/* The currently selected navigation item */
[data-testid="stSidebar"] .cs-nav-active button {
    background: #182743 !important;
    color: #e9f1ff !important;
    border: 1px solid #263d60 !important;
}

[data-testid="stSidebar"] .cs-nav-active button [data-testid="stIconMaterial"] {
    color: #76a5ff !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #7f8da2 !important;
    font-size: 10px !important;
}

[data-testid="stSidebar"] hr {
    border-color: #202a39 !important;
    margin: 15px 0 10px !important;
}

/* ---------------- TYPOGRAPHY ---------------- */

h1, h2, h3, h4 {
    color: #eef3fb !important;
    letter-spacing: -0.5px !important;
    font-weight: 650 !important;
}

h1 {
    font-size: 29px !important;
    line-height: 1.25 !important;
    margin-bottom: 0.35rem !important;
}

h2 {
    font-size: 22px !important;
    margin-top: 1.3rem !important;
}

h3 {
    font-size: 16px !important;
    margin-top: 1rem !important;
}

p, li {
    color: #b5c0d0;
}

[data-testid="stCaptionContainer"] {
    color: var(--cs-muted) !important;
}

/* ---------------- TOP BAR ---------------- */

.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding: 0 0 18px;
    margin: 0 0 23px;
    border-bottom: 1px solid var(--cs-border);
}

.brand {
    color: #eef3fb;
    font-size: 12px;
    font-weight: 650;
    letter-spacing: 0.1px;
}

.muted {
    color: var(--cs-muted);
    font-size: 11px;
}

.status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 9px;
    border: 1px solid #214537;
    border-radius: 20px;
    background: #10251f;
    color: #76d9aa;
    font-size: 10px;
    white-space: nowrap;
}

.status::before {
    content: "";
    width: 6px;
    height: 6px;
    background: #4dd49a;
    border-radius: 50%;
}

/* ---------------- CARDS / PANELS ---------------- */

.panel,
.metric {
    background: var(--cs-panel);
    border: 1px solid var(--cs-border);
    border-radius: 11px;
    padding: 17px 18px;
}

.panel {
    margin: 8px 0 14px;
}

.panel-title {
    color: #e8eef8;
    font-size: 13px;
    font-weight: 650;
}

.panel-sub {
    color: #8290a5;
    font-size: 11px;
    margin-top: 4px;
}

.metric {
    padding: 15px 16px;
    min-height: 104px;
}

.metric-label {
    color: #8997ac;
    font-size: 10px;
    letter-spacing: 0.55px;
    text-transform: uppercase;
}

.metric-value {
    color: #f0f5fc;
    font-size: 27px;
    line-height: 1.3;
    font-weight: 700;
    letter-spacing: -0.7px;
    margin-top: 9px;
}

.alert {
    background: #171c28;
    border: 1px solid #31364b;
    border-radius: 10px;
    padding: 14px 16px;
    margin: 8px 0 15px;
}

.alert-label {
    color: #f0b96b;
    font-size: 10px;
    font-weight: 650;
    letter-spacing: 0.7px;
    text-transform: uppercase;
}

.alert-title {
    color: #edf2fb;
    font-size: 14px;
    font-weight: 650;
    margin-top: 4px;
}

.severity {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 5px;
    background: #302024;
    color: #ff9eaa;
    font-size: 10px;
    font-weight: 650;
}

/* ---------------- INPUTS ---------------- */

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
    background: #101824 !important;
    color: #e6edf7 !important;
    border-color: #29364a !important;
    border-radius: 7px !important;
}

[data-testid="stSelectbox"] svg,
[data-testid="stMultiSelect"] svg {
    color: #95a4b9 !important;
}

[data-testid="stWidgetLabel"] p {
    color: #aab6c8 !important;
    font-size: 11px !important;
}

/* ---------------- BUTTONS ---------------- */

.stButton button,
.stDownloadButton button,
[data-testid="stFormSubmitButton"] button {
    border-radius: 7px !important;
    border: 1px solid #2a3a51 !important;
    background: #172337 !important;
    color: #e6eefb !important;
    font-size: 12px !important;
    font-weight: 550 !important;
    transition: all 120ms ease !important;
}

.stButton button:hover,
.stDownloadButton button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    border-color: #4b77cf !important;
    background: #1c2c45 !important;
    color: #fff !important;
}

.stButton button:focus,
.stDownloadButton button:focus {
    box-shadow: 0 0 0 1px #4f83f1 !important;
}

/* ---------------- DATA TABLES ---------------- */

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border: 1px solid var(--cs-border) !important;
    border-radius: 9px !important;
    overflow: hidden !important;
}

[data-testid="stDataFrame"] * {
    font-size: 11px;
}

[data-testid="stDataFrame"] [role="columnheader"] {
    background: #151e2c !important;
}

hr {
    border-color: var(--cs-border) !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--cs-border) !important;
    border-radius: 9px !important;
    background: #101722 !important;
}

[data-testid="stExpander"] summary {
    color: #dfe8f6 !important;
    font-size: 12px !important;
}

[data-testid="stTabs"] button {
    color: #9ba9bc !important;
    font-size: 12px !important;
}

[data-testid="stTabs"] button[aria-selected="true"] {
    color: #82aaff !important;
}

[data-testid="stAlert"] {
    border-radius: 9px !important;
}

@media (max-width: 900px) {
    [data-testid="stAppViewContainer"] .main .block-container {
        padding: 1.2rem 1rem 2rem !important;
    }
}
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
        # Migrate older local databases safely without deleting case history.
        existing_columns = {
            row[1] for row in con.execute("PRAGMA table_info(incident_cases)").fetchall()
        }
        if "notes" not in existing_columns:
            con.execute("ALTER TABLE incident_cases ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
        if "created_at" not in existing_columns:
            con.execute("ALTER TABLE incident_cases ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
        if "updated_at" not in existing_columns:
            con.execute("ALTER TABLE incident_cases ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")


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
    # Minimal product identity
    st.markdown(
        """
        <div class="cs-logo">
            <div class="cs-logo-mark">CS</div>
            <div>
                <div class="cs-logo-name">ChronoSentinel</div>
                <div class="cs-logo-sub">SECURITY OPERATIONS</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top-level destinations. Existing route names are preserved.
    nav_groups = [
        ("ANALYTICS", [
            ("Dashboard", "dashboard"),
            ("Live Monitoring", "sensors"),
            ("Threat Analytics", "query_stats"),
        ]),
        ("CONTENT", [
            ("Incidents", "crisis_alert"),
            ("Attack Classifier", "shield"),
        ]),
        ("CUSTOMIZATION", [
            ("Reports & Audit", "description"),
        ]),
    ]

    if "main_navigation" not in st.session_state:
        st.session_state["main_navigation"] = "Dashboard"

    nav_choice = st.session_state["main_navigation"]

    for group_label, group_items in nav_groups:
        st.markdown(
            f'<div class="cs-section-label">{group_label}</div>',
            unsafe_allow_html=True,
        )

        for label, icon_name in group_items:
            slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")

            # Keep the active destination visibly selected.
            active_class = (
                "cs-nav-active"
                if nav_choice == label
                else "cs-nav-inactive"
            )

            # Material icons are consistent, lightweight line-style icons.
            clicked = st.button(
                label,
                key=f"nav_{slug}",
                icon=f":material/{icon_name}:",
                use_container_width=True,
            )

            # Add a class to the selected button wrapper.
            st.markdown(
                f"""
                <style>
                [data-testid="stSidebar"] .st-key-nav_{slug} {{
                    border-radius: 7px;
                }}
                [data-testid="stSidebar"] .st-key-nav_{slug} button {{
                    {"background:#182743 !important;border:1px solid #263d60 !important;color:#e9f1ff !important;" if nav_choice == label else ""}
                }}
                [data-testid="stSidebar"] .st-key-nav_{slug} button [data-testid="stIconMaterial"] {{
                    {"color:#76a5ff !important;" if nav_choice == label else ""}
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )

            if clicked:
                st.session_state["main_navigation"] = label
                st.rerun()

    # Resolve the chosen top-level route.
    page = st.session_state["main_navigation"]

    # Keep the existing nested page destinations and routing.
    if page == "Incidents":
        incident_view = st.selectbox(
            "Incident workspace",
            ["Incident Queue", "Threat Investigation"],
            key="merged_section_page",
        )
        if incident_view == "Threat Investigation":
            page = "Threat Investigation"

    elif page == "Threat Analytics":
        analytics_view = st.selectbox(
            "Analytics workspace",
            ["Attack Analytics", "ML Anomaly Detection", "Cyber DNA"],
            key="merged_section_page",
        )
        page = analytics_view

    elif page == "Reports & Audit":
        reports_view = st.selectbox(
            "Reports workspace",
            ["Reports", "Logs & Events", "Actions & Audit"],
            key="merged_section_page",
        )
        page = reports_view

    elif page == "Attack Classifier":
        page = "Supervised Attack Classifier"

    st.divider()

    st.markdown(
        '<div class="cs-section-label">SYSTEM STATUS</div>',
        unsafe_allow_html=True,
    )
    st.caption("WAF · ModSecurity CRS")
    st.caption("SQLite event store")
    st.caption(f"Database: {'Unavailable' if db_error else 'Connected'}")
    st.caption(f"Events loaded: {len(events)}")

    if st.button(
        "Refresh data",
        key="nav_refresh_data",
        icon=":material/refresh:",
        use_container_width=True,
    ):
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
    c1, c2 = st.columns(2)
    with c1:
        severities = st.multiselect("Severity", ["Critical", "High", "Medium", "Low", "Info"], default=["Critical", "High", "Medium", "Low", "Info"])
    with c2:
        response_filter = st.selectbox("Response status", ["All", "Blocked", "Observed / not confirmed blocked"])
    filtered = [e for e in events if severity_name(e.get("severity")) in severities]
    if response_filter == "Blocked":
        filtered = [e for e in filtered if e.get("blocked")]
    elif response_filter == "Observed / not confirmed blocked":
        filtered = [e for e in filtered if not e.get("blocked")]
    st.dataframe(pd.DataFrame([{
        "ID": e.get("id"), "Timestamp": e.get("timestamp"), "Severity": severity_name(e.get("severity")),
        "Event": event_title(e), "Source IP": e.get("source_ip"), "Target": e.get("target"),
        "Status": "BLOCKED" if e.get("blocked") else "OBSERVED / NOT CONFIRMED BLOCKED",
        "Description": e.get("description"),
    } for e in filtered]), use_container_width=True, hide_index=True)

elif page == "Incidents":
    st.subheader("Incident queue" if page == "Incidents" else "Threat investigation")
    st.caption("Cases are analyst-managed records. An observed IP does not establish a person's identity.")

    # Complete incident queue: search/filter all cases, including resolved history.
    if page == "Incidents":
        st.markdown("### Incident case queue")
        if cases:
            event_by_id = {int(e["id"]): e for e in events if e.get("id") is not None}
            case_rows = []
            for item in cases:
                linked_event = event_by_id.get(int(item.get("event_id", -1)), {})
                case_rows.append({
                    "Case ID": item.get("id"),
                    "Event ID": item.get("event_id"),
                    "Severity": severity_name(linked_event.get("severity")),
                    "Event": event_title(linked_event) if linked_event else "Event unavailable",
                    "Source IP": linked_event.get("source_ip") or "Not recorded",
                    "Status": item.get("status") or "Open",
                    "Created (UTC)": item.get("created_at"),
                    "Last updated (UTC)": item.get("updated_at"),
                })

            case_df = pd.DataFrame(case_rows)
            case_status_filter = st.selectbox(
                "Filter by case status",
                ["All", "Open", "Investigating", "Resolved"],
                key="case_status_filter",
            )

            visible_cases = case_df.copy()
            if case_status_filter != "All":
                visible_cases = visible_cases[visible_cases["Status"] == case_status_filter]

            st.caption(f"Showing {len(visible_cases)} of {len(case_df)} incident case(s)")
            st.dataframe(visible_cases, use_container_width=True, hide_index=True)
            if visible_cases.empty:
                st.info("No cases match the selected status filter.")

            st.markdown("### Manage an existing case")
            case_lookup = {
                f"Case #{item.get('id')} · Event #{item.get('event_id')} · {item.get('status', 'Open')}": item
                for item in cases
            }
            selected_case_label = st.selectbox(
                "Select a case to update",
                list(case_lookup.keys()),
                key="manage_existing_case",
            )
            selected_case = case_lookup[selected_case_label]
            selected_case_event = event_by_id.get(int(selected_case.get("event_id", -1)), {})
            st.write(
                f"**Linked event:** {event_title(selected_case_event) if selected_case_event else 'Event unavailable'}"
                f" · **Severity:** {severity_name(selected_case_event.get('severity'))}"
                f" · **Source IP:** {selected_case_event.get('source_ip') or 'Not recorded'}"
            )
            allowed_statuses = ["Open", "Investigating", "Resolved"]
            current_status = selected_case.get("status") or "Open"
            if current_status not in allowed_statuses:
                current_status = "Open"
            new_case_status = st.selectbox(
                "Case status",
                allowed_statuses,
                index=allowed_statuses.index(current_status),
                key=f"case_status_{selected_case.get('id')}",
            )
            case_notes = st.text_area(
                "Analyst notes",
                value=selected_case.get("notes", "") or "",
                key=f"case_notes_{selected_case.get('id')}",
                help="Record investigation findings and the reason for resolving or reopening the case.",
            )
            if st.button("Save case updates", type="primary", key=f"save_case_{selected_case.get('id')}"):
                try:
                    update_case(int(selected_case["id"]), new_case_status, case_notes)
                    st.success(f"Case #{selected_case['id']} updated and audit entry recorded.")
                    st.rerun()
                except sqlite3.Error as exc:
                    st.error(f"Could not update the case: {exc}")
        else:
            st.info("No incident cases yet. Select an event below to create the first case.")

        st.divider()

    # Event investigation for incident triage.
    if not events:
        st.info("No events available to investigate.")
    else:
        choices = {
            f"#{e.get('id')} · {severity_name(e.get('severity'))} · {event_title(e)} · {e.get('source_ip') or 'IP unknown'}": e
            for e in events
        }
        label = st.selectbox(
            "Select recorded event to investigate",
            list(choices.keys()),
            key="investigation_event_choice",
        )
        event = choices[label]
        active_case = next(
            (
                item for item in cases
                if int(item.get("event_id", -1)) == int(event.get("id", -2))
                and item.get("status") in ("Open", "Investigating")
            ),
            None,
        )

        a, b, c = st.columns(3)
        a.metric("Severity", severity_name(event.get("severity")))
        b.metric("WAF response recorded", "Blocked" if event.get("blocked") else "Not confirmed")
        c.metric("Source IP", event.get("source_ip") or "Not recorded")

        panel("Trigger & event details", "Recorded telemetry only")
        st.write(f"**Event:** {event_title(event)}")
        st.write(f"**Category:** {event.get('category') or 'Not classified'} · **Source system:** {event.get('source') or 'Unknown'}")
        st.write(f"**Timestamp (UTC):** {event.get('timestamp') or 'Not recorded'}")
        st.write(f"**Target/request:** `{event.get('target') or 'Not recorded'}`")
        st.write(f"**Description:** {event.get('description') or 'No description recorded'}")
        with st.expander("Matched rules and raw evidence", expanded=False):
            st.json(event.get("evidence") or {})

        panel("Recommended analyst actions", "Suggestions only; no automatic remediation is executed")
        for rec in recommendations(event):
            st.markdown(f"- {rec}")

        if active_case:
            st.info(
                f"Active case #{active_case['id']} is linked to this event. "
                "Manage its status and notes in the incident case queue above."
            )
        else:
            resolved_case = next(
                (
                    item for item in cases
                    if int(item.get("event_id", -1)) == int(event.get("id", -2))
                    and item.get("status") == "Resolved"
                ),
                None,
            )
            if resolved_case:
                st.caption(
                    f"Resolved case #{resolved_case['id']} already exists for this event. "
                    "You can reopen it from Manage an existing case."
                )
            if st.button("Create incident case", type="primary", key="create_incident_case"):
                try:
                    if make_case(int(event["id"])):
                        st.success("Incident case created and audit entry recorded.")
                    else:
                        st.info("An open or investigating case already exists for this event.")
                    st.rerun()
                except sqlite3.Error as exc:
                    st.error(f"Could not create the incident case: {exc}")

        st.warning(
            "Attribution, geolocation, reputation, and MITRE ATT&CK mapping are not inferred "
            "without supporting telemetry."
        )

elif page == "Threat Investigation":
    st.subheader("Threat investigation")
    st.caption(
        "Investigate recorded telemetry, correlate related events, and document findings. "
        "Correlations are based only on fields present in the local event store."
    )

    if not events:
        st.info("No stored events are available. Start the collector and send a request through the local WAF.")
    else:
        # Investigation filters are applied to stored records only; they do not initiate scans.
        f1, f2 = st.columns(2)
        with f1:
            investigation_severities = st.multiselect(
                "Severity", ["Critical", "High", "Medium", "Low", "Info"],
                default=["Critical", "High", "Medium", "Low", "Info"],
                key="threat_severity_filter",
            )
        with f2:
            investigation_response = st.selectbox(
                "Recorded response", ["All", "Blocked", "Not confirmed blocked"],
                key="threat_response_filter",
            )
        filtered_events = [
            e for e in events if severity_name(e.get("severity")) in investigation_severities
        ]
        if investigation_response == "Blocked":
            filtered_events = [e for e in filtered_events if e.get("blocked")]
        elif investigation_response == "Not confirmed blocked":
            filtered_events = [e for e in filtered_events if not e.get("blocked")]
        st.caption(f"Showing {len(filtered_events)} of {len(events)} recorded event(s)")
        if not filtered_events:
            st.info("No events match these filters. Change a filter to see more events.")
        else:
            event_options = {
                f"#{e.get('id')} · {severity_name(e.get('severity'))} · {event_title(e)} · {e.get('source_ip') or 'IP not recorded'}": e
                for e in filtered_events
            }
            selected_label = st.selectbox(
                "Select event to investigate", list(event_options.keys()), key="threat_selected_event"
            )
            selected_event = event_options[selected_label]
            selected_id = int(selected_event.get("id", -1))
            source_ip = selected_event.get("source_ip")

            related_events = [
                e for e in events
                if e.get("source_ip") and source_ip and e.get("source_ip") == source_ip
            ]
            related_events.sort(key=lambda e: str(e.get("timestamp") or ""), reverse=True)
            linked_cases = [
                case_item for case_item in cases
                if int(case_item.get("event_id", -1)) == selected_id
            ]
            active_linked_cases = [
                c for c in linked_cases if c.get("status") in ("Open", "Investigating")
            ]
            high_related = sum(
                severity_name(e.get("severity")) in ("High", "Critical") for e in related_events
            )
            blocked_related = sum(bool(e.get("blocked")) for e in related_events)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Selected severity", severity_name(selected_event.get("severity")))
            m2.metric("Events with same source IP", len(related_events) if source_ip else "N/A")
            m3.metric("High / critical from source", high_related if source_ip else "N/A")
            m4.metric("Recorded blocks from source", blocked_related if source_ip else "N/A")

            if not source_ip:
                st.info("This event has no source IP. Source-based correlation is unavailable for this event.")
            else:
                st.caption(
                    f"Correlation key: source IP {source_ip}. This is a technical correlation only; "
                    "it does not identify a person or prove the events share a cause."
                )

            left, right = st.columns([1.2, 1], gap="large")
            with left:
                panel("Selected event", "Original stored event fields")
                st.write(f"**Event ID:** {selected_event.get('id')}")
                st.write(f"**Event type:** {event_title(selected_event)}")
                st.write(f"**Category:** {selected_event.get('category') or 'Not classified'}")
                st.write(f"**Detection source:** {selected_event.get('source') or 'Unknown'}")
                st.write(f"**Timestamp (UTC):** {selected_event.get('timestamp') or 'Not recorded'}")
                st.write(f"**Source IP:** {source_ip or 'Not recorded'}")
                st.write(f"**Target/request:** `{selected_event.get('target') or 'Not recorded'}`")
                st.write(f"**Response:** {'Blocked (recorded)' if selected_event.get('blocked') else 'Block not confirmed'}")
                st.write(f"**Description:** {selected_event.get('description') or 'No description recorded'}")
                with st.expander("Raw evidence and matched rules", expanded=True):
                    st.json(selected_event.get("evidence") or {})
                st.download_button(
                    "Download selected event JSON",
                    data=json.dumps(selected_event, indent=2, ensure_ascii=False, default=str),
                    file_name=f"chronosentinel_event_{selected_id}.json",
                    mime="application/json",
                    key=f"download_threat_event_{selected_id}",
                )

            with right:
                panel("Investigation findings", "Evidence-led recommendations; no automatic remediation")
                for recommendation in recommendations(selected_event):
                    st.markdown(f"- {recommendation}")
                if active_linked_cases:
                    for case_item in active_linked_cases:
                        st.info(
                            f"Active case #{case_item.get('id')} · {case_item.get('status')}. "
                            "Manage notes and status in the Incidents section."
                        )
                elif linked_cases:
                    st.caption(
                        "This event has prior case history: "
                        + ", ".join(f"#{c.get('id')} ({c.get('status')})" for c in linked_cases)
                    )
                else:
                    st.caption("No incident case is currently linked to this event.")

            st.markdown("### Related events from the same source IP")
            if source_ip and related_events:
                related_rows = [{
                    "Event ID": e.get("id"),
                    "Timestamp (UTC)": e.get("timestamp"),
                    "Severity": severity_name(e.get("severity")),
                    "Event": event_title(e),
                    "Category": e.get("category") or "Unknown",
                    "Target": e.get("target") or "Not recorded",
                    "Response": "BLOCKED" if e.get("blocked") else "NOT CONFIRMED",
                    "Selected": "Yes" if int(e.get("id", -2)) == selected_id else "",
                } for e in related_events]
                st.dataframe(pd.DataFrame(related_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No source-IP-related events can be shown for this selection.")

            st.markdown("### Investigation checklist")
            st.caption("Use this checklist as analyst guidance; checking an item does not change system controls.")
            c1, c2 = st.columns(2)
            with c1:
                st.checkbox("Review raw evidence and matched rules", key=f"threat_check_evidence_{selected_id}")
                st.checkbox("Compare nearby events and timestamps", key=f"threat_check_timeline_{selected_id}")
            with c2:
                st.checkbox("Verify whether the WAF response was recorded", key=f"threat_check_response_{selected_id}")
                st.checkbox("Document findings in the linked incident case", key=f"threat_check_notes_{selected_id}")

            st.warning(
                "No automatic blocking, attribution, geolocation, reputation lookup, or MITRE ATT&CK mapping "
                "is performed unless supporting telemetry or integrations are added."
            )

elif page == "Attack Analytics":
    st.subheader("Attack analytics")
    st.caption(
        "Explore trends and distributions in events stored by ChronoSentinel AI. "
        "Charts reflect recorded telemetry only, not all traffic on a network."
    )

    if not events:
        st.info("No recorded events are available yet. Generate approved lab traffic and refresh the data to populate analytics.")
    else:
        analytics_df = pd.DataFrame(events).copy()
        analytics_df["severity_display"] = analytics_df["severity"].apply(severity_name)
        analytics_df["source_display"] = analytics_df["source"].fillna("unknown").astype(str)
        analytics_df["category_display"] = analytics_df["category"].fillna("unknown").astype(str)
        analytics_df["event_display"] = analytics_df.apply(lambda row: event_title(row.to_dict()), axis=1)
        analytics_df["source_ip_display"] = analytics_df["source_ip"].fillna("Not recorded").astype(str)
        analytics_df["timestamp_parsed"] = pd.to_datetime(analytics_df["timestamp"], errors="coerce", utc=True)
        analytics_df["response_display"] = analytics_df["blocked"].apply(
            lambda value: "Blocked" if bool(value) else "Not confirmed blocked"
        )

        f1, f2, f3 = st.columns([1.2, 1.2, 1.3])
        with f1:
            selected_severities = st.multiselect(
                "Severity", ["Critical", "High", "Medium", "Low", "Info"],
                default=["Critical", "High", "Medium", "Low", "Info"],
                key="analytics_severity_filter",
            )
        with f2:
            source_options = sorted(analytics_df["source_display"].unique().tolist())
            selected_sources = st.multiselect(
                "Detection source", source_options, default=source_options,
                key="analytics_source_filter",
            )
        with f3:
            response_filter = st.selectbox(
                "Recorded response", ["All", "Blocked", "Not confirmed blocked"],
                key="analytics_response_filter",
            )
        filtered_df = analytics_df[
            analytics_df["severity_display"].isin(selected_severities)
            & analytics_df["source_display"].isin(selected_sources)
        ].copy()
        if response_filter != "All":
            filtered_df = filtered_df[filtered_df["response_display"] == response_filter]
        total_count = len(filtered_df)
        blocked_count = int(filtered_df["blocked"].fillna(False).astype(bool).sum())
        high_critical_count = int(filtered_df["severity_display"].isin(["High", "Critical"]).sum())
        distinct_sources = int(filtered_df.loc[filtered_df["source_ip"].notna() & (filtered_df["source_ip"].astype(str) != ""), "source_ip"].nunique())
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Events in current view", total_count)
        m2.metric("Recorded blocks", blocked_count)
        m3.metric("High / critical", high_critical_count)
        m4.metric("Distinct source IPs", distinct_sources)
        st.caption(f"Showing {total_count} of {len(analytics_df)} stored event(s). Empty or missing telemetry is not inferred.")

        if filtered_df.empty:
            st.warning("No events match the selected filters. Adjust the filters to see more events.")
        else:
            left, right = st.columns(2)
            with left:
                panel("Severity distribution", "Count of filtered recorded events")
                severity_order = ["Critical", "High", "Medium", "Low", "Info"]
                severity_counts = (
                    filtered_df["severity_display"].value_counts()
                    .reindex(severity_order, fill_value=0)
                )
                st.bar_chart(severity_counts[severity_counts > 0], use_container_width=True)
            with right:
                panel("Recorded response", "Blocked versus not confirmed blocked")
                response_counts = filtered_df["response_display"].value_counts()
                st.bar_chart(response_counts, use_container_width=True)

            left, right = st.columns(2)
            with left:
                panel("Events by detection source", "Source labels stored with each event")
                source_counts = filtered_df["source_display"].value_counts().rename_axis("Source").to_frame("Events")
                st.bar_chart(source_counts, use_container_width=True)
            with right:
                panel("Events by category", "Recorded event category")
                category_counts = filtered_df["category_display"].value_counts().rename_axis("Category").to_frame("Events")
                st.bar_chart(category_counts, use_container_width=True)

            panel("Event timeline (UTC)", "Counts by recorded day; timestamps that cannot be parsed are omitted")
            timeline_df = filtered_df.dropna(subset=["timestamp_parsed"]).copy()
            if not timeline_df.empty:
                timeline_df["Day (UTC)"] = timeline_df["timestamp_parsed"].dt.strftime("%Y-%m-%d")
                timeline_counts = timeline_df.groupby("Day (UTC)").size().rename("Events").to_frame()
                st.line_chart(timeline_counts, use_container_width=True)
            else:
                st.info("No valid timestamps are available for the timeline.")

            left, right = st.columns(2)
            with left:
                panel("Top recorded source IPs", "Technical identifiers only; not person attribution")
                ip_counts = filtered_df[filtered_df["source_ip_display"] != "Not recorded"]["source_ip_display"].value_counts().head(10).rename_axis("Source IP").to_frame("Events")
                if ip_counts.empty:
                    st.info("No source IPs are recorded for the current view.")
                else:
                    st.bar_chart(ip_counts, use_container_width=True)
            with right:
                panel("Frequently matched WAF rules", "Derived only from rule IDs in stored event evidence")
                rule_rows = []
                for _, row in filtered_df.iterrows():
                    evidence = row.get("evidence") or {}
                    if isinstance(evidence, str):
                        try:
                            evidence = json.loads(evidence)
                        except json.JSONDecodeError:
                            evidence = {}
                    rules = evidence.get("rules", []) if isinstance(evidence, dict) else []
                    if isinstance(rules, list):
                        for rule in rules:
                            if isinstance(rule, dict) and rule.get("rule_id"):
                                rule_rows.append({
                                    "Rule ID": str(rule.get("rule_id")),
                                    "Message": str(rule.get("message") or "No rule message recorded"),
                                })
                if rule_rows:
                    rule_df = pd.DataFrame(rule_rows)
                    rule_counts = rule_df.groupby(["Rule ID", "Message"]).size().reset_index(name="Matches")
                    rule_counts = rule_counts.sort_values("Matches", ascending=False).head(10)
                    st.dataframe(rule_counts, use_container_width=True, hide_index=True)
                else:
                    st.info("No matched rule IDs are present in evidence for the current view.")

            st.markdown("### Filtered event records")
            display_cols = [
                "id", "timestamp", "severity_display", "event_display", "category_display",
                "source_display", "source_ip_display", "target", "response_display", "description",
            ]
            records_df = filtered_df[display_cols].rename(columns={
                "id": "Event ID", "timestamp": "Timestamp (UTC)", "severity_display": "Severity",
                "event_display": "Event", "category_display": "Category", "source_display": "Detection source",
                "source_ip_display": "Source IP", "target": "Target / request",
                "response_display": "Recorded response", "description": "Description",
            })
            st.dataframe(records_df, use_container_width=True, hide_index=True)
            csv_data = records_df.to_csv(index=False).encode("utf-8")
            json_data = json.dumps(filtered_df.drop(columns=["timestamp_parsed"], errors="ignore").to_dict(orient="records"), indent=2, default=str).encode("utf-8")
            d1, d2, _ = st.columns([1, 1, 4])
            with d1:
                st.download_button(
                    "Download filtered CSV", data=csv_data,
                    file_name="chronosentinel_attack_analytics.csv", mime="text/csv",
                    key="download_analytics_csv",
                )
            with d2:
                st.download_button(
                    "Download filtered JSON", data=json_data,
                    file_name="chronosentinel_attack_analytics.json", mime="application/json",
                    key="download_analytics_json",
                )

        st.warning(
            "Analytics describe only events stored locally. A recorded block means the event record says it was blocked; "
            "this page does not perform live threat intelligence, forecast attacks, identify people, or execute remediation."
        )

elif page == "Logs & Events":
    st.subheader("Logs & events")
    c1, c2 = st.columns(2)
    with c1:
        sev = st.multiselect("Severity filter", ["Critical", "High", "Medium", "Low", "Info"], default=["Critical", "High", "Medium", "Low", "Info"])
    with c2:
        source = st.selectbox("Source filter", ["All"] + sorted({str(e.get("source") or "unknown") for e in events}))
    filtered = [e for e in events if severity_name(e.get("severity")) in sev]
    if source != "All":
        filtered = [e for e in filtered if str(e.get("source") or "unknown") == source]
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



elif page == "Cyber DNA":
    from app.cyber_dna import analyze_source

    st.subheader("Cyber DNA · Attacker Behaviour Analysis")
    st.caption(
        "Rule-based analysis of recorded events grouped by source IP. "
        "These are retrospective signals, not confirmed attribution or predictions of future attacks."
    )

    dna_results = analyze_source(events)
    if not dna_results:
        st.info("No events with a recorded source IP and valid timestamp are available.")
    else:
        total_sources = len(dna_results)
        repeated_sources = sum(r["Recorded events"] >= 3 for r in dna_results)
        escalating_sources = sum(
            any("Severity increased" in signal for signal in r["Signals"])
            for r in dna_results
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Sources analyzed", total_sources)
        c2.metric("Repeated activity", repeated_sources)
        c3.metric("Escalation patterns", escalating_sources)

        st.markdown("#### Source behaviour summary")
        summary = pd.DataFrame([{
            key: row[key] for key in (
                "Source IP", "Recorded events", "Distinct event types",
                "High/Critical", "Recorded blocks", "First seen", "Last seen"
            )
        } for row in dna_results])
        st.dataframe(summary, use_container_width=True, hide_index=True)

        choices = {
            f"{r['Source IP']} · {r['Recorded events']} event(s)": r
            for r in dna_results
        }
        selected = st.selectbox("Investigate source sequence", list(choices.keys()))
        detail = choices[selected]

        st.markdown("#### Observed sequence")
        timeline = pd.DataFrame([{
            "Timestamp": e.get("timestamp"),
            "Event": e.get("event_type"),
            "Category": e.get("category"),
            "Severity": str(e.get("severity") or "info").title(),
            "Target": e.get("target") or "Not recorded",
            "Recorded blocked": bool(e.get("blocked")),
            "Description": e.get("description") or ""
        } for e in detail["_sequence"]])
        st.dataframe(timeline, use_container_width=True, hide_index=True)

        st.markdown("#### Cyber DNA signals")
        if detail["Signals"]:
            for signal in detail["Signals"]:
                st.write(f"- {signal}")
        else:
            st.info("No repeated-activity or escalation rule was triggered for this source.")

        st.markdown("#### Recommended analyst actions")
        for recommendation in detail["Recommendations"]:
            st.write(f"- {recommendation}")

        export = summary.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Export source behaviour summary",
            data=export,
            file_name="chronosentinel_cyber_dna_summary.csv",
            mime="text/csv"
        )
        st.warning(
            "This engine analyzes only events already stored locally. "
            "A shared source IP does not prove a single attacker. Recommendations are advisory; "
            "no IP is blocked and no firewall rule is changed automatically."
        )

elif page == "ML Anomaly Detection":
    st.subheader("ML Anomaly Detection")
    st.caption(
        "Isolation Forest anomaly flags from the locally trained model. "
        "An anomaly is not proof of an attack."
    )

    try:
        with connect() as conn:
            prediction_count = conn.execute(
                "SELECT COUNT(*) FROM ml_predictions"
            ).fetchone()[0]
            anomaly_count = conn.execute(
                "SELECT COUNT(*) FROM ml_predictions WHERE anomaly=1"
            ).fetchone()[0]
            rows = conn.execute("""
                SELECT p.event_id, p.anomaly_score, p.anomaly,
                       p.model_name, p.created_at,
                       e.timestamp, e.severity, e.event_type,
                       e.source_ip, e.target, e.description, e.blocked
                FROM ml_predictions p
                JOIN security_events e ON e.id=p.event_id
                ORDER BY p.anomaly DESC, p.anomaly_score DESC,
                         p.created_at DESC
                LIMIT 500
            """).fetchall()
        predictions = [dict(r) for r in rows]
    except sqlite3.Error as exc:
        predictions = []
        prediction_count = anomaly_count = 0
        st.error(f"Could not load ML predictions: {exc}")

    model_path = PROJECT_DIR / "models" / "chronosentinel_anomaly.joblib"
    c1, c2, c3 = st.columns(3)
    c1.metric("Stored predictions", prediction_count)
    c2.metric("Anomalies flagged", anomaly_count)
    c3.metric("Model file", "Available" if model_path.exists() else "Missing")

    if not model_path.exists():
        st.warning(
            "No trained model file was found. Train it with "
            "`python scripts/chronosentinel_ml.py train`."
        )

    if predictions:
        view = pd.DataFrame([{
            "Event ID": r["event_id"],
            "Anomaly": "FLAGGED" if r["anomaly"] else "Not flagged",
            "Anomaly score": round(float(r["anomaly_score"]), 3),
            "Severity": severity_name(r["severity"]),
            "Event type": r["event_type"],
            "Source IP": r["source_ip"] or "Not recorded",
            "Target": r["target"] or "Not recorded",
            "WAF blocked": bool(r["blocked"]),
            "Timestamp": r["timestamp"],
            "Model": r["model_name"],
        } for r in predictions])

        only_anomalies = st.checkbox("Show only flagged anomalies", value=True)
        if only_anomalies:
            view = view[view["Anomaly"] == "FLAGGED"]

        st.dataframe(view, use_container_width=True, hide_index=True)

        flagged = [r for r in predictions if r["anomaly"]]
        if flagged:
            st.markdown("### Flagged event details")
            chosen = st.selectbox(
                "Select event ID",
                [r["event_id"] for r in flagged]
            )
            detail = next(r for r in flagged if r["event_id"] == chosen)
            st.write(f"**Event:** {detail['event_type']}")
            st.write(f"**Description:** {detail['description'] or 'Not recorded'}")
            st.write(f"**Anomaly score:** {float(detail['anomaly_score']):.3f}")
            st.caption(
                "Scores are model-derived ranking values, not probabilities "
                "that an event is malicious. Validate alerts against evidence."
            )

        st.download_button(
            "Export displayed ML results as CSV",
            view.to_csv(index=False),
            file_name="chronosentinel_ml_predictions.csv",
            mime="text/csv",
        )
    else:
        st.info(
            "No ML predictions are available yet. Run "
            "`python scripts/chronosentinel_ml.py score` in the project terminal."
        )


elif page == "Supervised Attack Classifier":
    import json
    import joblib
    import numpy as np
    import pandas as pd

    st.subheader("Supervised Attack Classifier")
    st.caption(
        "Random Forest trained on MSCAD traffic features. "
        "This classifier is separate from the Isolation Forest anomaly detector."
    )

    model_path = PROJECT_DIR / "models" / "chronosentinel_supervised.joblib"
    metrics_path = PROJECT_DIR / "reports" / "supervised_metrics.json"
    report_path = PROJECT_DIR / "reports" / "supervised_classification_report.json"

    if not model_path.exists():
        st.error("Supervised model not found. Train it with scripts/train_supervised.py first.")
    else:
        try:
            bundle = joblib.load(model_path)
            pipeline = bundle["pipeline"]
            feature_columns = bundle["feature_columns"]
            classes = bundle["class_names"]

            metrics = {}
            if metrics_path.exists():
                metrics = json.loads(metrics_path.read_text())

            a, b, c, d = st.columns(4)
            a.metric("Test accuracy", f"{metrics.get('accuracy', 0):.2%}" if metrics else "N/A")
            b.metric("Weighted precision", f"{metrics.get('weighted_precision', 0):.2%}" if metrics else "N/A")
            c.metric("Weighted recall", f"{metrics.get('weighted_recall', 0):.2%}" if metrics else "N/A")
            d.metric("Weighted F1", f"{metrics.get('weighted_f1', 0):.2%}" if metrics else "N/A")

            st.write(
                f"**Training dataset:** `{Path(str(bundle.get('dataset_path', 'unknown'))).name}`  \n"
                f"**Features expected:** {len(feature_columns)}  \n"
                f"**Classes:** {', '.join(classes)}"
            )

            if report_path.exists():
                report = json.loads(report_path.read_text())
                rows = []
                for label in classes:
                    item = report.get(label, {})
                    rows.append({
                        "Attack class": label,
                        "Precision": item.get("precision"),
                        "Recall": item.get("recall"),
                        "F1-score": item.get("f1-score"),
                        "Test samples": item.get("support")
                    })
                st.markdown("#### Per-class evaluation")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.caption(
                    "Rare classes have very few test examples; their scores are uncertain. "
                    "Metrics are from the saved holdout evaluation, not a guarantee of live performance."
                )

            st.markdown("#### Saved Flow Analysis")
            saved_flow_path = PROJECT_DIR / "reports" / "flow_predictions.csv"
            sample_flow_path = PROJECT_DIR / "reports" / "flow_sample_predictions.csv"
            chosen_flow_path = (
                saved_flow_path if saved_flow_path.exists()
                else sample_flow_path if sample_flow_path.exists()
                else None
            )

            if chosen_flow_path is None:
                st.info(
                    "No saved flow predictions found yet. Analyze a compatible CSV below "
                    "or run scripts/classify_flows.py to create a report."
                )
            else:
                try:
                    saved_flows = pd.read_csv(chosen_flow_path, low_memory=False)
                    if "Predicted_Attack" not in saved_flows.columns:
                        st.warning("The saved CSV does not contain Predicted_Attack.")
                    elif saved_flows.empty:
                        st.info("The saved flow-prediction report is empty.")
                    else:
                        st.caption(
                            f"Loaded `{chosen_flow_path.name}` · "
                            f"{len(saved_flows):,} rows. These are model predictions, "
                            "not confirmed incidents or proof of live network capture."
                        )

                        classes_found = sorted(
                            saved_flows["Predicted_Attack"].dropna().astype(str).unique()
                        )
                        f1, f2 = st.columns(2)
                        with f1:
                            selected_classes = st.multiselect(
                                "Filter predicted classes",
                                options=classes_found,
                                default=classes_found,
                                key="saved_flow_classes"
                            )
                        with f2:
                            min_confidence = st.slider(
                                "Minimum confidence",
                                min_value=0.0,
                                max_value=1.0,
                                value=0.0,
                                step=0.05,
                                key="saved_flow_min_confidence"
                            )

                        filtered = saved_flows[
                            saved_flows["Predicted_Attack"].astype(str).isin(selected_classes)
                        ].copy()

                        if "Confidence" in filtered.columns:
                            filtered["Confidence"] = pd.to_numeric(
                                filtered["Confidence"], errors="coerce"
                            )
                            filtered = filtered[
                                filtered["Confidence"].ge(min_confidence)
                            ]

                        counts = filtered["Predicted_Attack"].value_counts()
                        a, b, c = st.columns(3)
                        a.metric("Matching flows", f"{len(filtered):,}")
                        b.metric(
                            "Predicted non-Normal",
                            f"{int((filtered['Predicted_Attack'] != 'Normal').sum()):,}"
                        )
                        c.metric("Classes shown", f"{filtered['Predicted_Attack'].nunique()}")

                        st.markdown("##### Filtered class distribution")
                        st.dataframe(
                            counts.rename_axis("Predicted_Attack")
                            .reset_index(name="Rows"),
                            use_container_width=True,
                            hide_index=True
                        )

                        display_cols = [
                            col for col in [
                                "Predicted_Attack", "Confidence", "Severity",
                                "Model", "Interpretation_Note"
                            ] if col in filtered.columns
                        ]
                        sort_options = ["Original order"]
                        if "Confidence" in filtered.columns:
                            sort_options.append("Highest confidence first")
                        if "Severity" in filtered.columns:
                            sort_options.append("Severity first")

                        sort_choice = st.selectbox(
                            "Sort filtered predictions",
                            options=sort_options,
                            key="saved_flow_sort"
                        )

                        if sort_choice == "Highest confidence first" and "Confidence" in filtered.columns:
                            filtered = filtered.sort_values(
                                "Confidence", ascending=False, na_position="last"
                            )
                        elif sort_choice == "Severity first" and "Severity" in filtered.columns:
                            severity_order = {
                                "Critical": 0, "High": 1, "Medium": 2,
                                "Low": 3, "Info": 4, "Review": 5
                            }
                            filtered["_severity_order"] = (
                                filtered["Severity"].map(severity_order).fillna(99)
                            )
                            filtered = filtered.sort_values(
                                "_severity_order", ascending=True
                            ).drop(columns="_severity_order")

                        st.markdown("##### Filtered prediction details")
                        st.dataframe(
                            filtered[display_cols].head(500),
                            use_container_width=True,
                            hide_index=True
                        )
                        st.download_button(
                            "Download filtered flow predictions",
                            data=filtered.to_csv(index=False).encode("utf-8"),
                            file_name="chronosentinel_filtered_flow_predictions.csv",
                            mime="text/csv",
                            key="download_saved_flow_predictions"
                        )
                except Exception as exc:
                    st.warning(f"Could not read saved flow predictions: {exc}")

            st.markdown("#### Analyze network traffic CSV")
            st.caption(
                "Upload flow-level traffic features. The CSV must use the same "
                "feature definitions as the MSCAD training dataset."
            )
            uploaded = st.file_uploader(
                "Upload a compatible network traffic CSV",
                type=["csv"],
                key="supervised_attack_csv"
            )

            if uploaded is not None:
                try:
                    incoming = pd.read_csv(uploaded, low_memory=False)
                    incoming.columns = [str(col).strip() for col in incoming.columns]

                    def feature_key(value):
                        return "".join(
                            ch.lower() for ch in str(value)
                            if ch.isalnum()
                        )

                    if incoming.empty:
                        st.warning("The uploaded CSV has no rows.")
                    else:
                        # Exclude labels so the model never uses ground truth as input.
                        label_keys = {
                            "label", "labels", "target", "class",
                            "attack", "attacklabel", "groundtruth"
                        }
                        incoming = incoming.loc[
                            :,
                            [c for c in incoming.columns
                             if feature_key(c) not in label_keys]
                        ]

                        # Resolve quoted/unquoted feature names without fabricating values.
                        source_by_key = {}
                        for col in incoming.columns:
                            source_by_key.setdefault(feature_key(col), col)

                        resolved = {}
                        missing = []
                        for feature in feature_columns:
                            actual_col = source_by_key.get(feature_key(feature))
                            if actual_col is None:
                                missing.append(feature)
                            else:
                                resolved[feature] = actual_col

                        if missing:
                            st.error(
                                f"CSV is missing {len(missing)} required model features. "
                                "No predictions were generated."
                            )
                            st.code("\\n".join(missing[:40]))
                            st.caption(
                                "Matching names alone does not guarantee matching "
                                "feature definitions. Do not fill missing features with zeros."
                            )
                        else:
                            X_input = pd.DataFrame(index=incoming.index)
                            for feature in feature_columns:
                                X_input[feature] = pd.to_numeric(
                                    incoming[resolved[feature]],
                                    errors="coerce"
                                )

                            import numpy as np
                            values = X_input.to_numpy(dtype=float)
                            valid = np.isfinite(values).all(axis=1)
                            skipped = int((~valid).sum())

                            if not valid.any():
                                st.error(
                                    "No rows contain valid numeric values for every required feature."
                                )
                            else:
                                X_valid = X_input.loc[valid]
                                prediction_ids = pipeline.predict(X_valid)
                                probabilities = pipeline.predict_proba(X_valid)
                                predicted_labels = [
                                    classes[int(i)] for i in prediction_ids
                                ]
                                confidence = probabilities.max(axis=1)

                                severity_map = {
                                    "Normal": ("Info", "Continue monitoring; no attack-specific action indicated."),
                                    "Brute_Force": ("High", "Review authentication logs and investigate the source."),
                                    "Port_Scan": ("Medium", "Review scan patterns and source activity."),
                                    "HTTP_DDoS": ("Critical", "Validate request rates and review approved WAF/DDoS protections."),
                                    "ICMP_Flood": ("High", "Validate ICMP traffic volume and review network controls."),
                                    "Web_Crwling": ("Low", "Review request patterns and access policies.")
                                }

                                result = incoming.loc[valid].copy()
                                result["Predicted_Attack"] = predicted_labels
                                result["Confidence"] = np.round(confidence, 4)
                                result["Severity"] = [
                                    severity_map.get(
                                        label, ("Review", "Investigate before taking action.")
                                    )[0]
                                    for label in predicted_labels
                                ]
                                result["Recommended_Action"] = [
                                    severity_map.get(
                                        label, ("Review", "Investigate before taking action.")
                                    )[1]
                                    for label in predicted_labels
                                ]
                                result["Prediction_Status"] = "Model prediction — not a confirmed incident"

                                st.success(
                                    f"Analyzed {len(result):,} rows; "
                                    f"skipped {skipped:,} rows with missing or invalid numeric features."
                                )

                                counts = result["Predicted_Attack"].value_counts()
                                a, b, c = st.columns(3)
                                a.metric("Flows analyzed", f"{len(result):,}")
                                b.metric(
                                    "Predicted non-Normal",
                                    f"{int((result['Predicted_Attack'] != 'Normal').sum()):,}"
                                )
                                c.metric("Classes predicted", f"{result['Predicted_Attack'].nunique()}")

                                st.markdown("#### Predicted class distribution")
                                st.dataframe(
                                    counts.rename_axis("Predicted_Attack")
                                    .reset_index(name="Rows"),
                                    use_container_width=True,
                                    hide_index=True
                                )

                                st.markdown("#### Prediction details")
                                st.dataframe(
                                    result.head(500),
                                    use_container_width=True,
                                    hide_index=True
                                )
                                st.caption(
                                    "Confidence is the model's predicted class probability, not calibrated certainty. "
                                    "Results are advisory and do not automatically create confirmed incidents, "
                                    "block IP addresses, or change firewall rules. Use only with compatible, "
                                    "representative traffic features."
                                )

                                st.download_button(
                                    "Download all predictions as CSV",
                                    data=result.to_csv(index=False).encode("utf-8"),
                                    file_name="chronosentinel_supervised_predictions.csv",
                                    mime="text/csv"
                                )
                                st.download_button(
                                    "Download class summary as CSV",
                                    data=counts.rename_axis("Predicted_Attack")
                                    .reset_index(name="Rows")
                                    .to_csv(index=False).encode("utf-8"),
                                    file_name="chronosentinel_attack_summary.csv",
                                    mime="text/csv"
                                )
                except Exception as exc:
                    st.error(f"Could not analyze this CSV: {exc}")
                    st.info(
                        "Check that the file is a valid CSV with compatible numeric "
                        "traffic feature columns."
                    )

        except Exception as exc:
            st.error(f"Could not load the supervised model: {exc}")
            st.info("The existing anomaly-detection page is unchanged.")

elif page == "Reports":
    st.subheader("Security reports")
    st.caption(
        "SOC reporting based on events and incident cases stored "
        "in the local ChronoSentinel AI database."
    )

    # ---------------------------------------------------------
    # Prepare report data without changing the database schema
    # ---------------------------------------------------------
    import pandas as pd
    import json

    report_events = list(events or [])
    report_cases = list(cases or [])

    def report_severity(event):
        return severity_name(event.get("severity"))

    def report_blocked(event):
        return bool(event.get("blocked"))

    def report_event_label(event):
        return event_title(event)

    event_rows = []
    for event in report_events:
        evidence = event.get("evidence") or {}
        event_rows.append({
            "ID": event.get("id"),
            "Timestamp (UTC)": event.get("timestamp"),
            "Severity": report_severity(event),
            "Source": event.get("source") or "Unknown",
            "Category": event.get("category") or "Unclassified",
            "Event": report_event_label(event),
            "Source IP": event.get("source_ip") or "Not recorded",
            "Target / Request": event.get("target") or "Not recorded",
            "Response": (
                "Blocked" if report_blocked(event)
                else "Not confirmed blocked"
            ),
            "Description": event.get("description") or "",
            "Evidence JSON": json.dumps(evidence, default=str),
        })

    all_df = pd.DataFrame(event_rows)

    # ---------------------------------------------------------
    # Report filters
    # ---------------------------------------------------------
    st.markdown("### Report filters")

    f1, f2, f3 = st.columns(3)

    severity_options = ["Critical", "High", "Medium", "Low", "Info"]
    source_options = sorted({
        str(e.get("source") or "Unknown") for e in report_events
    })

    with f1:
        selected_severities = st.multiselect(
            "Severity",
            severity_options,
            default=severity_options,
            key="reports_severity_filter",
        )

    with f2:
        selected_source = st.selectbox(
            "Detection source",
            ["All"] + source_options,
            key="reports_source_filter",
        )

    with f3:
        selected_response = st.selectbox(
            "Recorded response",
            ["All", "Blocked", "Not confirmed blocked"],
            key="reports_response_filter",
        )

    filtered_events = []
    for event in report_events:
        if report_severity(event) not in selected_severities:
            continue

        if (
            selected_source != "All"
            and str(event.get("source") or "Unknown") != selected_source
        ):
            continue

        response = (
            "Blocked" if report_blocked(event)
            else "Not confirmed blocked"
        )
        if selected_response != "All" and response != selected_response:
            continue

        filtered_events.append(event)

    filtered_rows = []
    for event in filtered_events:
        evidence = event.get("evidence") or {}
        filtered_rows.append({
            "ID": event.get("id"),
            "Timestamp (UTC)": event.get("timestamp"),
            "Severity": report_severity(event),
            "Source": event.get("source") or "Unknown",
            "Category": event.get("category") or "Unclassified",
            "Event": report_event_label(event),
            "Source IP": event.get("source_ip") or "Not recorded",
            "Target / Request": event.get("target") or "Not recorded",
            "Response": (
                "Blocked" if report_blocked(event)
                else "Not confirmed blocked"
            ),
            "Description": event.get("description") or "",
            "Evidence JSON": json.dumps(evidence, default=str),
        })

    filtered_df = pd.DataFrame(filtered_rows)

    # ---------------------------------------------------------
    # SOC report summary
    # ---------------------------------------------------------
    st.markdown("### Security posture summary")

    total_events = len(filtered_events)
    blocked_events = sum(
        1 for event in filtered_events if report_blocked(event)
    )
    high_critical = sum(
        1 for event in filtered_events
        if report_severity(event) in ("High", "Critical")
    )
    distinct_sources = len({
        str(event.get("source_ip"))
        for event in filtered_events
        if event.get("source_ip")
    })

    open_cases = [
        case for case in report_cases
        if case.get("status") in ("Open", "Investigating")
    ]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Events in report", total_events)
    m2.metric("Recorded blocks", blocked_events)
    m3.metric("High / Critical", high_critical)
    m4.metric("Distinct source IPs", distinct_sources)
    m5.metric("Open cases", len(open_cases))

    if high_critical:
        st.error(
            f"Priority review: {high_critical} high/critical event(s) "
            "are present in the filtered report. Review the event "
            "evidence and linked incident cases."
        )
    elif total_events:
        st.success(
            "No high/critical events appear in the current filtered view. "
            "This does not establish that the environment is threat-free."
        )
    else:
        st.info("No events match the current report filters.")

    st.caption(
        "A recorded block means the stored event says a request was blocked. "
        "Source IP addresses are technical identifiers, not proof of identity."
    )

    # ---------------------------------------------------------
    # Event timeline and severity distribution
    # ---------------------------------------------------------
    st.markdown("### Event trends")

    if not filtered_df.empty:
        chart_df = filtered_df.copy()
        chart_df["_timestamp"] = pd.to_datetime(
            chart_df["Timestamp (UTC)"],
            utc=True,
            errors="coerce",
        )
        chart_df = chart_df.dropna(subset=["_timestamp"])

        chart_left, chart_right = st.columns(2)

        with chart_left:
            st.markdown("#### Event timeline (UTC)")
            if not chart_df.empty:
                chart_df["Day (UTC)"] = (
                    chart_df["_timestamp"].dt.strftime("%Y-%m-%d")
                )
                timeline = (
                    chart_df.groupby("Day (UTC)")
                    .size()
                    .rename("Events")
                    .sort_index()
                )
                st.bar_chart(timeline)
            else:
                st.info("No valid timestamps are available for the timeline.")

        with chart_right:
            st.markdown("#### Severity distribution")
            severity_counts = (
                filtered_df["Severity"]
                .value_counts()
                .reindex(severity_options, fill_value=0)
            )
            severity_counts = severity_counts[severity_counts > 0]
            if not severity_counts.empty:
                st.bar_chart(severity_counts)
            else:
                st.info("No severity data is available.")

        st.markdown("#### Events by detection source")
        source_counts = filtered_df["Source"].value_counts()
        if not source_counts.empty:
            st.bar_chart(source_counts)
    else:
        st.info("Charts will appear when events match your filters.")

    # ---------------------------------------------------------
    # Event report table
    # ---------------------------------------------------------
    st.markdown("### Filtered security event records")
    st.caption(f"Showing {len(filtered_df)} event record(s).")

    if not filtered_df.empty:
        display_columns = [
            "ID",
            "Timestamp (UTC)",
            "Severity",
            "Source",
            "Event",
            "Source IP",
            "Response",
            "Target / Request",
            "Description",
        ]
        st.dataframe(
            filtered_df[display_columns],
            use_container_width=True,
            hide_index=True,
        )

        # Keep downloads in memory; no extra files or schema changes.
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        json_data = json.dumps(
            [
                {
                    **event,
                    "evidence": event.get("evidence") or {},
                }
                for event in filtered_events
            ],
            indent=2,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download filtered events (CSV)",
                data=csv_data,
                file_name="chronosentinel_security_report.csv",
                mime="text/csv",
                key="reports_download_csv",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Download filtered events (JSON)",
                data=json_data,
                file_name="chronosentinel_security_report.json",
                mime="application/json",
                key="reports_download_json",
                use_container_width=True,
            )
    else:
        st.warning("No matching events to display or export.")

    # ---------------------------------------------------------
    # Incident case report
    # ---------------------------------------------------------
    st.markdown("### Incident case report")

    if report_cases:
        case_rows = []
        for case in report_cases:
            linked_event = next(
                (
                    event for event in report_events
                    if str(event.get("id")) == str(case.get("event_id"))
                ),
                {},
            )

            case_rows.append({
                "Case ID": case.get("id"),
                "Event ID": case.get("event_id"),
                "Severity": (
                    report_severity(linked_event)
                    if linked_event else "Unknown"
                ),
                "Event": (
                    report_event_label(linked_event)
                    if linked_event else "Linked event unavailable"
                ),
                "Source IP": (
                    linked_event.get("source_ip") or "Not recorded"
                ),
                "Status": case.get("status") or "Unknown",
                "Created (UTC)": case.get("created_at", ""),
                "Last updated (UTC)": case.get("updated_at", ""),
                "Analyst notes": case.get("notes", ""),
            })

        cases_df = pd.DataFrame(case_rows)
        st.dataframe(
            cases_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download incident cases (CSV)",
            data=cases_df.to_csv(index=False).encode("utf-8"),
            file_name="chronosentinel_incident_cases.csv",
            mime="text/csv",
            key="reports_download_cases",
        )
    else:
        st.info("No incident cases have been recorded yet.")

    # ---------------------------------------------------------
    # Report integrity / limitations
    # ---------------------------------------------------------
    st.markdown("---")
    st.caption(
        "Report scope: locally stored SQLite events and incident cases. "
        "Charts summarize the current filtered records only. This page "
        "does not query external threat intelligence, identify people, "
        "predict future attacks, or execute security remediation."
    )
