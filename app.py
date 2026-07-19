import os
import uuid

import streamlit as st

from agent.config import OUTPUT_DIR
from agent.core import new_checkpointer, run_copilot
from agent.data_loader import load_dataframe

st.set_page_config(page_title="Data Science Co-Pilot", page_icon="📐", layout="wide")

# ---------------------------------------------------------------------------
# Design concept: an architect's desk blueprint. Off-white blueprint paper,
# navy and graphite ink, a double drafting grid behind the page, crop-marks
# on cards, technical ruler dividers, and typewriter-style corrections.
# Rotated rubber stamps with animated bouncy slam-down for Approved status.
# Dense two-column layout keeps everything above the fold.
# ---------------------------------------------------------------------------
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Work+Sans:wght@400;500;600;700&family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Architects+Daughter&display=swap" rel="stylesheet">
<style>
:root {
    --paper: #F3F1E9;      /* Off-white blueprint paper background */
    --insert: #FAFAF7;     /* Clean sheet insert */
    --ink: #2B2E33;        /* Graphite ink color */
    --muted: #6E7278;      /* Faded graphite pencil */
    --border: #C8CBCD;     /* Thin pencil frame borders */
    --navy: #1C3B57;       /* Technical drawing blueprint navy */
    --revision: #B33A2E;   /* Red marking ink */
    --approved: #2F6B4F;   /* Green verification stamp */
    --drafting: #A67C2E;   /* Yellow drafting pencil */
}

/* Base application styling */
.stApp {
    background-color: var(--paper) !important;
    background-image:
        linear-gradient(rgba(28, 59, 87, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(28, 59, 87, 0.04) 1px, transparent 1px),
        linear-gradient(rgba(28, 59, 87, 0.015) 5px, transparent 5px),
        linear-gradient(90deg, rgba(28, 59, 87, 0.015) 5px, transparent 5px) !important;
    background-size: 50px 50px, 50px 50px, 10px 10px, 10px 10px !important;
}

html, body, [class*="css"] {
    font-family: 'Work Sans', sans-serif;
    color: var(--ink);
}

/* Density tweaks for containers */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}
[data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stVerticalBlock"] > div {
    padding-bottom: 0.3rem !important;
}

/* Headings typography */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    color: var(--navy) !important;
    letter-spacing: 0.02em !important;
}

/* Corner crop marks (registration marks) */
.crop-card {
    position: relative;
    background: var(--insert);
    border: 1px solid var(--border);
    padding: 1rem;
    box-sizing: border-box;
}
.crop-card::before {
    content: "";
    position: absolute;
    top: -4px; left: -4px; right: -4px; height: 12px;
    background:
        linear-gradient(to right, var(--navy) 1.5px, transparent 1.5px) 0 0 / 12px 1.5px no-repeat,
        linear-gradient(to bottom, var(--navy) 1.5px, transparent 1.5px) 0 0 / 1.5px 12px no-repeat,
        linear-gradient(to left, var(--navy) 1.5px, transparent 1.5px) 100% 0 / 12px 1.5px no-repeat,
        linear-gradient(to bottom, var(--navy) 1.5px, transparent 1.5px) 100% 0 / 1.5px 12px no-repeat;
    pointer-events: none;
}
.crop-card::after {
    content: "";
    position: absolute;
    bottom: -4px; left: -4px; right: -4px; height: 12px;
    background:
        linear-gradient(to right, var(--navy) 1.5px, transparent 1.5px) 0 100% / 12px 1.5px no-repeat,
        linear-gradient(to top, var(--navy) 1.5px, transparent 1.5px) 0 100% / 1.5px 12px no-repeat,
        linear-gradient(to left, var(--navy) 1.5px, transparent 1.5px) 100% 100% / 12px 1.5px no-repeat,
        linear-gradient(to top, var(--navy) 1.5px, transparent 1.5px) 100% 100% / 1.5px 12px no-repeat;
    pointer-events: none;
}

/* Title block header tag */
.sheet-header {
    border-bottom: 2px solid var(--navy);
    padding-bottom: 8px;
    margin-bottom: 12px;
}
.sheet-tag {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    color: var(--muted);
    text-transform: uppercase;
}
.case-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800;
    font-size: 2.1rem;
    color: var(--navy);
    margin: 2px 0;
    letter-spacing: -0.01em;
    line-height: 1.1;
    text-transform: uppercase;
}
.case-subtitle {
    font-family: 'Work Sans', sans-serif;
    color: var(--ink);
    font-size: 0.85rem;
    max-width: 90%;
    line-height: 1.4;
}
.provider-stamp {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    color: var(--navy);
    border: 2px solid var(--navy);
    padding: 4px 12px;
    transform: rotate(-2deg);
    text-transform: uppercase;
    font-weight: 700;
    box-shadow: 0 0 0 1px var(--navy);
}

/* Ruler tick divider styling */
.ruler {
    height: 18px;
    margin: 0.8rem 0;
    border-bottom: 1.5px solid var(--navy);
    position: relative;
}
.ruler::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 9px;
    background-image:
        repeating-linear-gradient(90deg, var(--navy) 0, var(--navy) 1.5px, transparent 1.5px, transparent 40px),
        repeating-linear-gradient(90deg, var(--navy) 0, var(--navy) 1px, transparent 1px, transparent 20px),
        repeating-linear-gradient(90deg, var(--muted) 0, var(--muted) 1px, transparent 1px, transparent 5px);
    background-size: 100% 9px, 100% 6px, 100% 4px;
    background-repeat: repeat-x;
    opacity: 0.8;
}

/* Action block labels */
.tag-no {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.annotation {
    font-family: 'Architects Daughter', cursive;
    font-size: 0.8rem;
    color: var(--navy);
    line-height: 1.2;
}

/* Cleaning log */
.cleaning-note {
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: var(--ink);
    padding: 8px 12px;
    border-left: 3px solid var(--drafting);
    background: rgba(166, 124, 46, 0.05);
    margin-bottom: 1rem;
}

/* Revision log heading */
.case-log-heading {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    color: var(--muted);
    text-transform: uppercase;
    margin: 0.4rem 0 0.6rem 0;
    border-bottom: 1.5px solid var(--navy);
    padding-bottom: 4px;
}

/* Timeline trace */
.timeline {
    position: relative;
    padding-left: 26px;
    margin: 0.5rem 0 1.2rem 0;
}
.timeline::before {
    content: "";
    position: absolute;
    left: 7px;
    top: 6px;
    bottom: 6px;
    border-left: 2px dashed var(--navy);
    opacity: 0.35;
}
.entry {
    position: relative;
    background: var(--insert);
    border: 1px solid var(--border);
    border-left: 4px solid var(--muted);
    padding: 0.8rem 1.1rem;
    margin-bottom: 0.8rem;
}
.entry::before {
    content: "";
    position: absolute;
    left: -23px;
    top: 1.1rem;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--muted);
    border: 2px solid var(--paper);
    box-shadow: 0 0 0 1px var(--navy);
}

.entry.surveyed { border-left-color: var(--navy); }
.entry.surveyed::before { background: var(--navy); }
.entry.spec { border-left-color: var(--navy); }
.entry.spec::before { background: var(--navy); }
.entry.revision { border-left-color: var(--revision); }
.entry.revision::before { background: var(--revision); }
.entry.approved { border-left-color: var(--approved); }
.entry.approved::before { background: var(--approved); }
.entry.drafting { border-left-color: var(--drafting); }
.entry.drafting::before { background: var(--drafting); }

/* Stamp slam down animation */
@keyframes stampSlam {
    0% {
        transform: scale(2.2) rotate(15deg);
        opacity: 0;
        filter: blur(1.5px);
    }
    45% {
        transform: scale(0.92) rotate(-6deg);
        opacity: 0.9;
    }
    70% {
        transform: scale(1.08) rotate(1deg);
        opacity: 0.95;
    }
    100% {
        transform: scale(1) rotate(-3deg);
        opacity: 1;
        filter: none;
    }
}

.stamp {
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 8px;
    border: 2px solid currentColor;
    background: transparent;
    display: inline-block;
    float: right;
    margin-top: -2px;
}
.entry.surveyed .stamp  { color: var(--navy); transform: rotate(-2.5deg); }
.entry.spec .stamp      { color: var(--navy); transform: rotate(1.2deg); }
.entry.revision .stamp  { color: var(--revision); transform: rotate(-5deg); }
.entry.approved .stamp  { color: var(--approved); animation: stampSlam 0.4s cubic-bezier(0.18, 0.89, 0.32, 1.28) both; }
.entry.drafting .stamp  { color: var(--drafting); transform: rotate(2deg); }

.entry-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
    font-weight: 700;
}
.entry-tool {
    font-family: 'Space Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--navy);
}
.entry-code {
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    background: #EAE8DF; /* Blueprint-matching shaded off-white for code */
    border: 1px solid var(--border);
    padding: 8px 12px;
    margin-top: 6px;
    white-space: pre-wrap;
    word-break: break-all;
    color: var(--ink);
}
.entry-revision-text {
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    color: var(--revision);
    background-color: rgba(179, 58, 46, 0.05);
    border-left: 2px solid var(--revision);
    padding: 8px 12px;
    margin-top: 8px;
    white-space: pre-wrap;
    word-break: break-all;
}
.entry-spec-text {
    font-family: 'Space Mono', monospace;
    font-size: 0.76rem;
    color: var(--navy);
    margin-top: 0.45rem;
    white-space: pre-wrap;
}

/* Collapsible Code elements */
.entry details { margin-top: 0.5rem; }
.entry summary {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    cursor: pointer;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 2px 0;
}
.entry summary:hover { color: var(--navy); }

/* Findings card & details */
.findings-card {
    background: var(--insert);
    border: 1px solid var(--border);
    padding: 1rem;
    font-family: 'Work Sans', sans-serif;
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--ink);
}

.chart-frame {
    background: var(--insert);
    padding: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    max-width: 100%;
}
.chart-frame img {
    max-height: 250px !important;
    width: auto !important;
    max-width: 100% !important;
    object-fit: contain !important;
    display: block;
}

/* Follow-up question label styling */
.followup-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    color: var(--muted);
    text-transform: uppercase;
    margin: 1rem 0 0.4rem 0;
}

/* --- Native Streamlit widget overrides --- */
[data-testid="stFileUploaderDropzone"] {
    background: var(--insert) !important;
    border: 1.5px dashed var(--navy) !important;
    border-radius: 0px !important;
    padding: 1rem !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--navy) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small {
    font-family: 'Space Mono', monospace !important;
    color: var(--muted) !important;
}
[data-testid="stFileUploader"] button {
    background: var(--insert) !important;
    color: var(--navy) !important;
    border: 1px solid var(--navy) !important;
    border-radius: 0px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}
[data-testid="stFileUploader"] button:hover {
    background: var(--navy) !important;
    color: var(--insert) !important;
}
[data-testid="stFileUploaderFile"] {
    background: var(--insert) !important;
    border: 1px solid var(--navy) !important;
    border-radius: 0px !important;
}
[data-testid="stFileUploaderFileName"] {
    font-family: 'Space Mono', monospace !important;
    color: var(--ink) !important;
}
[data-testid="stTextArea"] textarea {
    background: var(--insert) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 0px !important;
    color: var(--ink) !important;
    font-family: 'Work Sans', sans-serif !important;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--navy) !important;
    box-shadow: none !important;
}
.stButton button {
    background: var(--navy) !important;
    color: var(--insert) !important;
    border: 1px solid var(--navy) !important;
    border-radius: 0px !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    font-size: 0.78rem !important;
    padding: 0.5rem 1.3rem !important;
    box-shadow: none !important;
    transition: all 0.15s ease-in-out !important;
}
.stButton button:hover {
    background: var(--paper) !important;
    color: var(--navy) !important;
    border-color: var(--navy) !important;
}
.stButton button:disabled {
    background: var(--border) !important;
    color: var(--muted) !important;
    border-color: var(--border) !important;
}
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 0px !important;
    background: var(--insert) !important;
    box-shadow: none !important;
    margin-bottom: 0.5rem !important;
}
[data-testid="stExpander"] details {
    padding: 0 !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
    color: var(--navy) !important;
    font-weight: 700 !important;
    padding: 8px 12px !important;
    border-radius: 0px !important;
    background-color: rgba(28, 59, 87, 0.02) !important;
}
[data-testid="stExpander"] summary:hover {
    background-color: rgba(28, 59, 87, 0.05) !important;
}
[data-testid="stExpander"] p {
    font-family: 'Work Sans', sans-serif !important;
    font-size: 0.85rem !important;
    color: var(--ink) !important;
}

/* Custom design for Streamlit Alerts */
div[data-testid="stAlert"] {
    background-color: var(--insert) !important;
    border: 1px solid var(--border) !important;
    border-left: 4px solid var(--navy) !important;
    color: var(--ink) !important;
    border-radius: 0px !important;
}
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
    color: var(--ink) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* Custom design for Streamlit Spinner */
[data-testid="stSpinner"] {
    background-color: rgba(28, 59, 87, 0.06) !important;
    border: 1px dashed var(--navy) !important;
    border-radius: 0px !important;
    padding: 10px 16px !important;
    margin: 8px 0 !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    color: var(--navy) !important;
}
[data-testid="stSpinner"] svg {
    stroke: var(--navy) !important;
    fill: var(--navy) !important;
    color: var(--navy) !important;
}
[data-testid="stSpinner"] p, [data-testid="stSpinner"] div {
    color: var(--navy) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
}
</style>
""")


def esc(text: str) -> str:
    """Escape a string for safe raw HTML embedding -- prevents the agent's
    own text from ever being interpreted as markdown/LaTeX/HTML."""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("$", "&#36;"))


# def render_findings(insights_text: str):
#     """Structured findings card: a navy header bar plus a cleanly bulleted
#     body -- replaces the earlier flat, unstyled <ul>."""
#     lines = [line.strip("-* ").strip() for line in insights_text.split("\n") if line.strip()]
#     items = "".join(f"<li>{esc(line)}</li>" for line in lines if line)
#     st.markdown(
#         f'<div class="findings-card crop-card">'
#         f'<div class="findings-header">Findings &amp; Technical Specifications</div>'
#         f'<div class="findings-body">{"<ul>" + items + "</ul>" if items else "<em>No findings text returned.</em>"}</div>'
#         f'</div>',
#         unsafe_allow_html=True,
#     )

def render_findings(insights_text: str):
    """Structured findings card: Parses text into technical blocks and metadata
    key-values, displayed matching the architect/blueprint theme without emojis."""
    lines = [line.strip("-* ").strip() for line in insights_text.split("\n") if line.strip()]

    if not lines:
        st.markdown(
            f'<div class="findings-card crop-card">'
            f'<div class="findings-header" style="font-family:\'Space Mono\', monospace; font-size:0.8rem; color:var(--navy); font-weight:700; border-bottom:1px solid var(--border); padding-bottom:4px; margin-bottom:8px;">FINDINGS &amp; TECHNICAL SPECIFICATIONS</div>'
            f'<div class="findings-body"><em>No findings text returned.</em></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    html_output = []
    html_output.append('<div class="findings-card crop-card">')
    html_output.append(
        '<div class="findings-header" style="font-family:\'Space Mono\', monospace; font-size:0.8rem; color:var(--navy); font-weight:700; border-bottom:1px solid var(--border); padding-bottom:4px; margin-bottom:12px; text-transform:uppercase; letter-spacing:0.05em;">FINDINGS &amp; TECHNICAL SPECIFICATIONS</div>')

    technical_notes = []
    data_metrics = []

    for line in lines:
        # Check if the line is a key-value pair (e.g., "Total Revenue: $5,000" or "Metric - Value")
        if ":" in line and len(line.split(":", 1)[0]) < 30:
            key, val = line.split(":", 1)
            data_metrics.append((key.strip(), val.strip()))
        elif " - " in line and len(line.split(" - ", 1)[0]) < 30:
            key, val = line.split(" - ", 1)
            data_metrics.append((key.strip(), val.strip()))
        else:
            technical_notes.append(line)

    # Render descriptive points as numbered schematic logs
    if technical_notes:
        html_output.append('<div style="margin-bottom: 12px;">')
        for idx, note in enumerate(technical_notes, 1):
            html_output.append(
                f'<div style="margin-bottom: 8px; font-family:\'Work Sans\', sans-serif; font-size:0.85rem; line-height:1.5; display:flex; align-items:flex-start;">'
                f'<span style="font-family:\'Space Mono\', monospace; font-size:0.75rem; color:var(--navy); font-weight:700; min-width:30px; display:inline-block;">[{idx:02d}]</span>'
                f'<span style="color:var(--ink);">{esc(note)}</span>'
                f'</div>'
            )
        html_output.append('</div>')

    # Render metric/key-value logs inside a blueprint data grid
    if data_metrics:
        if technical_notes:
            html_output.append('<div style="border-top: 1px dashed var(--border); margin: 12px 0;"></div>')

        html_output.append(
            '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px;">')
        for key, val in data_metrics:
            html_output.append(
                f'<div style="background: rgba(28, 59, 87, 0.02); border: 1px solid var(--border); padding: 6px 10px;">'
                f'<div style="font-family:\'Space Mono\', monospace; font-size:0.65rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.02em;">{esc(key)}</div>'
                f'<div style="font-family:\'Space Mono\', monospace; font-size:0.82rem; color:var(--navy); font-weight:700; margin-top:2px;">{esc(val)}</div>'
                f'</div>'
            )
        html_output.append('</div>')

    html_output.append('</div>')

    st.markdown("".join(html_output), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Title block
# ---------------------------------------------------------------------------
st.markdown('<div class="sheet-tag">Sheet No. 001 &middot; Data Analysis Spec</div>', unsafe_allow_html=True)

header_col, pill_col = st.columns([5, 2])
with header_col:
    st.markdown('<div class="case-title">📐 Autonomous Data Science Co-Pilot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="case-subtitle">A self-correcting blueprint execution agent. Upload a structured '
        'dataset, ask an analysis query, and monitor real-time code executions and documentation lookups.</div>',
        unsafe_allow_html=True
    )
with pill_col:
    st.markdown(
        f'<div style="text-align:right; padding-top:14px;">'
        f'<span class="provider-stamp">{esc(os.getenv("LLM_PROVIDER", "LLM CORE ENGINE"))}</span></div>',
        unsafe_allow_html=True
    )
st.markdown('<div class="ruler"></div>', unsafe_allow_html=True)

# Define columns for the dense side-by-side design layout
main_col, log_col = st.columns([5, 6])

with main_col:
    # ---------------------------------------------------------------------------
    # Action card: Upload + Query
    # ---------------------------------------------------------------------------
    st.markdown('<div class="crop-card" style="padding: 15px; margin-bottom: 12px;">', unsafe_allow_html=True)

    col_u, col_q = st.columns([1, 1])
    with col_u:
        st.markdown('<div class="tag-no" style="margin-bottom: 6px;">1. CHOOSE BLUEPRINT DATASET</div>',
                    unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload your data file", type=["csv", "xlsx", "json", "xls"],
                                         label_visibility="collapsed")
    with col_q:
        st.markdown('<div class="tag-no" style="margin-bottom: 6px;">2. SPECIFY ANALYSIS INSTRUCTIONS</div>',
                    unsafe_allow_html=True)
        user_request = st.text_area(
            "What do you want to know?",
            placeholder="e.g. Show me total revenue by region as a bar chart.",
            height=70,
            label_visibility="collapsed",
        )

    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)

    col_b, col_a = st.columns([2, 3])
    with col_b:
        run_clicked = st.button("RUN ANALYSIS SEQUENCE", type="primary", disabled=uploaded_file is None,
                                use_container_width=True)
    with col_a:
        st.markdown(
            '<div class="annotation" style="padding-top: 8px; font-size: 0.75rem;">← Compile, execute, and revise autonomously</div>',
            unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        # New file -> fresh checkpointer + fresh thread_id, so a follow-up
        # question can never accidentally reference a previous file's data.
        if st.session_state.get("uploaded_file_name") != uploaded_file.name:
            st.session_state["uploaded_file_name"] = uploaded_file.name
            st.session_state["checkpointer"] = new_checkpointer()
            st.session_state["thread_id"] = str(uuid.uuid4())
            st.session_state.pop("result_history", None)

        try:
            df = load_dataframe(file_bytes=uploaded_file.getvalue(), filename=uploaded_file.name)
            st.session_state["df_preview"] = df
            with st.expander("Preview dataset schema & head", expanded=False):
                st.dataframe(df.head(10), use_container_width=True)
                st.markdown(
                    f'<div class="tag-no" style="margin-top: 6px;">Dimensions: {df.shape[0]} rows &middot; {df.shape[1]} columns</div>',
                    unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Could not read this file: {e}")
            st.stop()

# ---------------------------------------------------------------------------
# Execution and Result Retrieval
# ---------------------------------------------------------------------------
if run_clicked:
    df = st.session_state.get("df_preview")
    if df is None:
        st.error("Please upload a valid file first.")
        st.stop()

    request_text = user_request.strip() or (
        "Explore this dataset, surface the most important patterns, and "
        "create the single most informative chart."
    )

    with st.spinner("Surveying the data and drafting an analysis..."):
        try:
            result = run_copilot(
                df, user_request=request_text, output_dir=OUTPUT_DIR,
                checkpointer=st.session_state["checkpointer"],
                thread_id=st.session_state["thread_id"],
            )
            # A fresh "Run analysis" click starts a brand-new results
            # history for this file, so old follow-ups from a previous
            # question don't linger underneath a new initial analysis.
            st.session_state["result_history"] = [("Initial analysis", request_text, result)]
        except EnvironmentError as e:
            st.error(f"Configuration error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"The agent crashed unexpectedly: {e}")
            st.stop()

# Render results (if any analysis has been run for the current file)
if "result_history" in st.session_state:
    history = st.session_state["result_history"]
    latest_label, latest_request, latest_result = history[-1]

    with main_col:
        for label, question, result in history:
            st.markdown(f'<div class="tag-no" style="margin-top:10px;">{esc(label)}: {esc(question)}</div>', unsafe_allow_html=True)

            if not result.success:
                st.error(f"The agent could not complete this request. {result.error or ''}")
                continue

            if result.chart_paths:
                st.markdown('<div class="case-log-heading" style="margin-top: 8px;">Result Exhibits</div>',
                            unsafe_allow_html=True)
                cols = st.columns(min(3, len(result.chart_paths)))
                for i, path in enumerate(result.chart_paths):
                    with cols[i % len(cols)]:
                        st.markdown('<div class="chart-frame crop-card">', unsafe_allow_html=True)
                        st.image(path, width=320)
                        st.markdown(
                            '<div class="annotation" style="font-size:0.7rem; text-align:center; margin-top:5px;">EXHIBIT ' + chr(
                                65 + i) + ' &middot; PLOT OUTPUT</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(
                '<div class="case-log-heading" style="margin-top: 10px;">Analysis Output</div>',
                unsafe_allow_html=True)
            render_findings(result.insights)

            with st.expander(f"Schema profile ({label})"):
                schema_step = next((s for s in result.steps if s.tool_name == "get_dataframe_schema"), None)
                if schema_step:
                    st.json(schema_step.tool_output)
                else:
                    st.caption("Not re-checked this turn -- using the schema from the initial analysis.")

            st.markdown('<hr style="border:none;border-top:1px dashed var(--border);margin:1rem 0;">', unsafe_allow_html=True)

        # --- Follow-up question, appended to history rather than replacing it ---
        st.markdown('<div class="followup-label">Ask a follow-up about this dataset</div>', unsafe_allow_html=True)
        followup_text = st.text_area(
            "Follow-up question",
            placeholder="e.g. What about units sold instead of revenue?",
            height=70,
            label_visibility="collapsed",
            key="followup_input",
        )
        followup_clicked = st.button("Ask follow-up", key="followup_button")

        if followup_clicked and followup_text.strip():
            df = st.session_state.get("df_preview")
            with st.spinner("Considering the follow-up..."):
                try:
                    followup_result = run_copilot(
                        df, user_request=followup_text.strip(), output_dir=OUTPUT_DIR,
                        checkpointer=st.session_state["checkpointer"],
                        thread_id=st.session_state["thread_id"],
                    )
                    label = f"Follow-up {len(history)}"
                    st.session_state["result_history"].append((label, followup_text.strip(), followup_result))
                    st.rerun()
                except Exception as e:
                    st.error(f"The agent crashed unexpectedly: {e}")

    # Right side: Revision Log -- always shows only the MOST RECENT turn's trace
    with log_col:
        result = latest_result
        if result.cleaning_log:
            note = " · ".join(esc(line) for line in result.cleaning_log)
            st.markdown(f'<div class="cleaning-note">🖊 {note}</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="case-log-heading">Revision Log &middot; {esc(latest_label)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="timeline">', unsafe_allow_html=True)

        for i, step in enumerate(result.steps, 1):
            out = step.tool_output if isinstance(step.tool_output, dict) else {}
            status = out.get("status")

            if step.tool_name == "get_dataframe_schema":
                css_class, stamp = "surveyed", "Surveyed"
            elif step.tool_name == "search_documentation":
                css_class, stamp = "spec", "Spec Consulted"
            elif status == "error":
                css_class, stamp = "revision", "Revision Needed"
            elif status == "success":
                css_class, stamp = "approved", "Approved"
            else:
                css_class, stamp = "drafting", "Drafting"

            entry = f'<div class="entry crop-card {css_class}">'
            entry += f'<span class="stamp">{esc(stamp)}</span>'
            entry += f'<span class="entry-label">Entry {i:02d}</span> &nbsp; <span class="entry-tool">{esc(step.tool_name)}</span>'

            if step.tool_name == "run_python_code":
                code = step.tool_input.get("code", "")
                if status == "error":
                    entry += f'<details open><summary>Code attempted</summary><div class="entry-code">{esc(code)}</div></details>'
                    entry += f'<div class="entry-revision-text">{esc(str(out.get("error", "")))}</div>'
                else:
                    entry += f'<details><summary>Show code</summary><div class="entry-code">{esc(code)}</div></details>'
                    if status == "success" and out.get("stdout"):
                        entry += f'<details><summary>Show output</summary><div class="entry-code">{esc(out["stdout"])}</div></details>'
            elif step.tool_name == "search_documentation":
                raw = out.get("raw", "")
                preview = raw[:300] + ("…" if len(raw) > 300 else "")
                entry += f'<details><summary>Reference retrieved</summary><div class="entry-spec-text">{esc(preview)}</div></details>'

            entry += '</div>'
            st.markdown(entry, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

else:
    # Default state for the right side, shown before any analysis has run
    with log_col:
        st.markdown('<div class="case-log-heading">System Blueprint Specifications</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="crop-card" style="margin-top: 5px;">
            <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; line-height: 1.6; color: var(--ink);">
                <span style="color: var(--navy); font-weight: 700;">SPEC-SHEET NO:</span> KYS-CO-6751<br>
                <span style="color: var(--navy); font-weight: 700;">AGENT TYPE:</span> Autonomous Data Analyst (LangGraph)<br>
                <span style="color: var(--navy); font-weight: 700;">RETRY LOOP:</span> Document-Retrieval Self-Correction<br>
                <span style="color: var(--navy); font-weight: 700;">SANDBOX ENVIRONMENT:</span> Python REPL v3.11<br>
                <span style="color: var(--navy); font-weight: 700;">DIVIDER CODE:</span> ANSI-IEEE-754<br>
            </div>
            <div class="ruler" style="height: 12px; margin: 12px 0 8px 0;"></div>
            <div class="annotation" style="font-size: 0.75rem; color: var(--muted); margin-top: 4px;">
                * Ready to survey uploaded dataset.<br>
                * Will compile code, detect exceptions, consult references, and revise dynamically.
            </div>
        </div>
        """, unsafe_allow_html=True)