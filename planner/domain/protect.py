"""Protected ownership: customers, open opportunities, unexpired locks."""

from __future__ import annotations

from datetime import date

from planner.domain.models import Account


def is_protected(account: Account, as_of: date) -> bool:
    if account.is_customer or account.has_open_opportunity:
        return True
    if account.lock_end_date is not None and account.lock_end_date >= as_of:
        return True
    return False


def protection_reason(account: Account, as_of: date) -> str:
    reasons = []
    if account.is_customer:
        reasons.append("customer")
    if account.has_open_opportunity:
        reasons.append("open opportunity")
    if account.lock_end_date is not None and account.lock_end_date >= as_of:
        reasons.append(f"lock through {account.lock_end_date.isoformat()}")
    return ", ".join(reasons) if reasons else "not protected"
