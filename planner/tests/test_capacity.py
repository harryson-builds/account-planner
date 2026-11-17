from datetime import date

from planner.config.schema import load_scenario, merge_overrides
from planner.domain.capacity import simulate_year
from planner.domain.dates import ramp_factor
from planner.tests.conftest import account, seat, snapshot


def test_ramp_curve():
    curve = [0.25, 0.5, 0.75, 1.0]
    start = date(2026, 2, 1)
    assert ramp_factor(start, date(2026, 1, 31), curve) == 0
    assert ramp_factor(start, date(2026, 2, 28), curve) == 0.25
    assert ramp_factor(start, date(2026, 5, 31), curve) == 1.0
    assert ramp_factor(start, date(2027, 2, 1), curve) == 1.0


def test_departure_frees_the_seat():
    cfg = merge_overrides(
        load_scenario("baseline"),
        {"fiscal": {"start": date(2026, 2, 1), "end": date(2026, 5, 31)}},
    )
    accs = [account(account_id=f"ACC-{i}", fit_score=90 - i) for i in range(3)]
    departing = seat(
        seat_id="S-D",
        rep_id="REP-D",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 3, 31),
        cap_override=10,
    )
    remaining = seat(seat_id="S-R", rep_id="REP-R", cap_override=10)
    snap = snapshot(accs, [departing, remaining])
    year = simulate_year(snap, cfg)
    feb = next(m for m in year["months"] if m["month"] == "2026-02")
    apr = next(m for m in year["months"] if m["month"] == "2026-04")
    assert feb["staffed_ae_seats"] == 2
    assert apr["staffed_ae_seats"] == 1


def test_future_hire_becomes_named_in_start_month():
    cfg = merge_overrides(
        load_scenario("baseline"),
        {"fiscal": {"start": date(2026, 2, 1), "end": date(2026, 4, 30)}},
    )
    acc = account(account_id="ACC-E", territory="EAST")
    future = seat(
        seat_id="SEAT-E",
        rep_id="REP-E",
        territory="EAST",
        start_date=date(2026, 3, 1),
        eligibility_status="future",
        cap_override=10,
    )
    snap = snapshot([acc], [future])
    year = simulate_year(snap, cfg)
    feb = next(m for m in year["months"] if m["month"] == "2026-02")
    mar = next(m for m in year["months"] if m["month"] == "2026-03")
    assert feb["staffed_ae_seats"] == 0
    assert mar["staffed_ae_seats"] == 1
    mar_rows = next(a for a in year["assignment_by_month"] if a["month"] == "2026-03")["rows"]
    assert mar_rows[0]["proposed_owner_id"] == "REP-E"
