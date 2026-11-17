"""Qualification gate vs policy eligibility."""

from __future__ import annotations

from planner.config.schema import ScenarioConfig
from planner.domain.models import Account


def gate_pass(account: Account, config: ScenarioConfig) -> bool:
    return account.qualification_gate in config.eligibility.qualification_gates


def policy_eligible(account: Account, derived: str, config: ScenarioConfig) -> bool:
    if derived == "Unknown":
        return False
    if not gate_pass(account, config):
        return False
    if not account.tier or account.tier not in config.eligibility.tiers:
        return False
    return derived in config.policy_segments()
