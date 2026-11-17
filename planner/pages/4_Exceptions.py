from __future__ import annotations

import streamlit as st

from planner.paths import REPO_ROOT  # noqa: F401
from planner.ui.state import get_service, sidebar_controls
from planner.ui.theme import fictional_banner, inject

inject()
svc = get_service()
scenario_id = sidebar_controls(svc)
fictional_banner()

st.title("Exceptions")
st.caption("Blocked rows, stale CRM segments, over-cap books, parent-child routing, and below-viable books.")

result = svc.assignment(scenario_id)
ex = result["exceptions"]
codes = sorted({e["reason_code"] for e in ex})
picked = st.multiselect("Reason", codes, default=codes)
filtered = [e for e in ex if e["reason_code"] in picked]
st.metric("Exception rows", len(filtered))
st.dataframe(filtered, hide_index=True, use_container_width=True)

st.download_button(
    "Export exception CSV",
    data=svc.exception_export(scenario_id),
    file_name="exceptions.csv",
    mime="text/csv",
)

st.subheader("Helio Analytics walkthrough (seeded)")
row = next((r for r in result["rows"] if r["account_id"] == "ACC-0001"), None)
if row:
    st.json(row)
