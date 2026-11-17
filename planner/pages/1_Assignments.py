from __future__ import annotations

import streamlit as st

from planner.paths import REPO_ROOT  # noqa: F401
from planner.ui.components import books_frame, decisions_frame, kpis, matrix_table
from planner.ui.state import get_service, sidebar_controls
from planner.ui.theme import fictional_banner, inject

inject()
svc = get_service()
scenario_id = sidebar_controls(svc)
fictional_banner()

st.title("Assignments")
st.caption(
    "Allocate eligible accounts in tier, then fit score, then account id. "
    "Choose the eligible AE with the lowest fill ratio, then rep id."
)

result = svc.assignment(scenario_id)
k = result["kpis"]
kpis(
    [
        ("Raw inventory", k["raw_inventory"], "All accounts in the snapshot."),
        ("Gate pass", k["gate_pass"], "qualification_gate in the scenario policy."),
        ("Policy-eligible", k["policy_eligible"], "Named-account policy."),
        ("Assignable", k["currently_assignable"], "Can receive a new named owner this cut."),
    ]
)

st.subheader("Segment × tier")
st.dataframe(matrix_table(result["matrix"]), hide_index=True, use_container_width=True)

st.subheader("CRM field readiness")
st.caption("Coverage among policy-eligible rows (plus unknown headcount). Missing fields are review exceptions.")
st.dataframe(result["field_readiness"], hide_index=True, use_container_width=True)

st.subheader("Books by rep")
st.caption("Retained customers, open opportunities, and unexpired locks count toward cap. Over-cap books are flagged.")
books = books_frame(result["books"])
st.dataframe(books, hide_index=True, use_container_width=True)

st.subheader("Future seats vs named owners")
roster = result["roster_view"]
st.dataframe(
    [
        {
            "seat_id": r["seat_id"],
            "rep_id": r["rep_id"] or "(vacant)",
            "role": r["role"],
            "segment": r["segment"],
            "territory": r["territory"],
            "start": r["start_date"],
            "named_owner_now": r["active_named"],
            "future": r["future"],
        }
        for r in roster
        if r["role"] == "AE"
    ],
    hide_index=True,
    use_container_width=True,
)

st.subheader("Proposed and retained rows")
status_filter = st.multiselect(
    "Status",
    ["PROPOSED", "RETAINED", "BLOCKED", "UNALLOCATED", "INVENTORY"],
    default=["PROPOSED", "RETAINED", "UNALLOCATED"],
)
rows = [r for r in result["rows"] if r["status"] in status_filter]
st.dataframe(decisions_frame(rows), hide_index=True, use_container_width=True)

st.download_button(
    "Export assignment CSV",
    data=svc.assignment_export(scenario_id),
    file_name="assignments.csv",
    mime="text/csv",
)
