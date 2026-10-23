
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "chronosentinel.db"

st.set_page_config(
    page_title="ChronoSentinel AI | Security Operations",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {
    background: #151c28;
    border: 1px solid #29364a;
    padding: 16px;
    border-radius: 10px;
}
section[data-testid="stSidebar"] {
    border-right: 1px solid #29364a;
}
.status-pill {
    padding: 5px 10px;
    border-radius: 6px;
    background: #15372d;
    color: #6ee7b7;
    font-size: 13px;
}
.muted {color: #9ca9bc; font-size: 13px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=2)
def load_events():
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query("""
            SELECT id, timestamp, source, category, event_type,
                   severity, source_ip, target, description,
                   blocked, evidence_json
            FROM security_events
            ORDER BY id DESC
            LIMIT 500
        """, connection)


def parse_timestamp(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# Automatic refresh every 3 seconds.
st_autorefresh(interval=3000, key="soc_refresh")

events = load_events()

header_left, header_right = st.columns([3, 1])
with header_left:
    st.title("🛡️ ChronoSentinel AI")
    st.caption("SECURITY OPERATIONS CENTER  /  THREAT MONITORING")
with header_right:
    st.markdown(
        '<span class="status-pill">● Dashboard active</span>',
        unsafe_allow_html=True,
    )
    st.caption("Database: " + ("Connected" if DB_PATH.exists() else "Not found"))

st.divider()

if events.empty:
    st.info("No security events are stored yet. Waiting for incoming events.")
    st.stop()

events["blocked"] = events["blocked"].astype(bool)
events["severity"] = events["severity"].fillna("unknown").str.lower()
events["source"] = events["source"].fillna("unknown")
events["category"] = events["category"].fillna("unknown")

# Sidebar filters
st.sidebar.title("Investigation Filters")

source_options = sorted(events["source"].unique().tolist())
severity_options = sorted(events["severity"].unique().tolist())
category_options = sorted(events["category"].unique().tolist())

selected_sources = st.sidebar.multiselect(
    "Event source", source_options, default=source_options
)
selected_severities = st.sidebar.multiselect(
    "Severity", severity_options, default=severity_options
)
selected_categories = st.sidebar.multiselect(
    "Category", category_options, default=category_options
)
show_blocked_only = st.sidebar.checkbox("Blocked events only", value=False)

if st.sidebar.button("Refresh now", width="stretch"):
    st.cache_data.clear()
    st.rerun()

filtered = events[
    events["source"].isin(selected_sources)
    & events["severity"].isin(selected_severities)
    & events["category"].isin(selected_categories)
].copy()

if show_blocked_only:
    filtered = filtered[filtered["blocked"]]

# Overview metrics
total = len(filtered)
blocked_count = int(filtered["blocked"].sum())
high_count = int(filtered["severity"].isin(["critical", "high"]).sum())
network_count = int((filtered["category"] == "network_attack").sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("EVENTS LOADED", total)
m2.metric("REQUESTS BLOCKED", blocked_count)
m3.metric("HIGH / CRITICAL", high_count)
m4.metric("NETWORK ALERTS", network_count)

st.caption(
    f"Showing up to 500 stored records · Auto-refresh every 3 seconds · "
    f"Last UI refresh: {datetime.now().astimezone().strftime('%H:%M:%S %Z')}"
)

st.divider()

# Event distribution
left, right = st.columns(2)
with left:
    st.subheader("Events by Source")
    if not filtered.empty:
        st.bar_chart(filtered["source"].value_counts())
    else:
        st.caption("No events match the current filters.")

with right:
    st.subheader("Events by Severity")
    if not filtered.empty:
        st.bar_chart(filtered["severity"].value_counts())

st.divider()
st.subheader("Security Event Stream")

if filtered.empty:
    st.info("No events match your selected filters.")
else:
    display = filtered[
        [
            "id", "timestamp", "source", "category", "event_type",
            "severity", "source_ip", "target", "blocked", "description",
        ]
    ].copy()

    display["status"] = display["blocked"].map(
        {True: "BLOCKED", False: "OBSERVED"}
    )
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        height=330,
    )

    st.subheader("Incident Investigation")
    event_ids = filtered["id"].astype(int).tolist()
    selected_id = st.selectbox("Select event ID", event_ids)
    selected = filtered[filtered["id"] == selected_id].iloc[0]

    detail_left, detail_right = st.columns([1, 2])
    with detail_left:
        st.markdown("**Event classification**")
        st.write("Source:", selected["source"])
        st.write("Category:", selected["category"])
        st.write("Type:", selected["event_type"])
        st.write("Severity:", selected["severity"].upper())
        st.write(
            "Status:",
            "BLOCKED" if selected["blocked"] else "OBSERVED — no block confirmed",
        )
        st.write("Source IP:", selected["source_ip"] or "Not available")
        st.write("Target:", selected["target"] or "Not available")

    with detail_right:
        st.markdown("**Description**")
        st.write(selected["description"] or "No description recorded.")
        st.markdown("**Evidence**")
        try:
            evidence = json.loads(selected["evidence_json"] or "{}")
        except (ValueError, TypeError):
            evidence = {"raw_evidence": selected["evidence_json"]}
        st.json(evidence)

st.divider()
st.caption(
    "ChronoSentinel AI prototype · Dashboard refresh does not itself "
    "collect network traffic or block connections."
)
