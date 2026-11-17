from datetime import datetime

from planner.config.schema import load_scenario
from planner.domain.activity import calibrate
from planner.domain.models import Activity
from planner.tests.conftest import account, snapshot


def test_qualifying_touches_and_notes_ignored():
    cfg = load_scenario("baseline")
    accs = [
        account(account_id="ACC-W", owner_id="REP-1"),
        account(account_id="ACC-U", owner_id="REP-1", display_name="Untouched"),
    ]
    acts = [
        Activity(
            activity_id="ACT-1",
            account_id="ACC-W",
            timestamp=datetime(2026, 1, 20, 10, 0, 0),
            activity_type="call",
            rep_id="REP-1",
        ),
        Activity(
            activity_id="ACT-2",
            account_id="ACC-U",
            timestamp=datetime(2026, 1, 20, 10, 0, 0),
            activity_type="note",
            rep_id="REP-1",
        ),
    ]
    rows = [
        {
            "account_id": "ACC-W",
            "status": "RETAINED",
            "derived_segment": "Enterprise",
            "proposed_owner_id": "REP-1",
            "owner_id": "REP-1",
        },
        {
            "account_id": "ACC-U",
            "status": "RETAINED",
            "derived_segment": "Enterprise",
            "proposed_owner_id": "REP-1",
            "owner_id": "REP-1",
        },
    ]
    out = calibrate(snapshot(accs, [], acts), cfg, rows)
    assert out["method"] == "proxy_snapshot_ownership"
    assert out["worked_accounts"] == 1
    assert out["untouched_accounts"] == 1
    assert out["untouched_share"] == 0.5
