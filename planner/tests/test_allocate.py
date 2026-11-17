from datetime import date

from planner.config.schema import load_scenario
from planner.domain.allocate import allocate, sort_accounts
from planner.tests.conftest import AS_OF, account, seat, snapshot


def test_protected_customer_and_open_opp_count_toward_cap():
    cfg = load_scenario("baseline")
    customer = account(account_id="ACC-1", owner_id="REP-1", is_customer=True, fit_score=10)
    opp = account(account_id="ACC-2", owner_id="REP-1", has_open_opportunity=True, employee_count=1600, fit_score=11)
    free = account(account_id="ACC-3", employee_count=1700, fit_score=99)
    snap = snapshot(
        [customer, opp, free],
        [seat(cap_override=2)],
    )
    rows, books, _ = allocate(snap, cfg, AS_OF)
    by_id = {r.account_id: r for r in rows}
    assert by_id["ACC-1"].status == "RETAINED"
    assert by_id["ACC-2"].status == "RETAINED"
    assert by_id["ACC-3"].status == "BLOCKED"
    assert by_id["ACC-3"].reason_code == "BOOK_FULL"
    assert not by_id["ACC-3"].currently_assignable
    assert books["REP-1"].open_slots == 0


def test_expired_lock_is_not_protected():
    cfg = load_scenario("baseline")
    expired = account(
        account_id="ACC-8",
        lock_end_date=date(2025, 12, 1),
        owner_id=None,
        fit_score=70,
    )
    snap = snapshot([expired], [seat()])
    rows, _, _ = allocate(snap, cfg, AS_OF)
    assert rows[0].status == "PROPOSED"
    assert not rows[0].protected


def test_unexpired_lock_is_retained():
    cfg = load_scenario("baseline")
    locked = account(
        account_id="ACC-7",
        lock_end_date=date(2026, 6, 1),
        owner_id="REP-1",
        fit_score=40,
    )
    snap = snapshot([locked], [seat()])
    rows, _, _ = allocate(snap, cfg, AS_OF)
    assert rows[0].status == "RETAINED"
    assert rows[0].protected


def test_future_seat_is_not_a_named_owner():
    cfg = load_scenario("baseline")
    acc = account(account_id="ACC-E", territory="EAST")
    future = seat(
        seat_id="SEAT-F",
        rep_id="REP-F",
        territory="EAST",
        start_date=date(2026, 3, 1),
        eligibility_status="future",
    )
    snap = snapshot([acc], [future])
    rows, _, _ = allocate(snap, cfg, AS_OF)
    assert rows[0].status == "BLOCKED"
    assert rows[0].reason_code == "FUTURE_SEAT_ONLY"
    assert not rows[0].currently_assignable


def test_mandatory_sdr_for_mid_market():
    cfg = load_scenario("baseline")
    acc = account(
        account_id="ACC-M",
        employee_count=400,
        crm_segment="Mid-Market",
        territory="EAST",
    )
    ae = seat(
        seat_id="SEAT-M",
        rep_id="REP-M",
        segment="Mid-Market",
        territory="EAST",
    )
    snap = snapshot([acc], [ae])
    rows, _, _ = allocate(snap, cfg, AS_OF)
    assert rows[0].reason_code == "REQUIRED_SDR_GAP"

    sdr = seat(
        seat_id="SEAT-S",
        rep_id="REP-S",
        role="SDR",
        segment="Mid-Market",
        territory="EAST",
    )
    rows2, _, _ = allocate(snapshot([acc], [ae, sdr]), cfg, AS_OF)
    assert rows2[0].status == "PROPOSED"
    assert rows2[0].proposed_sdr_id == "REP-S"


def test_stable_assignment_order_and_lowest_fill():
    cfg = load_scenario("baseline")
    a_high = account(account_id="ACC-A1", tier="A", fit_score=90)
    a_low = account(account_id="ACC-A0", tier="A", fit_score=90)
    b = account(account_id="ACC-B1", tier="B", fit_score=99, employee_count=1300)
    r1 = seat(seat_id="S1", rep_id="REP-Z", cap_override=10)
    r2 = seat(seat_id="S2", rep_id="REP-A", cap_override=10)
    snap = snapshot([b, a_high, a_low], [r1, r2])
    rows, books, _ = allocate(snap, cfg, AS_OF)
    proposed = [r for r in rows if r.status == "PROPOSED"]
    assert [r.account_id for r in sorted(proposed, key=lambda r: (0 if r.tier == "A" else 1, r.account_id))][:2] == [
        "ACC-A0",
        "ACC-A1",
    ]
    # Equal empty books: lowest fill (tie) then rep id REP-A before REP-Z
    first = next(r for r in rows if r.account_id == "ACC-A0")
    assert first.proposed_owner_id == "REP-A"


def test_cap_limit_stops_new_accounts():
    cfg = load_scenario("baseline")
    accs = [
        account(account_id=f"ACC-{i}", fit_score=100 - i, employee_count=1500 + i)
        for i in range(5)
    ]
    snap = snapshot(accs, [seat(cap_override=3)])
    rows, books, _ = allocate(snap, cfg, AS_OF)
    assert sum(1 for r in rows if r.status == "PROPOSED") == 3
    assert sum(1 for r in rows if r.status == "UNALLOCATED") == 2
    assert len(books["REP-1"].account_ids) == 3


def test_parent_child_ambiguity():
    cfg = load_scenario("baseline")
    parent = account(account_id="ACC-P", is_customer=True, owner_id="REP-1")
    child = account(account_id="ACC-C", parent_account_id="ACC-P", fit_score=99, employee_count=1800)
    snap = snapshot([parent, child], [seat(cap_override=14)])
    rows, _, _ = allocate(snap, cfg, AS_OF)
    by_id = {r.account_id: r for r in rows}
    assert by_id["ACC-P"].status == "RETAINED"
    assert by_id["ACC-C"].reason_code == "PARENT_CHILD_AMBIGUOUS"


def test_missing_geography_blocks_eligible():
    cfg = load_scenario("baseline")
    acc = account(account_id="ACC-G", country=None)
    snap = snapshot([acc], [seat()])
    rows, _, _ = allocate(snap, cfg, AS_OF)
    assert rows[0].reason_code == "MISSING_GEOGRAPHY"
    assert rows[0].policy_eligible
    assert not rows[0].currently_assignable
