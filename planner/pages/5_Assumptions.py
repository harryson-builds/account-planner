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

st.title("Assumptions")
st.caption(
    "Vary caps, hiring timing, qualification policy, and ARR inputs without changing source CSVs. "
    "Overrides live in local SQLite. Scenario runs never write the release ledger."
)

cfg = svc.scenario(scenario_id)
st.markdown(f"**{cfg.name}** · `{cfg.id}` · version `{cfg.version}` — {cfg.description}")

with st.form("overrides"):
    c1, c2, c3 = st.columns(3)
    with c1:
        ent_cap = st.number_input("Enterprise cap", min_value=1, value=int(cfg.caps["Enterprise"]))
        mm_cap = st.number_input("Mid-Market cap", min_value=1, value=int(cfg.caps["Mid-Market"]))
        com_cap = st.number_input("Commercial cap", min_value=1, value=int(cfg.caps["Commercial"]))
    with c2:
        include_com = st.checkbox("Include Commercial in named-account policy", value=cfg.eligibility.include_commercial)
        shift = st.number_input("FY27 hire shift (months)", min_value=0, max_value=6, value=int(cfg.hiring_shift_months))
        lock_days = st.number_input("Lock days", min_value=0, max_value=365, value=int(cfg.lock_days))
    with c3:
        worked = st.number_input("Base worked rate", min_value=0.0, max_value=1.0, value=float(cfg.arr.worked_rate.base), step=0.01)
        opp = st.number_input("Base opportunity rate", min_value=0.0, max_value=1.0, value=float(cfg.arr.opportunity_rate.base), step=0.01)
        win = st.number_input("Base win rate", min_value=0.0, max_value=1.0, value=float(cfg.arr.win_rate.base), step=0.01)
        arr_win = st.number_input("Base ARR / win (USD)", min_value=0.0, value=float(cfg.arr.avg_arr_per_win.base), step=1000.0)
        lag = st.number_input("Base close lag (months)", min_value=0, max_value=12, value=int(cfg.arr.close_lag_months.base))
    saved = st.form_submit_button("Apply overrides")
    reset = st.form_submit_button("Reset to YAML")

if saved:
    svc.save_overrides(
        scenario_id,
        {
            "caps": {"Enterprise": int(ent_cap), "Mid-Market": int(mm_cap), "Commercial": int(com_cap)},
            "eligibility": {"include_commercial": bool(include_com)},
            "hiring_shift_months": int(shift),
            "lock_days": int(lock_days),
            "arr": {
                "worked_rate": {"base": float(worked)},
                "opportunity_rate": {"base": float(opp)},
                "win_rate": {"base": float(win)},
                "avg_arr_per_win": {"base": float(arr_win)},
                "close_lag_months": {"base": int(lag)},
            },
        },
    )
    st.success("Overrides saved. Source YAML is unchanged.")
    st.rerun()
if reset:
    svc.clear_overrides(scenario_id)
    st.success("Overrides cleared.")
    st.rerun()

fy = svc.fy27(scenario_id)
st.subheader("FY27 capacity by month")
cap_rows = []
for m in fy["capacity"]["months"]:
    cap_rows.append(
        {
            "month": m["month"],
            "staffed AE": m["staffed_ae_seats"],
            "ramp-adj": m["ramp_adjusted_ae_seats"],
            "hires": m["planned_hires"],
            "SDR avail": m["sdr_available"],
            "gross slots": m["gross_book_slots"],
            "retained": m["retained_accounts"],
            "open slots": m["open_slots"],
            "net new": m["net_new_eligible"],
            "viable seats": m["viable_seats"],
            "unallocated+blocked": m["unallocated_accounts"],
        }
    )
st.dataframe(cap_rows, hide_index=True, use_container_width=True)

st.subheader("ARR variants (USD, modeled new-logo)")
st.dataframe(
    [
        {
            "variant": name,
            "modeled ARR": payload["modeled_arr_fy"],
            "outside FY": payload["modeled_arr_outside_fy"],
            "target": payload["target_fy"],
            "gap": payload["gap_to_target"],
            "worked_rate": payload["inputs"]["worked_rate"],
            "opp_rate": payload["inputs"]["opportunity_rate"],
            "win_rate": payload["inputs"]["win_rate"],
            "ARR/win": payload["inputs"]["avg_arr_per_win"],
            "lag": payload["inputs"]["close_lag_months"],
        }
        for name, payload in fy["arr"].items()
    ],
    hide_index=True,
    use_container_width=True,
)

st.subheader("Sensitivity (one lever at a time vs base)")
st.dataframe(pd.DataFrame(fy["sensitivity"]), hide_index=True, use_container_width=True)

st.subheader("Activity calibration")
st.json(
    {
        "method": fy["activity"]["method"],
        "assigned": fy["activity"]["assigned_accounts"],
        "worked": fy["activity"]["worked_accounts"],
        "untouched_share": fy["activity"]["untouched_share"],
        "by_segment": fy["activity"]["by_segment"],
    }
)
