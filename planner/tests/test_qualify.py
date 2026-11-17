from planner.config.schema import load_scenario, merge_overrides
from planner.domain.allocate import allocate
from planner.domain.qualify import gate_pass, policy_eligible
from planner.tests.conftest import AS_OF, account, seat, snapshot


def test_qualifying_vs_assignable():
    cfg = load_scenario("baseline")
    pass_ab = account(account_id="ACC-1", employee_count=1500, tier="A", qualification_gate="PASS")
    commercial = account(account_id="ACC-2", employee_count=50, crm_segment="Commercial", tier="A")
    tier_c = account(account_id="ACC-3", employee_count=1500, tier="C")
    fail = account(account_id="ACC-4", employee_count=1500, qualification_gate="FAIL")
    assert policy_eligible(pass_ab, "Enterprise", cfg)
    assert not policy_eligible(commercial, "Commercial", cfg)
    assert not policy_eligible(tier_c, "Enterprise", cfg)
    assert not policy_eligible(fail, "Enterprise", cfg)
    assert gate_pass(pass_ab, cfg)
    assert not gate_pass(fail, cfg)

    snap = snapshot(
        [pass_ab, commercial, tier_c, fail],
        [seat()],
    )
    rows, _, _ = allocate(snap, cfg, AS_OF)
    by_id = {r.account_id: r for r in rows}
    assert by_id["ACC-1"].policy_eligible
    assert by_id["ACC-1"].currently_assignable
    assert by_id["ACC-1"].status == "PROPOSED"
    assert not by_id["ACC-2"].policy_eligible
    assert by_id["ACC-2"].status == "INVENTORY"
    assert not by_id["ACC-3"].currently_assignable
    assert not by_id["ACC-4"].policy_eligible


def test_include_commercial_policy():
    cfg = merge_overrides(load_scenario("baseline"), {"eligibility": {"include_commercial": True}})
    acc = account(account_id="ACC-2", employee_count=50, crm_segment="Commercial", tier="A")
    assert policy_eligible(acc, "Commercial", cfg)
    snap = snapshot(
        [acc],
        [
            seat(seat_id="C1", rep_id="REP-C", segment="Commercial"),
            seat(seat_id="S1", rep_id="REP-S", role="SDR", segment="Commercial"),
        ],
    )
    rows, _, _ = allocate(snap, cfg, AS_OF)
    assert rows[0].status == "PROPOSED"
