"""Review decisions and transactional weekly release."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from planner.config.schema import ScenarioConfig
from planner.domain.allocate import allocate
from planner.domain.dates import shift_roster
from planner.domain.models import Snapshot


def apply_reviews(rows: list[dict[str, Any]], reviews: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        copy = dict(row)
        review = reviews.get(row["account_id"])
        if review:
            copy["review_decision"] = review["decision"]
            copy["review_reason"] = review.get("reason") or ""
            copy["reviewer"] = review.get("reviewer") or ""
        else:
            copy["review_decision"] = "pending"
            copy["review_reason"] = ""
            copy["reviewer"] = ""
        out.append(copy)
    return out


def approved_for_release(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if r.get("status") == "PROPOSED" and r.get("review_decision") == "approve"
    ]


def recheck_batch(
    snapshot: Snapshot,
    config: ScenarioConfig,
    approved: list[dict[str, Any]],
    as_of: date,
    active_locks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return conflict rows. Empty list means the batch may commit."""
    conflicts: list[dict[str, Any]] = []
    current = snapshot.account_map()
    roster = {s.rep_id: s for s in shift_roster(snapshot.roster, config) if s.rep_id}
    decisions, books, _ = allocate(snapshot, config, as_of)

    proposed_now = {d.account_id: d for d in decisions}

    # Running cap usage: start from books after retain, add this batch.
    usage = {rep: len(book.account_ids) for rep, book in books.items()}
    # Remove proposed accounts that are in this batch so we re-add them in order
    for row in approved:
        owner = row.get("proposed_owner_id")
        acc = row["account_id"]
        if owner in books and acc in books[owner].account_ids:
            usage[owner] = max(0, usage[owner] - 1)

    for row in approved:
        acc_id = row["account_id"]
        account = current.get(acc_id)
        if account is None:
            conflicts.append(
                {
                    "account_id": acc_id,
                    "code": "MISSING_ACCOUNT",
                    "detail": "Account is not in the current snapshot.",
                }
            )
            continue
        if (account.owner_id or None) != (row.get("owner_id") or None):
            conflicts.append(
                {
                    "account_id": acc_id,
                    "code": "OWNERSHIP_CHANGED",
                    "detail": (
                        f"Preview owner was {row.get('owner_id') or 'none'}; "
                        f"snapshot now has {account.owner_id or 'none'}."
                    ),
                }
            )
            continue
        lock = active_locks.get(acc_id)
        if lock and lock.get("new_owner_id"):
            conflicts.append(
                {
                    "account_id": acc_id,
                    "code": "DUPLICATE_ACTIVE_OWNERSHIP",
                    "detail": (
                        f"Already locked to {lock.get('new_owner_id')} "
                        f"through {lock.get('lock_end_date')} in batch {lock.get('batch_id')}. "
                        "Do not write a second active ledger row."
                    ),
                }
            )
            continue
        now = proposed_now.get(acc_id)
        if now is None or now.status != "PROPOSED" or now.proposed_owner_id != row.get("proposed_owner_id"):
            conflicts.append(
                {
                    "account_id": acc_id,
                    "code": "PREVIEW_STALE",
                    "detail": (
                        f"Current proposal is {None if now is None else now.status} "
                        f"to {None if now is None else now.proposed_owner_id}, "
                        f"not {row.get('proposed_owner_id')}."
                    ),
                }
            )
            continue
        owner = row.get("proposed_owner_id")
        seat = roster.get(owner or "")
        if seat is None or not seat.is_active_named(as_of):
            conflicts.append(
                {
                    "account_id": acc_id,
                    "code": "INVALID_STAFF",
                    "detail": f"Proposed owner {owner} is not an active named AE as of {as_of.isoformat()}.",
                }
            )
            continue
        cap = seat.cap_override if seat.cap_override is not None else config.cap_for(seat.segment)
        usage[owner] = usage.get(owner, 0) + 1
        if usage[owner] > cap:
            conflicts.append(
                {
                    "account_id": acc_id,
                    "code": "CAPACITY",
                    "detail": f"{owner} would exceed cap {cap} ({usage[owner]} assigned).",
                }
            )
            continue
    return conflicts


def build_ledger_rows(
    approved: list[dict[str, Any]],
    as_of: date,
    lock_days: int,
) -> list[dict[str, Any]]:
    lock_end = as_of + timedelta(days=lock_days)
    rows = []
    for row in approved:
        rows.append(
            {
                "account_id": row["account_id"],
                "prev_owner_id": row.get("owner_id"),
                "new_owner_id": row.get("proposed_owner_id"),
                "lock_end_date": lock_end.isoformat(),
            }
        )
    return rows
