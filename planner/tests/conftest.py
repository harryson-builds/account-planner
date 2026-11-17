from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from planner.config.schema import load_scenario, merge_overrides
from planner.domain.models import Account, Activity, Seat, Snapshot
from planner.repo.db import Database


AS_OF = date(2026, 2, 1)


@pytest.fixture
def config():
    return load_scenario("baseline")


@pytest.fixture
def tight():
    return load_scenario("tight_books")


def account(**kwargs) -> Account:
    data = {
        "account_id": "ACC-1000",
        "display_name": "Test Co",
        "employee_count": 1500,
        "crm_segment": "Enterprise",
        "country": "US",
        "territory": "WEST",
        "industry": "Software",
        "tier": "A",
        "qualification_gate": "PASS",
        "fit_score": 80,
        "owner_id": None,
        "sdr_id": None,
        "is_customer": False,
        "has_open_opportunity": False,
    }
    data.update(kwargs)
    return Account.model_validate(data)


def seat(**kwargs) -> Seat:
    data = {
        "seat_id": "SEAT-1",
        "rep_id": "REP-1",
        "role": "AE",
        "segment": "Enterprise",
        "territory": "WEST",
        "start_date": date(2025, 1, 1),
        "ramp_profile": "standard",
        "eligibility_status": "active",
    }
    data.update(kwargs)
    return Seat.model_validate(data)


def snapshot(accounts: list[Account], roster: list[Seat], activities: list[Activity] | None = None) -> Snapshot:
    return Snapshot(
        snapshot_date=AS_OF,
        source="test",
        accounts=accounts,
        roster=roster,
        activities=activities or [],
    )


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.sqlite")
