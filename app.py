"""
EcoMuni AI — Streamlit Frontend (app.py)
Complete single-file UI for the EcoMuni AI civic issue platform.

Run with:
    streamlit run app.py

Requires the FastAPI backend running on http://localhost:8000
"""

import json
import random
import time
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

import pandas as pd
import requests
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

# Severity colour palette (1-10 → hex)
def severity_color(score: Optional[int]) -> str:
    if score is None:
        return "#94a3b8"
    if score <= 3:
        return "#22c55e"
    if score <= 6:
        return "#f59e0b"
    return "#ef4444"

def severity_label(score: Optional[int]) -> str:
    if score is None:
        return "Unknown"
    if score <= 3:
        return "Low"
    if score <= 6:
        return "Moderate"
    if score <= 8:
        return "High"
    return "Critical"

CATEGORY_ICONS = {
    "POTHOLE": "🕳️", "ROAD_CRACK": "🛣️", "BROKEN_STREETLIGHT": "💡",
    "GARBAGE_DUMP": "🗑️", "OPEN_DRAIN": "🚧", "SEWAGE_OVERFLOW": "💧",
    "WATER_LOGGING": "🌊", "WATER_HYACINTH_BLOCKAGE": "🌿",
    "FALLEN_TREE": "🌳", "BROKEN_FOOTPATH": "🚶", "ENCROACHMENT": "⚠️",
    "AIR_POLLUTION_SOURCE": "🏭", "WATER_BODY_CONTAMINATION": "☣️",
    "ELECTRICAL_HAZARD": "⚡", "ABANDONED_VEHICLE": "🚗",
    "GRAFFITI_VANDALISM": "🎨", "CONSTRUCTION_DEBRIS": "🏗️",
    "DEAD_ANIMAL": "🐾", "OTHER": "📍",
}

STATUS_COLORS = {"unverified": "#ef4444", "verified": "#f59e0b", "resolved": "#22c55e"}
STATUS_LABELS = {"unverified": "🔴 Unverified", "verified": "🟠 Verified", "resolved": "🟢 Resolved"}

# ──────────────────────────────────────────────────────────────────────────────
# Page config & global CSS
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EcoMuni AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Root palette ── */
:root {
    --bg:        #0d1117;
    --surface:   #161b22;
    --surface2:  #1c2333;
    --border:    #30363d;
    --accent:    #3fb950;
    --accent2:   #58a6ff;
    --warn:      #d29922;
    --danger:    #f85149;
    --text:      #e6edf3;
    --muted:     #8b949e;
    --radius:    12px;
}

/* ── App chrome ── */
.stApp { background: var(--bg); color: var(--text); }
header[data-testid="stHeader"] { background: var(--bg); border-bottom: 1px solid var(--border); }
section[data-testid="stSidebar"] { background: var(--surface); }

/* ── Remove default padding ── */
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px; }

/* ── Hero header ── */
.eco-hero {
    background: linear-gradient(135deg, #0d2818 0%, #0d1117 60%);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem 2.5rem 1.75rem;
    margin-bottom: 1.75rem;
    position: relative;
    overflow: hidden;
}
.eco-hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse 60% 80% at 90% -10%, rgba(63,185,80,.18) 0%, transparent 70%);
    pointer-events: none;
}
.eco-hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 .25rem;
    letter-spacing: -.02em;
}
.eco-hero-title span { color: var(--accent); }
.eco-hero-sub {
    color: var(--muted);
    font-size: .95rem;
    margin: 0;
    font-weight: 400;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    padding: 4px;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: var(--muted);
    font-weight: 500;
    font-size: .9rem;
    padding: .5rem 1.25rem;
    border: none;
    transition: all .15s;
}
.stTabs [aria-selected="true"] {
    background: var(--surface2) !important;
    color: var(--text) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Cards ── */
.eco-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color .15s;
}
.eco-card:hover { border-color: #444c56; }
.eco-card-header {
    display: flex;
    align-items: center;
    gap: .6rem;
    margin-bottom: .75rem;
}
.eco-card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: var(--text);
    margin: 0;
}
.eco-badge {
    display: inline-block;
    border-radius: 20px;
    font-size: .72rem;
    font-weight: 600;
    padding: 2px 10px;
    letter-spacing: .03em;
    text-transform: uppercase;
}
.eco-badge-red   { background: rgba(248,81,73,.15); color: #f85149; border: 1px solid rgba(248,81,73,.3); }
.eco-badge-amber { background: rgba(210,153,34,.15); color: #d29922; border: 1px solid rgba(210,153,34,.3); }
.eco-badge-green { background: rgba(63,185,80,.15);  color: #3fb950; border: 1px solid rgba(63,185,80,.3); }
.eco-badge-blue  { background: rgba(88,166,255,.15); color: #58a6ff; border: 1px solid rgba(88,166,255,.3); }

/* ── Metric tile ── */
.eco-metric {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
}
.eco-metric-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
    margin-bottom: .2rem;
}
.eco-metric-label {
    font-size: .75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .06em;
    font-weight: 500;
}

/* ── Leaderboard row ── */
.lb-row {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: .6rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: border-color .15s;
}
.lb-row:hover { border-color: var(--accent); }
.lb-rank {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    width: 2.2rem;
    text-align: center;
    flex-shrink: 0;
}
.lb-name {
    font-weight: 600;
    font-size: .95rem;
    flex: 1;
    color: var(--text);
}
.lb-score {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--accent);
}
.lb-sub { font-size: .78rem; color: var(--muted); }

/* ── BOM table ── */
.bom-table {
    width: 100%;
    border-collapse: collapse;
    font-size: .85rem;
    margin-top: .5rem;
}
.bom-table th {
    background: var(--surface2);
    color: var(--muted);
    font-weight: 600;
    text-transform: uppercase;
    font-size: .72rem;
    letter-spacing: .06em;
    padding: .5rem .75rem;
    border-bottom: 1px solid var(--border);
    text-align: left;
}
.bom-table td {
    padding: .5rem .75rem;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    vertical-align: top;
}
.bom-table tr:last-child td { border-bottom: none; }
.bom-avail-yes { color: var(--accent); font-size: .72rem; font-weight: 600; }
.bom-avail-no  { color: var(--warn);   font-size: .72rem; font-weight: 600; }

/* ── Email block ── */
.email-block {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    font-size: .85rem;
    line-height: 1.7;
    color: #cdd9e5;
    white-space: pre-wrap;
    font-family: 'Inter', monospace;
    max-height: 260px;
    overflow-y: auto;
}

/* ── Inputs ── */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(63,185,80,.2) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--accent) !important;
    color: #0d1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: .9rem !important;
    padding: .5rem 1.25rem !important;
    transition: opacity .15s !important;
}
.stButton > button:hover { opacity: .88 !important; }

/* ── Secondary button ── */
button[kind="secondary"] {
    background: var(--surface2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--surface2);
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    padding: .75rem;
}

/* ── Expander ── */
details { background: var(--surface2); border-radius: 8px; border: 1px solid var(--border) !important; }
summary { padding: .75rem 1rem; font-weight: 600; color: var(--text); cursor: pointer; }

/* ── Alerts ── */
.stSuccess { background: rgba(63,185,80,.1); border-left: 3px solid var(--accent); border-radius: 6px; }
.stError   { background: rgba(248,81,73,.1); border-left: 3px solid var(--danger); border-radius: 6px; }
.stWarning { background: rgba(210,153,34,.1); border-left: 3px solid var(--warn); border-radius: 6px; }
.stInfo    { background: rgba(88,166,255,.1); border-left: 3px solid var(--accent2); border-radius: 6px; }

/* ── Velocity bar ── */
.vel-bar-bg {
    background: var(--surface2);
    border-radius: 20px;
    height: 6px;
    width: 100%;
    overflow: hidden;
    margin-top: 4px;
}
.vel-bar-fill {
    background: linear-gradient(90deg, var(--accent), #58a6ff);
    height: 100%;
    border-radius: 20px;
    transition: width .4s ease;
}

/* ── Divider ── */
.eco-divider { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }

/* ── Hide default Streamlit footer ── */
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# API helpers
# ──────────────────────────────────────────────────────────────────────────────
def api_get(path: str, params: dict = None) -> Optional[dict]:
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot reach backend at `http://localhost:8000`. Is the FastAPI server running?")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def api_post_form(path: str, data: dict, file_field: str, file_bytes: bytes, filename: str, mime: str) -> Optional[dict]:
    try:
        files = {file_field: (filename, file_bytes, mime)}
        r = requests.post(f"{API_BASE}{path}", data=data, files=files, timeout=60)
        if r.status_code in (200, 201):
            return r.json()
        detail = r.json().get("detail", r.text) if r.content else r.text
        if isinstance(detail, dict):
            st.error(f"**{detail.get('error', 'ERROR')}**: {detail.get('message', '')}")
        else:
            st.error(f"Server returned {r.status_code}: {detail}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot reach backend at `http://localhost:8000`. Is the FastAPI server running?")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

def api_post_file(path: str, file_bytes: bytes, filename: str, mime: str) -> Optional[dict]:
    try:
        files = {"image": (filename, file_bytes, mime)}
        r = requests.post(f"{API_BASE}{path}", files=files, timeout=60)
        if r.status_code in (200, 201):
            return r.json()
        detail = r.json().get("detail", r.text) if r.content else r.text
        if isinstance(detail, dict):
            st.error(f"**{detail.get('error', 'ERROR')}**: {detail.get('message', '')}")
        else:
            st.error(f"Server returned {r.status_code}: {detail}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot reach backend at `http://localhost:8000`.")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

def guess_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "gif": "image/gif", "webp": "image/webp",
            "mp4": "video/mp4", "mov": "video/quicktime"}.get(ext, "image/jpeg")

def report_status(r: dict) -> str:
    if r.get("is_resolved"):
        return "resolved"
    if r.get("is_verified"):
        return "verified"
    return "unverified"

def fmt_dt(s: Optional[str]) -> str:
    if not s:
        return "—"
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return s

def hours_elapsed(start: Optional[str], end: Optional[str]) -> Optional[float]:
    if not start or not end:
        return None
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return round((e - s).total_seconds() / 3600, 1)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Shared UI components
# ──────────────────────────────────────────────────────────────────────────────
def render_hero():
    st.markdown("""
    <div class="eco-hero">
        <p class="eco-hero-title">🌿 Eco<span>Muni</span> AI</p>
        <p class="eco-hero-sub">
            AI-powered civic issue reporting &nbsp;·&nbsp; Circular economy intelligence &nbsp;·&nbsp; Community velocity leaderboards
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_analysis_card(report: dict, key_prefix: str = ""):
    """Renders the full Gemini analysis panel for a single report."""
    sev = report.get("severity_score")
    cat = report.get("issue_category", "UNKNOWN")
    icon = CATEGORY_ICONS.get(cat, "📍")
    status = report_status(report)
    badge_cls = {"unverified": "eco-badge-red", "verified": "eco-badge-amber", "resolved": "eco-badge-green"}[status]
    sev_col = severity_color(sev)

    st.markdown(f"""
    <div class="eco-card">
        <div class="eco-card-header">
            <span style="font-size:1.4rem">{icon}</span>
            <p class="eco-card-title">Report #{report.get('id')} — {cat.replace('_',' ').title()}</p>
            <span class="eco-badge {badge_cls}">{status}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="eco-metric">
            <div class="eco-metric-val" style="color:{sev_col}">{sev or '—'}<span style="font-size:1rem">/10</span></div>
            <div class="eco-metric-label">Severity</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="eco-metric">
            <div class="eco-metric-val">{severity_label(sev)}</div>
            <div class="eco-metric-label">Risk Level</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        loc = report.get("locality_name") or "—"
        st.markdown(f"""
        <div class="eco-metric">
            <div class="eco-metric-val" style="font-size:1.1rem;padding-top:.3rem">{loc}</div>
            <div class="eco-metric-label">Locality</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        pts = report.get("velocity_points", 0)
        st.markdown(f"""
        <div class="eco-metric">
            <div class="eco-metric-val">{pts:,}</div>
            <div class="eco-metric-label">Velocity Pts</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:.75rem'></div>", unsafe_allow_html=True)

    # Bill of Materials
    # FIX: backend now returns array of strings; handle both string-item and dict-item formats
    materials_raw = report.get("materials_json")
    if materials_raw:
        try:
            bom = json.loads(materials_raw) if isinstance(materials_raw, str) else materials_raw
        except Exception:
            bom = []
        if bom:
            with st.expander("📦 Bill of Materials (BOM)", expanded=False):
                if bom and isinstance(bom[0], dict):
                    # Rich BOM (dict items with item_name, quantity, etc.)
                    rows_html = "".join(
                        f"""<tr>
                            <td><strong>{item.get('item_name','—')}</strong></td>
                            <td>{item.get('quantity','—')} {item.get('unit','')}</td>
                            <td>{item.get('purpose','—')}</td>
                            <td>{'<span class="bom-avail-yes">✓ Available</span>' if item.get('availability') == 'COMMONLY_AVAILABLE' else '<span class="bom-avail-no">⟳ Procure</span>'}</td>
                        </tr>""" for item in bom
                    )
                    st.markdown(f"""
                    <table class="bom-table">
                        <thead><tr><th>Item</th><th>Qty</th><th>Purpose</th><th>Status</th></tr></thead>
                        <tbody>{rows_html}</tbody>
                    </table>""", unsafe_allow_html=True)
                else:
                    # Simplified BOM (list of plain strings)
                    rows_html = "".join(f"<tr><td>• {str(item)}</td></tr>" for item in bom)
                    st.markdown(f"""
                    <table class="bom-table">
                        <thead><tr><th>Required Materials / Tools</th></tr></thead>
                        <tbody>{rows_html}</tbody>
                    </table>""", unsafe_allow_html=True)

    # Municipal draft email
    # FIX: backend stores autonomous_municipal_draft as a JSON-encoded plain string,
    # not a {"subject": ..., "body": ...} dict. Handle both gracefully.
    draft_raw = report.get("municipal_draft")
    if draft_raw:
        try:
            draft_parsed = json.loads(draft_raw) if isinstance(draft_raw, str) else draft_raw
        except Exception:
            draft_parsed = draft_raw  # already a plain string
        with st.expander("📧 Auto-drafted Municipal Grievance Email", expanded=False):
            if isinstance(draft_parsed, dict):
                subject = draft_parsed.get("subject", "")
                body = draft_parsed.get("body", "").replace("\\n", "\n")
                if subject:
                    st.markdown(f"**Subject:** `{subject}`")
                    st.markdown("<div style='margin:.5rem 0'></div>", unsafe_allow_html=True)
            else:
                # Plain string email body
                body = str(draft_parsed).replace("\\n", "\n")
            if body and body not in ('""', "''", ""):
                st.markdown(f'<div class="email-block">{body}</div>', unsafe_allow_html=True)
                st.markdown("<div style='margin:.5rem 0'></div>", unsafe_allow_html=True)
                if st.button("📋 Copy Email Body", key=f"{key_prefix}copy_{report.get('id')}"):
                    st.code(body, language=None)
            else:
                st.info("Email draft not available for this report.")

    # Timestamps
    with st.expander("🕐 Timeline", expanded=False):
        tc1, tc2, tc3 = st.columns(3)
        tc1.markdown(f"**Reported**\n\n{fmt_dt(report.get('reported_at'))}")
        tc2.markdown(f"**Verified**\n\n{fmt_dt(report.get('verified_at'))}")
        tc3.markdown(f"**Resolved**\n\n{fmt_dt(report.get('resolved_at'))}")
        hours = hours_elapsed(report.get("reported_at"), report.get("resolved_at"))
        if hours:
            st.info(f"⏱️ Resolved in **{hours} hours** after reporting.")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — Report & Verify
# ──────────────────────────────────────────────────────────────────────────────
def tab_report_verify():
    st.markdown("### 📷 Submit a New Civic Issue Report")
    st.markdown('<hr class="eco-divider">', unsafe_allow_html=True)

    # ── Report form ──
    with st.container():
        col_left, col_right = st.columns([1.1, 1], gap="large")

        with col_left:
            st.markdown("**Upload Photo or Video**")
            uploaded = st.file_uploader(
                "Drag & drop or click to browse",
                type=["jpg", "jpeg", "png", "webp", "gif", "mp4", "mov"],
                key="report_upload",
                label_visibility="collapsed",
            )
            if uploaded:
                if uploaded.type.startswith("image"):
                    st.image(uploaded, use_container_width=True)
                else:
                    st.video(uploaded)

        with col_right:
            st.markdown("**Citizen Details**")
            citizen_id = st.text_input("Citizen ID", placeholder="e.g. CIT-00123", key="citizen_id")
            locality = st.text_input("Locality / Ward Name", placeholder="e.g. Sector 62, Noida", key="locality")

            st.markdown("**GPS Coordinates**")
            coord_col1, coord_col2, coord_col3 = st.columns([2, 2, 1])
            with coord_col1:
                lat = st.number_input("Latitude", value=28.6139, format="%.6f", key="lat")
            with coord_col2:
                lon = st.number_input("Longitude", value=77.2090, format="%.6f", key="lon")
            with coord_col3:
                st.markdown("<div style='margin-top:1.75rem'></div>", unsafe_allow_html=True)
                def randomize_coords():
                    st.session_state["lat"] = round(28.4 + random.random() * 0.5, 6)
                    st.session_state["lon"] = round(76.9 + random.random() * 0.6, 6)
                st.button("🎲", help="Randomise coordinates near Delhi NCR", on_click=randomize_coords)

            st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
            submit_btn = st.button("🚀 Submit Report", use_container_width=True, key="submit_report")

    # ── Submission logic ──
    if submit_btn:
        if not uploaded:
            st.warning("Please upload a photo or video of the civic issue.")
        elif not citizen_id.strip():
            st.warning("Please enter a Citizen ID.")
        else:
            file_bytes = uploaded.read()
            with st.spinner("🔍 Running SynthID verification and Gemini AI analysis…"):
                result = api_post_form(
                    "/api/report",
                    data={
                        "latitude": lat,
                        "longitude": lon,
                        "citizen_id": citizen_id.strip(),
                        "locality_name": locality.strip() or "UNKNOWN",
                    },
                    file_field="image",
                    file_bytes=file_bytes,
                    filename=uploaded.name,
                    mime=guess_mime(uploaded.name),
                )
            if result:
                st.success(f"✅ Report #{result.get('id')} submitted successfully and queued for community verification.")
                st.session_state["last_report"] = result

    # Show analysis for last submitted report
    if "last_report" in st.session_state:
        st.markdown('<hr class="eco-divider">', unsafe_allow_html=True)
        st.markdown("### 🤖 AI Analysis Results")
        render_analysis_card(st.session_state["last_report"], key_prefix="tab1_")

    # ── Open cases for neighbour verification ──
    st.markdown('<hr class="eco-divider">', unsafe_allow_html=True)
    st.markdown("### 🏘️ Open Cases Awaiting Neighbour Verification")
    st.caption("Help your community by verifying issues reported nearby. Upload a corroborating photo to add weight to the report.")

    reports_data = api_get("/api/reports", params={"limit": 50})
    if reports_data is None:
        return

    unverified = [r for r in reports_data if not r.get("is_verified") and not r.get("is_resolved")]

    if not unverified:
        st.info("🎉 No unverified open cases right now. Great work, community!")
        return

    for report in unverified:
        cat = report.get("issue_category", "OTHER")
        icon = CATEGORY_ICONS.get(cat, "📍")
        sev = report.get("severity_score")
        sev_col = severity_color(sev)

        with st.container():
            st.markdown(f"""
            <div class="eco-card">
                <div class="eco-card-header">
                    <span style="font-size:1.2rem">{icon}</span>
                    <p class="eco-card-title">#{report.get('id')} — {cat.replace('_',' ').title()}</p>
                    <span class="eco-badge eco-badge-red">Unverified</span>
                    <span style="margin-left:auto;font-size:.85rem;color:{sev_col};font-weight:600">
                        Severity {sev or '?'}/10
                    </span>
                </div>
                <div style="font-size:.82rem;color:#8b949e">
                    📍 {report.get('locality_name','—')} &nbsp;·&nbsp;
                    🕐 Reported {fmt_dt(report.get('reported_at'))}
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"✅ Verify Report #{report.get('id')} — Upload Corroborating Photo"):
                v_file = st.file_uploader(
                    "Your verification photo",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"verify_upload_{report.get('id')}",
                )
                if v_file:
                    st.image(v_file, width=280)
                if st.button(f"Submit Verification for #{report.get('id')}", key=f"verify_btn_{report.get('id')}"):
                    if not v_file:
                        st.warning("Upload a photo first.")
                    else:
                        with st.spinner("Checking authenticity…"):
                            res = api_post_file(
                                f"/api/verify/{report.get('id')}",
                                v_file.read(), v_file.name, guess_mime(v_file.name)
                            )
                        if res:
                            st.success(f"✅ Report #{report.get('id')} is now marked **Verified**. Community heroes earn velocity points when this is resolved!")
                            time.sleep(1)
                            st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — Active Civic Map
# ──────────────────────────────────────────────────────────────────────────────
def tab_map():
    st.markdown("### 🗺️ Live Civic Issue Map")
    st.caption("Real-time view of all open, verified, and resolved reports in the network.")

    reports_data = api_get("/api/reports", params={"limit": 200})
    if reports_data is None:
        return

    if not reports_data:
        st.info("No reports in the system yet. Submit the first one in the Report tab!")
        return

    # Legend
    leg1, leg2, leg3, leg4 = st.columns(4)
    total = len(reports_data)
    n_unverified = sum(1 for r in reports_data if report_status(r) == "unverified")
    n_verified   = sum(1 for r in reports_data if report_status(r) == "verified")
    n_resolved   = sum(1 for r in reports_data if report_status(r) == "resolved")

    leg1.markdown(f"""<div class="eco-metric"><div class="eco-metric-val">{total}</div>
    <div class="eco-metric-label">Total Reports</div></div>""", unsafe_allow_html=True)
    leg2.markdown(f"""<div class="eco-metric"><div class="eco-metric-val" style="color:#ef4444">{n_unverified}</div>
    <div class="eco-metric-label">🔴 Unverified</div></div>""", unsafe_allow_html=True)
    leg3.markdown(f"""<div class="eco-metric"><div class="eco-metric-val" style="color:#f59e0b">{n_verified}</div>
    <div class="eco-metric-label">🟠 Verified</div></div>""", unsafe_allow_html=True)
    leg4.markdown(f"""<div class="eco-metric"><div class="eco-metric-val" style="color:#22c55e">{n_resolved}</div>
    <div class="eco-metric-label">🟢 Resolved</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)

    # Filters
    fcol1, fcol2 = st.columns([1, 3])
    with fcol1:
        status_filter = st.multiselect(
            "Filter by status",
            ["unverified", "verified", "resolved"],
            default=["unverified", "verified", "resolved"],
            key="map_status_filter",
        )

    filtered = [r for r in reports_data if report_status(r) in status_filter]

    # Try folium first, fall back to st.map
    try:
        import folium
        from streamlit_folium import st_folium

        avg_lat = sum(r.get("latitude", 28.6) for r in filtered) / max(len(filtered), 1)
        avg_lon = sum(r.get("longitude", 77.2) for r in filtered) / max(len(filtered), 1)

        m = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=12,
            tiles="CartoDB dark_matter",
        )

        STATUS_FOLIUM_COLOR = {
            "unverified": "red",
            "verified": "orange",
            "resolved": "green",
        }

        for r in filtered:
            lat_r = r.get("latitude")
            lon_r = r.get("longitude")
            if lat_r is None or lon_r is None:
                continue
            status = report_status(r)
            cat = r.get("issue_category", "OTHER")
            sev = r.get("severity_score", "?")
            popup_html = f"""
            <div style="font-family:sans-serif;min-width:180px">
                <strong>#{r.get('id')} {CATEGORY_ICONS.get(cat,'📍')} {cat.replace('_',' ').title()}</strong><br>
                <span style="color:gray">Severity: <b>{sev}/10</b></span><br>
                {r.get('locality_name','—')}<br>
                <span style="font-size:.8em;color:gray">{fmt_dt(r.get('reported_at'))}</span>
            </div>
            """
            folium.CircleMarker(
                location=[lat_r, lon_r],
                radius=8 + (r.get("severity_score") or 3),
                color=STATUS_COLORS[status],
                fill=True,
                fill_color=STATUS_COLORS[status],
                fill_opacity=0.75,
                popup=folium.Popup(popup_html, max_width=240),
                tooltip=f"#{r.get('id')} · {cat} · Sev {sev}",
            ).add_to(m)

        st_folium(m, use_container_width=True, height=520)

    except ImportError:
        # Fallback: st.map with colour approximation via size
        st.info("💡 Install `streamlit-folium` and `folium` for an interactive dark map with popups. Showing basic map now.")
        map_df = pd.DataFrame([
            {
                "lat": r.get("latitude"),
                "lon": r.get("longitude"),
                "size": (r.get("severity_score") or 3) * 400,
            }
            for r in filtered
            if r.get("latitude") and r.get("longitude")
        ])
        if not map_df.empty:
            st.map(map_df, latitude="lat", longitude="lon", size="size")

    # Report list below map
    st.markdown('<hr class="eco-divider">', unsafe_allow_html=True)
    st.markdown("### 📋 All Reports")

    for r in sorted(filtered, key=lambda x: x.get("reported_at", ""), reverse=True):
        cat = r.get("issue_category", "OTHER")
        icon = CATEGORY_ICONS.get(cat, "📍")
        status = report_status(r)
        badge_cls = {"unverified": "eco-badge-red", "verified": "eco-badge-amber", "resolved": "eco-badge-green"}[status]
        sev = r.get("severity_score")

        with st.expander(f"{icon} #{r.get('id')} — {cat.replace('_',' ').title()} | {r.get('locality_name','—')}"):
            render_analysis_card(r, key_prefix="tab2_")

            # Resolve action for verified reports
            if status == "verified":
                st.markdown("---")
                st.markdown("**📸 Upload Resolution Proof**")
                res_file = st.file_uploader(
                    "Proof photo", type=["jpg", "jpeg", "png", "webp"],
                    key=f"resolve_upload_{r.get('id')}"
                )
                if res_file:
                    st.image(res_file, width=240)
                if st.button(f"Mark #{r.get('id')} as Resolved", key=f"resolve_btn_{r.get('id')}"):
                    if not res_file:
                        st.warning("Upload a resolution proof photo first.")
                    else:
                        with st.spinner("Verifying proof and calculating velocity score…"):
                            res = api_post_file(
                                f"/api/resolve/{r.get('id')}",
                                res_file.read(), res_file.name, guess_mime(res_file.name)
                            )
                        if res:
                            # FIX: /api/resolve now returns full ReportOut (not {points_earned})
                            pts = res.get("velocity_points", 0)
                            loc = res.get("locality_name", "your locality")
                            st.success(f"🎉 Report #{r.get('id')} resolved! Earned **{pts:,} velocity points** for {loc}.")
                            time.sleep(1)
                            st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3 — Velocity Leaderboard
# ──────────────────────────────────────────────────────────────────────────────
def tab_leaderboard():
    st.markdown("### 🏆 Resolution Velocity Leaderboard")
    st.caption(
        "Rankings are based on **how fast** your locality resolves civic issues — "
        "not how few problems it has. A high score means fast, effective community action."
    )

    # Explainer callout
    st.markdown("""
    <div class="eco-card" style="border-color:#3fb95040;background:rgba(63,185,80,.05)">
        <div style="display:flex;gap:1rem;align-items:flex-start">
            <span style="font-size:1.5rem">⚡</span>
            <div>
                <p style="margin:0;font-weight:600;color:#e6edf3">How Velocity Points Work</p>
                <p style="margin:.4rem 0 0;font-size:.85rem;color:#8b949e;line-height:1.6">
                    <strong style="color:#3fb950">Points = Severity × 1000 ÷ Hours to Resolve</strong><br>
                    A severity-8 pothole fixed in 2 hours scores 4,000 pts. The same pothole left for a week scores ~47 pts.
                    Speed and seriousness both matter — resolving dangerous issues fast earns the most.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Fetching leaderboard…"):
        lb_data = api_get("/api/leaderboard", params={"limit": 20})

    if lb_data is None:
        return

    if not lb_data:
        st.info("No resolved reports yet. The leaderboard fills up as issues get resolved.")
        return

    # Summary stats
    total_resolved = sum(r.get("total_resolved", 0) for r in lb_data)
    top_score = lb_data[0].get("cumulative_velocity_score", 0) if lb_data else 0
    top_locality = lb_data[0].get("locality_name", "—") if lb_data else "—"

    sc1, sc2, sc3 = st.columns(3)
    sc1.markdown(f"""<div class="eco-metric"><div class="eco-metric-val">{len(lb_data)}</div>
    <div class="eco-metric-label">Active Localities</div></div>""", unsafe_allow_html=True)
    sc2.markdown(f"""<div class="eco-metric"><div class="eco-metric-val">{total_resolved}</div>
    <div class="eco-metric-label">Total Issues Resolved</div></div>""", unsafe_allow_html=True)
    sc3.markdown(f"""<div class="eco-metric"><div class="eco-metric-val" style="font-size:1rem;padding-top:.4rem">{top_locality}</div>
    <div class="eco-metric-label">🥇 Current Leader</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin:1.5rem 0 .75rem'></div>", unsafe_allow_html=True)

    # Rank medals
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for entry in lb_data:
        rank = entry.get("rank", 0)
        score = entry.get("cumulative_velocity_score", 0)
        resolved = entry.get("total_resolved", 0)
        name = entry.get("locality_name", "Unknown")
        medal = medals.get(rank, f"#{rank}")

        # Bar width relative to top score
        bar_pct = min(int((score / max(top_score, 1)) * 100), 100)
        avg_vel = round(score / max(resolved, 1))

        st.markdown(f"""
        <div class="lb-row">
            <div class="lb-rank">{medal}</div>
            <div style="flex:1">
                <div class="lb-name">{name}</div>
                <div class="lb-sub">{resolved} issue{'s' if resolved != 1 else ''} resolved &nbsp;·&nbsp; ~{avg_vel:,} pts/issue avg</div>
                <div class="vel-bar-bg" style="margin-top:6px">
                    <div class="vel-bar-fill" style="width:{bar_pct}%"></div>
                </div>
            </div>
            <div style="text-align:right">
                <div class="lb-score">{score:,}</div>
                <div class="lb-sub">velocity pts</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Chart
    st.markdown('<hr class="eco-divider">', unsafe_allow_html=True)
    st.markdown("#### Velocity Score Comparison")

    df_chart = pd.DataFrame([
        {"Locality": e.get("locality_name", "?"),
         "Velocity Score": e.get("cumulative_velocity_score", 0),
         "Issues Resolved": e.get("total_resolved", 0)}
        for e in lb_data
    ]).sort_values("Velocity Score", ascending=True)

    st.bar_chart(df_chart.set_index("Locality")["Velocity Score"], use_container_width=True, height=300)

    # Raw data toggle
    with st.expander("📊 Raw Leaderboard Data"):
        st.dataframe(
            pd.DataFrame(lb_data)[["rank", "locality_name", "cumulative_velocity_score", "total_resolved"]].rename(
                columns={"rank": "Rank", "locality_name": "Locality",
                         "cumulative_velocity_score": "Velocity Score", "total_resolved": "Resolved"}
            ),
            use_container_width=True,
            hide_index=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main layout
# ──────────────────────────────────────────────────────────────────────────────
def main():
    render_hero()

    tab1, tab2, tab3 = st.tabs([
        "📷  Report & Verify",
        "🗺️  Active Civic Map",
        "🏆  Velocity Leaderboard",
    ])

    with tab1:
        tab_report_verify()

    with tab2:
        tab_map()

    with tab3:
        tab_leaderboard()


if __name__ == "__main__":
    main()
