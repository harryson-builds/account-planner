"""Warm-neutral Streamlit chrome. Original to this app; not copied from the workbook."""

from __future__ import annotations

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="stApp"] {
  font-family: "IBM Plex Sans", sans-serif;
  color: #1c1914;
}
.stApp { background: #f4f1ea; }
.block-container { padding-top: 1.2rem; max-width: 1280px; }
header[data-testid="stHeader"] { background: #f4f1ea; }
section[data-testid="stSidebar"] { background: #ebe6db; }
.banner {
  background: #efe6c9;
  border: 1px solid #d9c98a;
  color: #5c4a12;
  padding: 0.55rem 0.8rem;
  font-size: 0.85rem;
  border-radius: 6px;
  margin-bottom: 0.9rem;
}
.kpi-row { display: flex; gap: 0.7rem; flex-wrap: wrap; }
.kpi {
  background: #fffdf8;
  border: 1px solid #e4dccb;
  border-radius: 8px;
  padding: 0.7rem 0.85rem;
  min-width: 160px;
  flex: 1;
}
.kpi .label { font-size: 0.72rem; letter-spacing: 0.04em; text-transform: uppercase; color: #6f675c; }
.kpi .value { font-family: "IBM Plex Mono", monospace; font-size: 1.45rem; color: #0f4c3a; font-weight: 600; }
.kpi .hint { font-size: 0.75rem; color: #6f675c; margin-top: 0.15rem; }
.status {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  border: 1px solid transparent;
}
.status-pass { background: #dceee4; color: #0f4c3a; border-color: #b7d8c6; }
.status-block { background: #f8e4dc; color: #7a2e16; border-color: #ecc3b3; }
.status-hold { background: #efe6c9; color: #5c4a12; border-color: #d9c98a; }
.status-info { background: #e4ecec; color: #1d3c3c; border-color: #c5d4d4; }
h1, h2, h3 { color: #1c1914; }
[data-testid="stMetric"] {
  background: #fffdf8;
  border: 1px solid #e4dccb;
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
}
[data-testid="stMetric"] label { color: #6f675c !important; }
div[data-testid="stDataFrame"] { border: 1px solid #e4dccb; }
.small { font-size: 0.8rem; color: #6f675c; }
hr { border-color: #e4dccb; }
</style>
"""


def inject() -> None:
    st.set_page_config(
        page_title="Account Assignment & Capacity Planner",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)


def fictional_banner() -> None:
    st.markdown(
        '<div class="banner"><strong>Fictional planning snapshot.</strong> '
        "Sample outputs are labeled fictional. Modeled ARR is a scenario estimate, "
        "not historical bookings or pipeline.</div>",
        unsafe_allow_html=True,
    )
