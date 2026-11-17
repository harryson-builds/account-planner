"""Derive planning segment from employee count."""

from __future__ import annotations

from planner.config.schema import ScenarioConfig
from planner.domain.models import Account

TIER_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}


def derived_segment(employee_count: int | None, config: ScenarioConfig) -> str:
    return config.band_for(employee_count)


def discrepancy(account: Account, derived: str) -> str | None:
    if not account.crm_segment:
        return None
    if derived == "Unknown":
        return f"{account.crm_segment} → Unknown"
    if account.crm_segment != derived:
        return f"{account.crm_segment} → {derived}"
    return None


def tier_rank(tier: str | None) -> int:
    if tier is None:
        return 99
    return TIER_RANK.get(tier, 99)
