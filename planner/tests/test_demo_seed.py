"""Seeded walkthrough: Helio Analytics from qualification to a proposed owner."""

from planner.service import PlannerService


def test_helio_analytics_qualifies_and_is_proposed(tmp_path):
    svc = PlannerService(tmp_path / "demo.sqlite")
    result = svc.assignment("baseline")
    row = next(r for r in result["rows"] if r["account_id"] == "ACC-0001")
    assert row["display_name"] == "Helio Analytics"
    assert row["derived_segment"] == "Enterprise"
    assert row["discrepancy"] == "Mid-Market → Enterprise"
    assert row["gate_pass"]
    assert row["policy_eligible"]
    assert row["status"] == "PROPOSED"
    assert row["proposed_owner_id"] == "REP-E02"  # E01 is over cap on retained
    svc.upsert_review("ACC-0001", "approve", "named ENT book", "walkthrough")
    outcome = svc.release("baseline", "WALK-1", "walkthrough")
    assert outcome["status"] == "released"
    assert "ACC-0001" in outcome["result"]["account_ids"]
    ledger = svc.ledger()
    assert any(r["account_id"] == "ACC-0001" and r["new_owner_id"] == "REP-E02" for r in ledger)


def test_kpi_reconcile_to_rows(tmp_path):
    svc = PlannerService(tmp_path / "demo.sqlite")
    result = svc.assignment("baseline")
    rows = result["rows"]
    k = result["kpis"]
    assert k["raw_inventory"] == len(rows)
    assert k["gate_pass"] == sum(1 for r in rows if r["gate_pass"])
    assert k["policy_eligible"] == sum(1 for r in rows if r["policy_eligible"])
    assert k["currently_assignable"] == sum(1 for r in rows if r["currently_assignable"])
    assert k["proposed"] == sum(1 for r in rows if r["status"] == "PROPOSED")
    matrix_raw = 0
    for seg in result["matrix"].values():
        for cell in seg.values():
            matrix_raw += cell["raw"]
    with_seg_tier = sum(1 for r in rows if r["derived_segment"] in result["matrix"] and r.get("tier") in {"A", "B", "C", "D"})
    assert matrix_raw == with_seg_tier


def test_fy27_retained_and_gap_labels(tmp_path):
    svc = PlannerService(tmp_path / "demo.sqlite")
    fy = svc.fy27("baseline")
    month0 = fy["capacity"]["months"][0]
    assert month0["retained_accounts"] == 25
    assert fy["arr"]["base"]["target_fy"] == 70000
    assert fy["arr"]["base"]["label"].startswith("modeled new-logo ARR")
    delayed = svc.fy27("delayed_hires")
    assert delayed["arr"]["base"]["modeled_arr_fy"] < fy["arr"]["base"]["modeled_arr_fy"]
