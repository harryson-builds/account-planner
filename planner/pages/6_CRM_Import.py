from __future__ import annotations

from datetime import date

import streamlit as st

from planner.paths import DEMO_DIR, TEMPLATE_DIR
from planner.ui.state import get_service, sidebar_controls
from planner.ui.theme import fictional_banner, inject

inject()
svc = get_service()
sidebar_controls(svc)
fictional_banner()

st.title("CRM import")
st.caption(
    "Read-only relative to any CRM. Valid files replace the working snapshot. "
    "Invalid files keep the last valid snapshot. Import never writes the release ledger."
)

st.markdown(
    f"Templates: `{TEMPLATE_DIR}` · Demo: `{DEMO_DIR}`. "
    "See the [data dictionary](../docs/data_dictionary.md)."
)

snapshot_date = st.date_input("Snapshot date", value=date(2026, 2, 1))
accounts = st.file_uploader("Accounts CSV", type=["csv"])
roster = st.file_uploader("Roster CSV", type=["csv"])
activities = st.file_uploader("Activities CSV", type=["csv"])

cols = st.columns(2)
with cols[0]:
    if st.button("Reload fictional demo"):
        from planner.repo.seed import load_demo

        snap_id = load_demo(svc.db)
        st.success(f"Demo snapshot {snap_id} loaded. Ledger unchanged.")
        st.rerun()
with cols[1]:
    run = st.button("Validate and load", type="primary")

if run:
    if not (accounts and roster and activities):
        st.error("Upload all three files.")
    else:
        result = svc.import_csv(
            accounts,
            roster,
            activities,
            snapshot_date=snapshot_date,
            source="csv",
        )
        if result.ok:
            st.success("Snapshot stored. Previous valid snapshot remains in history.")
        else:
            st.error("Validation failed. Last valid snapshot is still current.")
            st.dataframe(result.error_table(), hide_index=True, use_container_width=True)

st.subheader("Snapshots on disk")
st.dataframe(svc.db.list_snapshots(), hide_index=True, use_container_width=True)

st.subheader("Ledger rows (must not change on failed import)")
st.metric("Ledger count", svc.db.ledger_count())
