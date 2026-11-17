from datetime import date

from planner.config.schema import load_scenario
from planner.domain.allocate import allocate
from planner.domain.pipeline import run_assignment
from planner.domain.release import recheck_batch
from planner.service import PlannerService
from planner.tests.conftest import AS_OF, account, seat, snapshot


def test_duplicate_release_is_idempotent(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    result = svc.assignment("baseline")
    proposed = [r for r in result["rows"] if r["status"] == "PROPOSED"]
    assert proposed
    sid, _ = svc.snapshot_record()
    for row in proposed[:3]:
        svc.upsert_review(row["account_id"], "approve", "ok", "tester")
    first = svc.release("baseline", "BATCH-1", "tester")
    assert first["status"] == "released"
    count = svc.db.ledger_count()
    second = svc.release("baseline", "BATCH-1", "tester")
    assert second["status"] == "idempotent"
    assert svc.db.ledger_count() == count
    assert second["result"]["account_ids"] == first["result"]["account_ids"]


def test_stale_ownership_leaves_batch_pending(tmp_path):
    cfg = load_scenario("baseline")
    acc = account(account_id="ACC-1")
    snap = snapshot([acc], [seat(cap_override=5)])
    rows, _, _ = allocate(snap, cfg, AS_OF)
    approved = [rows[0].as_dict()]
    approved[0]["status"] = "PROPOSED"
    mutated = acc.model_copy(update={"owner_id": "REP-OTHER"})
    snap2 = snapshot([mutated], [seat(cap_override=5)])
    conflicts = recheck_batch(snap2, cfg, approved, AS_OF, active_locks={})
    assert any(c["code"] == "OWNERSHIP_CHANGED" for c in conflicts)


def test_conflict_does_not_write_ledger(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    result = svc.assignment("baseline")
    proposed = [r for r in result["rows"] if r["status"] == "PROPOSED"]
    svc.upsert_review(proposed[0]["account_id"], "approve", "ok", "tester", "baseline")
    # Force a stale preview by changing the stored snapshot owner after reviews.
    sid, snap = svc.raw_snapshot()
    accounts = []
    for a in snap.accounts:
        if a.account_id == proposed[0]["account_id"]:
            accounts.append(a.model_copy(update={"owner_id": "REP-SPOIL"}))
        else:
            accounts.append(a)
    svc.db.overwrite_snapshot(sid, snap.model_copy(update={"accounts": accounts}))
    before = svc.db.ledger_count()
    outcome = svc.release("baseline", "BATCH-STALE", "tester")
    assert outcome["status"] == "pending_conflict"
    assert svc.db.ledger_count() == before


def test_scenario_run_does_not_touch_ledger(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    before = svc.db.ledger_count()
    svc.fy27("tight_books")
    svc.assignment("delayed_hires")
    assert svc.db.ledger_count() == before
