from __future__ import annotations

import streamlit as st

from planner.service import PlannerService


def get_service() -> PlannerService:
    if "planner_service" not in st.session_state:
        st.session_state.planner_service = PlannerService()
    return st.session_state.planner_service


def sidebar_controls(svc: PlannerService) -> str:
    scenarios = svc.scenarios()
    ids = [s.id for s in scenarios]
    names = {s.id: f"{s.name} ({s.id})" for s in scenarios}
    current = st.session_state.get("scenario_id", "baseline")
    if current not in ids:
        current = ids[0]
    choice = st.sidebar.selectbox(
        "Scenario",
        ids,
        index=ids.index(current),
        format_func=lambda i: names[i],
    )
    st.session_state.scenario_id = choice
    sid, snap = svc.snapshot_record()
    st.sidebar.caption(
        f"Snapshot {sid} · {snap.snapshot_date.isoformat()} · {snap.source} · "
        f"{len(snap.accounts)} accounts · rule {svc.scenario(choice).version}"
    )
    st.sidebar.caption("Bound to 127.0.0.1 · local SQLite ledger · CRM import is read-only.")
    return choice
