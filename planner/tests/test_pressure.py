"""Pressure tests: reproducibility, batch identity, locks, calibration, path safety."""

from __future__ import annotations

from datetime import date
from io import StringIO

import pytest

from planner.config.schema import load_scenario
from planner.domain.activity import calibrate
from planner.domain.release import recheck_batch
from planner.service import PlannerService
from planner.tests.conftest import AS_OF, account, seat, snapshot
from planner.tests.test_import import ACCOUNTS_HEADER, ACT_HEADER, ROSTER_HEADER


def test_same_snapshot_and_config_are_reproducible(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    a = svc.assignment("baseline")
    b = svc.assignment("baseline")
    assert [r["account_id"] + r["status"] + str(r.get("proposed_owner_id")) for r in a["rows"]] == [
        r["account_id"] + r["status"] + str(r.get("proposed_owner_id")) for r in b["rows"]
    ]
    assert a["kpis"] == b["kpis"]


def test_scenario_yaml_path_cannot_escape(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scenario("../baseline")
    with pytest.raises(FileNotFoundError):
        load_scenario("baseline/../../baseline")


def test_batch_id_reuse_across_snapshots_is_rejected(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    row = next(r for r in svc.assignment("baseline")["rows"] if r["status"] == "PROPOSED")
    svc.upsert_review(row["account_id"], "approve", "ok", "tester", "baseline")
    first = svc.release("baseline", "WEEK-1", "tester")
    assert first["status"] == "released"
    accounts = ACCOUNTS_HEADER + "ACC-9,Other,1500,Enterprise,US,WEST,Software,A,PASS,80,,,,,false,false,\n"
    roster = ROSTER_HEADER + "SEAT-1,REP-1,AE,Enterprise,WEST,2025-01-01,,standard,active,\n"
    imported = svc.import_csv(StringIO(accounts), StringIO(roster), StringIO(ACT_HEADER), date(2026, 2, 1))
    assert imported.ok
    again = svc.release("baseline", "WEEK-1", "tester")
    assert again["status"] == "batch_id_in_use"
    assert svc.db.ledger_count() == first["result"]["count"]


def test_released_account_is_not_written_twice(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    svc.upsert_review("ACC-0001", "approve", "ok", "tester", "baseline")
    first = svc.release("baseline", "LOCK-1", "tester")
    assert first["status"] == "released"
    other = next(
        r
        for r in svc.assignment("baseline")["rows"]
        if r["status"] == "PROPOSED" and r["account_id"] != "ACC-0001"
    )
    svc.upsert_review(other["account_id"], "approve", "ok", "tester", "baseline")
    second = svc.release("baseline", "LOCK-2", "tester")
    assert second["status"] == "released"
    ids = [row["account_id"] for row in svc.ledger()]
    assert ids.count("ACC-0001") == 1
    assert other["account_id"] in ids


def test_recheck_duplicate_lock_same_owner():
    cfg = load_scenario("baseline")
    acc = account(account_id="ACC-1")
    snap = snapshot([acc], [seat(cap_override=5)])
    approved = [
        {
            "account_id": "ACC-1",
            "owner_id": None,
            "proposed_owner_id": "REP-1",
            "status": "PROPOSED",
        }
    ]
    locks = {
        "ACC-1": {
            "new_owner_id": "REP-1",
            "lock_end_date": "2026-06-01",
            "batch_id": "OLD",
        }
    }
    conflicts = recheck_batch(snap, cfg, approved, AS_OF, locks)
    assert any(c["code"] == "DUPLICATE_ACTIVE_OWNERSHIP" for c in conflicts)


def test_activity_flags_arr_rate_drift(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    fy = svc.fy27("baseline")
    act = fy["activity"]
    assert act["implied_monthly_worked_rate"] is not None
    assert abs(act["worked_rate_drift"]) >= 0.05


def test_delayed_hires_moves_east_ae_later(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    base = svc.fy27("baseline")
    delayed = svc.fy27("delayed_hires")
    base_mar = next(a for a in base["capacity"]["assignment_by_month"] if a["month"] == "2026-03")
    delay_mar = next(a for a in delayed["capacity"]["assignment_by_month"] if a["month"] == "2026-03")
    base_row = next(r for r in base_mar["rows"] if r["account_id"] == "ACC-0003")
    delay_row = next(r for r in delay_mar["rows"] if r["account_id"] == "ACC-0003")
    assert base_row["proposed_owner_id"] == "REP-E05"
    assert delay_row["proposed_owner_id"] in {None, ""}
    assert delay_row["status"] in {"BLOCKED", "UNALLOCATED"}
