
from pathlib import Path
import re
import shutil
from datetime import datetime

# Run from ~/ChronoSentinel-AI
FILE = Path("app/dashboard.py")

if not FILE.exists():
    raise SystemExit(
        "ERROR: app/dashboard.py not found. "
        "Run this script from your ChronoSentinel-AI project folder."
    )

source = FILE.read_text(encoding="utf-8")

# Keep a timestamped backup before making changes.
backup = FILE.with_name(
    f"dashboard.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
shutil.copy2(FILE, backup)

# ---------------------------------------------------------
# 1. Replace the global stylesheet with a consistent dark UI
# ---------------------------------------------------------
new_css = r"""
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
"""

if "<style>" not in source or "</style>" not in source:
    raise SystemExit("ERROR: Could not locate the existing CSS block.")

source = re.sub(
    r"<style>.*?</style>",
    lambda _: new_css,
    source,
    count=1,
    flags=re.DOTALL,
)

# ---------------------------------------------------------
# 2. Replace the sidebar navigation, keeping existing routes
# ---------------------------------------------------------
sidebar_start = source.find("with st.sidebar:")
topbar_marker = '<div class="topbar">'

if sidebar_start == -1:
    raise SystemExit("ERROR: Could not find 'with st.sidebar:' in dashboard.py.")

topbar_pos = source.find(topbar_marker, sidebar_start)

if topbar_pos == -1:
    raise SystemExit(
        "ERROR: Could not find the existing topbar. "
        "No sidebar replacement was written."
    )

# Find the start of the Streamlit call that renders the topbar.
topbar_call = source.rfind("st.markdown(", sidebar_start, topbar_pos)

if topbar_call == -1:
    raise SystemExit("ERROR: Could not locate the topbar's st.markdown call.")

sidebar_code = r'''
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

'''

# Replace the complete old sidebar and any injected theme-toggle CSS,
# stopping immediately before the original topbar call.
source = source[:sidebar_start] + sidebar_code + "\n" + source[topbar_call:]

# Remove any leftover light appearance toggle if it exists elsewhere.
source = re.sub(
    r'^\s*light_mode\s*=\s*st\.toggle\([\s\S]*?^\s*\)\s*\n',
    "",
    source,
    flags=re.MULTILINE,
)

# Remove a previously injected theme_css block, if present.
source = re.sub(
    r'^\s*theme_css\s*=\s*""".*?"""\s*\n'
    r'\s*st\.markdown\(\s*theme_css,\s*unsafe_allow_html=True\s*\)\s*\n',
    "",
    source,
    flags=re.MULTILINE | re.DOTALL,
)

# Save only after all structural checks have passed.
FILE.write_text(source, encoding="utf-8")

# Basic syntax validation before restarting Streamlit.
import ast
try:
    ast.parse(source, filename=str(FILE))
except SyntaxError as exc:
    shutil.copy2(backup, FILE)
    raise SystemExit(
        f"Syntax validation failed; original file restored from {backup}.\n{exc}"
    )

print("SUCCESS: Dark ChronoSentinel UI patch applied.")
print(f"Backup: {backup}")
print("Next: stop Streamlit with Ctrl+C, then run:")
print("streamlit run app/dashboard.py")
