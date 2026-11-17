"""Overview — executive planning questions on the fictional snapshot."""

from __future__ import annotations

import streamlit as st

from planner.paths import REPO_ROOT  # noqa: F401  — sys.path bootstrap
from planner.ui.components import kpis, matrix_table
from planner.ui.state import get_service, sidebar_controls
from planner.ui.theme import fictional_banner, inject

inject()
svc = get_service()
scenario_id = sidebar_controls(svc)
fictional_banner()

st.title("Account Assignment & Capacity Planner")
st.caption(
    "Qualification protects book quality. Assignment rules enforce ownership and capacity. "
    "Scenario modeling shows where a hiring or allocation decision would change coverage and revenue potential."
)

assign = svc.assignment(scenario_id)
fy = svc.fy27(scenario_id)
compare = svc.compare_scenarios()
k = assign["kpis"]
base_arr = fy["arr"]["base"]
activity = fy["activity"]
m0 = fy["capacity"]["months"][0] if fy["capacity"]["months"] else {}

st.subheader("Planning questions")
kpis(
    [
        (
            "Policy-eligible",
            k["policy_eligible"],
            "PASS · Tier A/B · Enterprise or Mid-Market (unless Commercial is in policy).",
        ),
        (
            "Currently assignable",
            k["currently_assignable"],
            "Eligible and not blocked by geo, staff, SDR, parent routing, or a full book.",
        ),
        (
            "Proposed this cut",
            k["proposed"],
            "New named-owner proposals. Distinct from retained and released.",
        ),
        (
            "Released (local ledger)",
            k["released"],
            "Committed weekly releases with an active lock.",
        ),
    ]
)

uncovered = k.get("uncovered_by_territory") or {}
uncovered_txt = ", ".join(f"{name}: {n}" for name, n in sorted(uncovered.items())) or "none"
st.markdown(
    f"**Uncovered eligible demand:** {uncovered_txt}. "
    f"EAST Enterprise has no active named AE until the March hire. "
    f"EAST Mid-Market is blocked until SDR coverage starts in August."
)

st.subheader("Staffed seats vs FY27 hiring")
kpis(
    [
        (
            "Viable books (month 0)",
            m0.get("viable_seats", "—"),
            "Active AE books at or above the scenario viable minimum.",
        ),
        (
            "Staffed AE seats",
            m0.get("staffed_ae_seats", "—"),
            "Named AEs already started as of the snapshot month.",
        ),
        (
            "Ramp-adjusted seats",
            m0.get("ramp_adjusted_ae_seats", "—"),
            "Sum of ramp factors, not headcount.",
        ),
        (
            "Unallocated / blocked",
            m0.get("unallocated_accounts", "—"),
            "Eligible accounts still without a viable named owner this month.",
        ),
    ]
)
st.markdown(
    "Future seats are listed on Assignments and are **not** named owners until their start month. "
    "If a territory is short of eligible accounts, lowering the cap will not create coverage. "
    "If a territory is over-cap on retained customers, you need a higher cap, a split, or a later lock."
)

st.subheader("Worked vs assigned (activity calibration)")
untouched = activity.get("untouched_share")
untouched_pct = "—" if untouched is None else f"{untouched:.0%}"
st.markdown(
    f"Assigned accounts worked in the {activity['lookback_days']}-day lookback: "
    f"**{activity['worked_accounts']}** of **{activity['assigned_accounts']}** "
    f"(untouched share **{untouched_pct}**). "
    f"Method: `{activity['method']}` — {activity['method_note']}"
)
implied = activity.get("implied_monthly_worked_rate")
drift = activity.get("worked_rate_drift")
if implied is not None and drift is not None and abs(drift) >= 0.05:
    st.warning(
        f"Do not take a hiring decision on the ARR gap until you recalibrate. "
        f"Activity implies ~{implied:.0%} monthly first-worked accounts; the ARR model uses "
        f"{activity['worked_rate_used_in_arr']:.0%}. That drift is {drift:+.0%}."
    )
st.caption(
    "Tighter books are compared with the same default worked-account rate unless a scenario "
    "documents a historical calibration. Historical bookings are not used here."
)

st.subheader("Modeled new-logo ARR vs target")
kpis(
    [
        ("Base modeled ARR (USD)", f"{base_arr['modeled_arr_fy']:,.0f}", "Scenario estimate, FY27 closes only."),
        ("FY27 new-logo target", f"{base_arr['target_fy']:,.0f}", "Planning target, not quota attainment."),
        ("Gap to target", f"{base_arr['gap_to_target']:,.0f}", "Negative = short of target."),
        (
            "Outside FY closes",
            f"{base_arr['modeled_arr_outside_fy']:,.0f}",
            "Wins whose close lag lands after FY27.",
        ),
    ]
)
st.markdown(
    "Levers that move the gap: **book cap** (inventory that can be assigned), "
    "**hire month** (ramp and EAST coverage), **worked rate / win rate / lag**. "
    "Open Assumptions for the one-at-a-time sensitivity. "
    "Pipeline shown here is modeled opportunities, not CRM pipeline."
)

st.subheader("Segment × tier")
st.caption("Each cell: currently assignable · policy-eligible · gate pass · raw inventory.")
st.dataframe(matrix_table(assign["matrix"]), hide_index=True, use_container_width=True)

with st.expander("Scenario comparison (fictional)"):
    rows = []
    for sid, payload in compare.items():
        rows.append(
            {
                "scenario": payload["name"],
                "caps ENT/MM": f"{payload['caps']['Enterprise']}/{payload['caps']['Mid-Market']}",
                "hire shift (mo)": payload["hiring_shift_months"],
                "eligible": payload["kpis"]["policy_eligible"],
                "assignable": payload["kpis"]["currently_assignable"],
                "proposed": payload["kpis"]["proposed"],
                "modeled ARR (base)": payload["modeled_arr_base"],
                "gap": payload["gap_base"],
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)

st.page_link("pages/1_Assignments.py", label="Open assignment board")
st.page_link("pages/5_Assumptions.py", label="Edit scenario assumptions")
