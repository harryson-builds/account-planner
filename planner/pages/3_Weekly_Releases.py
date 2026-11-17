from __future__ import annotations

from datetime import date

import streamlit as st

from planner.paths import REPO_ROOT  # noqa: F401
from planner.ui.state import get_service, sidebar_controls
from planner.ui.theme import fictional_banner, inject

inject()
svc = get_service()
scenario_id = sidebar_controls(svc)
fictional_banner()

st.title("Weekly releases")
st.caption(
    "Release approved proposals in one transaction. Rechecks ownership, staff, protections, "
    "capacity, and duplicate active ownership. The same batch id on the same snapshot and scenario "
    "is idempotent. Reusing that id after a new import is rejected. Re-review if the proposed owner moved."
)

result = svc.assignment(scenario_id)
approved = [r for r in result["rows"] if r.get("status") == "PROPOSED" and r.get("review_decision") == "approve"]
st.metric("Approved for release", len(approved))
if approved:
    st.dataframe(
        [
            {
                "account_id": r["account_id"],
                "name": r["display_name"],
                "from": r.get("owner_id"),
                "to": r.get("proposed_owner_id"),
                "reviewer": r.get("reviewer"),
            }
            for r in approved
        ],
        hide_index=True,
        use_container_width=True,
    )

week = st.text_input("Batch id", value=f"FY27-W{date.today().isocalendar().week:02d}")
reviewer = st.text_input("Released by", value=st.session_state.get("reviewer", "Riley Chen"))

if st.button("Release approved batch", type="primary"):
    outcome = svc.release(scenario_id, week.strip(), reviewer)
    st.session_state["last_release"] = outcome
    st.rerun()

outcome = st.session_state.get("last_release")
if outcome:
    st.subheader(f"Last result: {outcome['status']}")
    if outcome.get("message"):
        st.warning(outcome["message"])
    if outcome.get("conflicts"):
        st.error("Batch left pending. Ledger was not written.")
        st.dataframe(outcome["conflicts"], hide_index=True, use_container_width=True)
    if outcome.get("result"):
        st.json(outcome["result"])

st.subheader("Release ledger (local)")
ledger = svc.ledger()
if not ledger:
    st.info("No releases yet. The ledger is local SQLite; nothing is pushed to a CRM.")
else:
    st.dataframe(ledger, hide_index=True, use_container_width=True)
