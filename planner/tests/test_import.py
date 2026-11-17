from datetime import date
from io import StringIO

from planner.repo.db import Database
from planner.repo.validator import validate_csv_bundle
from planner.service import PlannerService
from planner.tests.conftest import account, seat, snapshot


ACCOUNTS_HEADER = (
    "account_id,display_name,employee_count,crm_segment,country,territory,industry,tier,"
    "qualification_gate,fit_score,intent_score,owner_id,sdr_id,parent_account_id,"
    "is_customer,has_open_opportunity,lock_end_date\n"
)
ROSTER_HEADER = (
    "seat_id,rep_id,role,segment,territory,start_date,end_date,ramp_profile,eligibility_status,cap_override\n"
)
ACT_HEADER = "activity_id,account_id,timestamp,activity_type,rep_id,outcome\n"


def test_duplicate_account_ids_rejected():
    accounts = ACCOUNTS_HEADER + (
        "ACC-1,One,1000,Enterprise,US,WEST,Software,A,PASS,80,,REP-1,,,false,false,\n"
        "ACC-1,Two,1000,Enterprise,US,WEST,Software,A,PASS,80,,REP-1,,,false,false,\n"
    )
    roster = ROSTER_HEADER + "SEAT-1,REP-1,AE,Enterprise,WEST,2025-01-01,,standard,active,\n"
    acts = ACT_HEADER
    result = validate_csv_bundle(StringIO(accounts), StringIO(roster), StringIO(acts), date(2026, 2, 1))
    assert not result.ok
    assert any("duplicate" in e.message for e in result.errors)


def test_unknown_parent_and_bad_date_rejected():
    accounts = ACCOUNTS_HEADER + (
        "ACC-1,One,1000,Enterprise,US,WEST,Software,A,PASS,80,,,,,false,false,not-a-date\n"
        "ACC-2,Two,1000,Enterprise,US,WEST,Software,A,PASS,80,,,,ACC-9,false,false,\n"
    )
    roster = ROSTER_HEADER + "SEAT-1,REP-1,AE,Enterprise,WEST,2025-01-01,,standard,active,\n"
    result = validate_csv_bundle(StringIO(accounts), StringIO(roster), StringIO(ACT_HEADER), date(2026, 2, 1))
    assert not result.ok
    fields = {e.field for e in result.errors}
    assert "lock_end_date" in fields
    assert "parent_account_id" in fields


def test_last_valid_snapshot_kept_and_ledger_untouched(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    sid, snap = svc.raw_snapshot()
    ledger_before = svc.db.ledger_count()
    n_accounts = len(snap.accounts)
    bad = validate_csv_bundle(
        StringIO(ACCOUNTS_HEADER + "ACC-1,One,x,Enterprise,US,WEST,Software,A,PASS,80,,,,,false,false,\n"),
        StringIO(ROSTER_HEADER + "SEAT-1,REP-1,AE,Enterprise,WEST,2025-01-01,,standard,active,\n"),
        StringIO(ACT_HEADER),
        date(2026, 2, 1),
    )
    assert not bad.ok
    imported = svc.import_csv(
        StringIO(ACCOUNTS_HEADER + "ACC-1,One,x,Enterprise,US,WEST,Software,A,PASS,80,,,,,false,false,\n"),
        StringIO(ROSTER_HEADER + "SEAT-1,REP-1,AE,Enterprise,WEST,2025-01-01,,standard,active,\n"),
        StringIO(ACT_HEADER),
        date(2026, 2, 1),
    )
    assert not imported.ok
    sid2, snap2 = svc.raw_snapshot()
    assert sid2 == sid
    assert len(snap2.accounts) == n_accounts
    assert svc.db.ledger_count() == ledger_before


def test_valid_import_does_not_write_ledger(tmp_path):
    svc = PlannerService(tmp_path / "p.sqlite")
    before = svc.db.ledger_count()
    accounts = ACCOUNTS_HEADER + "ACC-1,One,1500,Enterprise,US,WEST,Software,A,PASS,80,,,,,false,false,\n"
    roster = ROSTER_HEADER + "SEAT-1,REP-1,AE,Enterprise,WEST,2025-01-01,,standard,active,\n"
    result = svc.import_csv(StringIO(accounts), StringIO(roster), StringIO(ACT_HEADER), date(2026, 2, 1))
    assert result.ok
    _, snap = svc.raw_snapshot()
    assert [a.account_id for a in snap.accounts] == ["ACC-1"]
    assert svc.db.ledger_count() == before
