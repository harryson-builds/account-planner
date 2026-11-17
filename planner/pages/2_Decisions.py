from __future__ import annotations

import pandas as pd
import streamlit as st

from planner.paths import REPO_ROOT  # noqa: F401
from planner.ui.state import get_service, sidebar_controls
from planner.ui.theme import fictional_banner, inject

inject()
svc = get_service()
scenario_id = sidebar_controls(svc)
fictional_banner()

st.title("Decisions")
st.caption(
    "Approve, hold, or reject proposed rows with a reason. "
    "Holds and rejects stay out of the weekly batch. "
    "Use filters at company scale; do not render one card per account."
)

result = svc.assignment(scenario_id)
proposed = [r for r in result["rows"] if r["status"] == "PROPOSED"]
reviewer = st.text_input("Reviewer", value=st.session_state.get("reviewer", "Riley Chen"))
st.session_state.reviewer = reviewer

if not proposed:
    st.info("No proposed assignments in this scenario. Check Exceptions for blocked demand.")
    st.stop()

segments = sorted({r.get("derived_segment") or "" for r in proposed})
territories = sorted({r.get("territory") or "" for r in proposed})
c1, c2, c3 = st.columns(3)
with c1:
    seg_f = st.multiselect("Segment", segments, default=segments)
with c2:
    terr_f = st.multiselect("Territory", territories, default=territories)
with c3:
    only_pending = st.checkbox("Pending only", value=False)

filtered = [
    r
    for r in proposed
    if (r.get("derived_segment") or "") in seg_f
    and (r.get("territory") or "") in terr_f
    and (not only_pending or (r.get("review_decision") or "pending") == "pending")
]
st.metric("Proposed in view", len(filtered))

frame = pd.DataFrame(
    [
        {
            "account_id": r["account_id"],
            "display_name": r["display_name"],
            "segment": r.get("derived_segment"),
            "tier": r.get("tier"),
            "territory": r.get("territory"),
            "proposed_owner_id": r.get("proposed_owner_id"),
            "current_owner_id": r.get("owner_id"),
            "decision": r.get("review_decision") or "pending",
            "reason": r.get("review_reason") or "",
            "explanation": r.get("explanation") or "",
        }
        for r in filtered
    ]
)
edited = st.data_editor(
    frame,
    hide_index=True,
    use_container_width=True,
    disabled=[
        "account_id",
        "display_name",
        "segment",
        "tier",
        "territory",
        "proposed_owner_id",
        "current_owner_id",
        "explanation",
    ],
    column_config={
        "decision": st.column_config.SelectboxColumn(options=["pending", "approve", "hold", "reject"]),
        "reason": st.column_config.TextColumn(),
    },
)

b1, b2 = st.columns(2)
with b1:
    if st.button("Save visible decisions", type="primary"):
        for _, row in edited.iterrows():
            svc.upsert_review(
                str(row["account_id"]),
                str(row["decision"]),
                str(row.get("reason") or ""),
                reviewer,
                scenario_id,
            )
        st.success(f"Saved {len(edited)} reviews.")
        st.rerun()
with b2:
    if st.button("Approve all visible"):
        for _, row in edited.iterrows():
            svc.upsert_review(str(row["account_id"]), "approve", "bulk approve", reviewer, scenario_id)
        st.success(f"Approved {len(edited)} rows. Open Weekly Releases to commit a batch.")
        st.rerun()
