"""Hand-calculated ARR goldens."""

from datetime import date

from planner.config.schema import load_scenario, merge_overrides
from planner.domain.arr import model_arr
from planner.domain.dates import shift_roster
from planner.domain.models import Seat
from planner.tests.conftest import seat as make_seat


def _capacity_stub(months: list[dict], rows_by_month: list[list[dict]]) -> dict:
    assignment = []
    for month, rows in zip(months, rows_by_month):
        assignment.append({"month": month, "as_of": month + "-28", "rows": rows, "books": []})
    return {"assignment_by_month": assignment, "months": [], "scenario_id": "t", "scenario_version": "1"}


def test_two_month_funnel_with_lag():
    """10 new-logo assigned accounts, worked 0.5, ramp 1.0, opp 0.4, win 0.5, ARR 24000, lag 1.

    Month 1 first-worked = 10 * 0.5 * 1 = 5, remaining 5.
    Month 2 first-worked = 5 * 0.5 * 1 = 2.5.
    Wins m1 = 5 * 0.4 * 0.5 = 1.0 close in month 2 (in FY).
    Wins m2 = 2.5 * 0.4 * 0.5 = 0.5 close in month 3 (outside FY).
    FY ARR = 1.0 * 24000 = 24000. Outside = 12000.
    """
    cfg = merge_overrides(
        load_scenario("baseline"),
        {
            "fiscal": {"label": "FY-short", "start": date(2026, 2, 1), "end": date(2026, 3, 31)},
            "arr": {
                "worked_rate": {"conservative": 0.5, "base": 0.5, "upside": 0.5},
                "opportunity_rate": {"conservative": 0.4, "base": 0.4, "upside": 0.4},
                "win_rate": {"conservative": 0.5, "base": 0.5, "upside": 0.5},
                "avg_arr_per_win": {"conservative": 24000, "base": 24000, "upside": 24000},
                "close_lag_months": {"conservative": 1, "base": 1, "upside": 1},
                "new_logo_arr_target": {"WEST": 24000, "total": 24000},
            },
            "ramp": {"standard": [1.0]},
        },
    )
    rows = [
        {
            "account_id": f"ACC-{i:02d}",
            "derived_segment": "Enterprise",
            "territory": "WEST",
            "status": "PROPOSED",
            "proposed_owner_id": "REP-1",
            "is_customer": False,
            "has_open_opportunity": False,
            "policy_eligible": True,
        }
        for i in range(10)
    ]
    cap = _capacity_stub(["2026-02", "2026-03"], [rows, rows])
    roster = [make_seat(start_date=date(2025, 1, 1), ramp_profile="standard")]
    modeled = model_arr(cap, cfg, roster, variant="base")
    assert modeled["monthly"][0]["expected_first_worked"] == 5
    assert modeled["monthly"][1]["expected_first_worked"] == 2.5
    assert modeled["modeled_arr_fy"] == 24000
    assert modeled["modeled_arr_outside_fy"] == 12000
    assert modeled["gap_to_target"] == 0


def test_zero_rate_is_zero_arr():
    cfg = merge_overrides(
        load_scenario("baseline"),
        {
            "fiscal": {"start": date(2026, 2, 1), "end": date(2026, 2, 28)},
            "arr": {"worked_rate": {"conservative": 0, "base": 0, "upside": 0}},
        },
    )
    rows = [
        {
            "account_id": "ACC-1",
            "derived_segment": "Enterprise",
            "territory": "WEST",
            "status": "PROPOSED",
            "proposed_owner_id": "REP-1",
            "is_customer": False,
            "has_open_opportunity": False,
            "policy_eligible": True,
        }
    ]
    cap = _capacity_stub(["2026-02"], [rows])
    modeled = model_arr(cap, cfg, [make_seat()], variant="base")
    assert modeled["modeled_arr_fy"] == 0
    assert modeled["monthly"][0]["expected_first_worked"] == 0


def test_customers_and_open_opps_excluded():
    cfg = merge_overrides(
        load_scenario("baseline"),
        {"fiscal": {"start": date(2026, 2, 1), "end": date(2026, 2, 28)}},
    )
    rows = [
        {
            "account_id": "ACC-C",
            "derived_segment": "Enterprise",
            "territory": "WEST",
            "status": "RETAINED",
            "proposed_owner_id": "REP-1",
            "is_customer": True,
            "has_open_opportunity": False,
            "policy_eligible": True,
        },
        {
            "account_id": "ACC-O",
            "derived_segment": "Enterprise",
            "territory": "WEST",
            "status": "RETAINED",
            "proposed_owner_id": "REP-1",
            "is_customer": False,
            "has_open_opportunity": True,
            "policy_eligible": True,
        },
    ]
    modeled = model_arr(_capacity_stub(["2026-02"], [rows]), cfg, [make_seat()], variant="base")
    assert modeled["monthly"][0]["expected_first_worked"] == 0


def test_cohort_dedupes_across_owner_change():
    """Remaining mass is per account, not per owner. Switching REP-1 → REP-2 does not reset the pool."""
    cfg = merge_overrides(
        load_scenario("baseline"),
        {
            "fiscal": {"start": date(2026, 2, 1), "end": date(2026, 3, 31)},
            "arr": {
                "worked_rate": {"conservative": 0.5, "base": 0.5, "upside": 0.5},
                "opportunity_rate": {"conservative": 0, "base": 0, "upside": 0},
                "win_rate": {"conservative": 0, "base": 0, "upside": 0},
                "avg_arr_per_win": {"conservative": 0, "base": 0, "upside": 0},
                "close_lag_months": {"conservative": 0, "base": 0, "upside": 0},
            },
            "ramp": {"standard": [1.0]},
        },
    )
    row = {
        "account_id": "ACC-X",
        "derived_segment": "Enterprise",
        "territory": "WEST",
        "status": "PROPOSED",
        "proposed_owner_id": "REP-1",
        "is_customer": False,
        "has_open_opportunity": False,
        "policy_eligible": True,
    }
    row2 = dict(row)
    row2["proposed_owner_id"] = "REP-2"
    cap = _capacity_stub(["2026-02", "2026-03"], [[row], [row2]])
    roster = [
        make_seat(seat_id="S1", rep_id="REP-1"),
        make_seat(seat_id="S2", rep_id="REP-2"),
    ]
    modeled = model_arr(cap, cfg, roster, variant="base")
    assert modeled["monthly"][0]["expected_first_worked"] == 0.5
    assert modeled["monthly"][1]["expected_first_worked"] == 0.25
    assert modeled["monthly"][1]["remaining_pool"] == 0.25
