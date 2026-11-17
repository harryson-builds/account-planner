"""Turn a snapshot + scenario into KPIs, matrix, exceptions, and proposed books."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from planner.config.schema import SEGMENTS, TIERS, ScenarioConfig
from planner.domain.allocate import AccountDecision, allocate, books_as_dicts
from planner.domain.models import Snapshot

MATRIX_METRICS = ("raw", "gate_pass", "policy_eligible", "assignable")


def _empty_cell() -> dict[str, int]:
    return {m: 0 for m in MATRIX_METRICS}


def build_matrix(rows: list[AccountDecision]) -> dict[str, dict[str, dict[str, int]]]:
    matrix: dict[str, dict[str, dict[str, int]]] = {
        seg: {tier: _empty_cell() for tier in TIERS} for seg in SEGMENTS
    }
    for row in rows:
        seg = row.derived_segment if row.derived_segment in SEGMENTS else None
        tier = row.tier if row.tier in TIERS else None
        if not seg or not tier:
            continue
        cell = matrix[seg][tier]
        cell["raw"] += 1
        if row.gate_pass:
            cell["gate_pass"] += 1
        if row.policy_eligible:
            cell["policy_eligible"] += 1
        if row.currently_assignable or row.status in {"PROPOSED", "RETAINED"}:
            # retained named books are staffed; assignable cells stay the net-new pool
            pass
        if row.currently_assignable:
            cell["assignable"] += 1
    return matrix


def kpis(
    rows: list[AccountDecision],
    released_ids: set[str] | None = None,
) -> dict[str, Any]:
    released_ids = released_ids or set()
    raw = len(rows)
    gate = sum(1 for r in rows if r.gate_pass)
    eligible = sum(1 for r in rows if r.policy_eligible)
    assignable = sum(1 for r in rows if r.currently_assignable)
    proposed = sum(1 for r in rows if r.status == "PROPOSED")
    retained = sum(1 for r in rows if r.status == "RETAINED")
    blocked = sum(1 for r in rows if r.status == "BLOCKED")
    unallocated = sum(1 for r in rows if r.status == "UNALLOCATED")
    released = sum(1 for r in rows if r.account_id in released_ids)
    discrepancies = sum(1 for r in rows if r.discrepancy)
    mm_to_ent = sum(1 for r in rows if r.discrepancy == "Mid-Market → Enterprise")
    uncovered: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.policy_eligible and r.status in {"BLOCKED", "UNALLOCATED"}:
            key = f"{r.territory or 'UNKNOWN'} · {r.derived_segment}"
            uncovered[key] += 1
    return {
        "raw_inventory": raw,
        "gate_pass": gate,
        "policy_eligible": eligible,
        "currently_assignable": assignable,
        "proposed": proposed,
        "retained": retained,
        "blocked": blocked,
        "unallocated": unallocated,
        "released": released,
        "segment_discrepancies": discrepancies,
        "mm_to_ent": mm_to_ent,
        "uncovered_by_territory": dict(uncovered),
    }


def exceptions(rows: list[AccountDecision], books: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.status in {"BLOCKED", "UNALLOCATED"} or row.reason_code == "MISSING_HEADCOUNT":
            out.append(
                {
                    "account_id": row.account_id,
                    "display_name": row.display_name,
                    "derived_segment": row.derived_segment,
                    "tier": row.tier,
                    "territory": row.territory,
                    "status": row.status,
                    "reason_code": row.reason_code,
                    "explanation": row.explanation,
                }
            )
        elif row.discrepancy:
            out.append(
                {
                    "account_id": row.account_id,
                    "display_name": row.display_name,
                    "derived_segment": row.derived_segment,
                    "tier": row.tier,
                    "territory": row.territory,
                    "status": "DISCREPANCY",
                    "reason_code": "STALE_CRM_SEGMENT",
                    "explanation": f"CRM segment disagrees with employees: {row.discrepancy}.",
                }
            )
    for book in books:
        if book.get("over_cap"):
            out.append(
                {
                    "account_id": "",
                    "display_name": book["rep_id"],
                    "derived_segment": book["segment"],
                    "tier": "",
                    "territory": book["territory"],
                    "status": "OVER_CAP",
                    "reason_code": "OVER_CAP_BOOK",
                    "explanation": (
                        f"{book['rep_id']} holds {book['book_count']} against cap {book['cap']} "
                        f"(retained demand exceeds the scenario cap)."
                    ),
                }
            )
        if book.get("below_viable") and book.get("book_count", 0) > 0:
            out.append(
                {
                    "account_id": "",
                    "display_name": book["rep_id"],
                    "derived_segment": book["segment"],
                    "tier": "",
                    "territory": book["territory"],
                    "status": "BELOW_VIABLE",
                    "reason_code": "BELOW_VIABLE_BOOK",
                    "explanation": (
                        f"{book['rep_id']} book {book['book_count']} is below the viable minimum."
                    ),
                }
            )
    return out


def field_readiness(rows: list[AccountDecision]) -> list[dict[str, Any]]:
    """CRM-field checklist for policy-eligible rows that cannot yet be named."""
    checks = [
        ("country", "Country", lambda r: bool(r.country)),
        ("territory", "Territory", lambda r: bool(r.territory)),
        ("employee_count", "Employee count", lambda r: r.employee_count is not None),
        ("owner", "Named AE (current or proposed)", lambda r: bool(r.proposed_owner_id or r.owner_id)),
        ("sdr", "SDR overlay (MM)", lambda r: r.derived_segment != "Mid-Market" or bool(r.proposed_sdr_id or r.sdr_id)),
        ("industry", "Industry", lambda r: bool(r.industry)),
    ]
    eligible = [r for r in rows if r.policy_eligible or r.derived_segment == "Unknown"]
    n = max(len(eligible), 1)
    out = []
    for field, label, fn in checks:
        missing = [r for r in eligible if not fn(r)]
        out.append(
            {
                "field": field,
                "label": label,
                "present": len(eligible) - len(missing),
                "missing": len(missing),
                "coverage": round((len(eligible) - len(missing)) / n, 4),
                "sample_ids": [r.account_id for r in missing[:8]],
            }
        )
    return out


def run_assignment(
    snapshot: Snapshot,
    config: ScenarioConfig,
    as_of: date | None = None,
    ownership_overlay: dict[str, str | None] | None = None,
    released_ids: set[str] | None = None,
) -> dict[str, Any]:
    as_of = as_of or snapshot.snapshot_date
    rows, books, roster = allocate(snapshot, config, as_of, ownership_overlay=ownership_overlay)
    book_rows = books_as_dicts(books, config, as_of)
    result = {
        "as_of": as_of.isoformat(),
        "scenario_id": config.id,
        "scenario_version": config.version,
        "rows": [r.as_dict() for r in rows],
        "books": book_rows,
        "kpis": kpis(rows, released_ids=released_ids),
        "matrix": build_matrix(rows),
        "exceptions": exceptions(rows, book_rows),
        "field_readiness": field_readiness(rows),
        "roster_view": [
            {
                "seat_id": s.seat_id,
                "rep_id": s.rep_id,
                "role": s.role,
                "segment": s.segment,
                "territory": s.territory,
                "start_date": s.start_date.isoformat(),
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "eligibility_status": s.eligibility_status,
                "active_named": s.is_active_named(as_of),
                "future": s.is_future(as_of),
                "ramp_profile": s.ramp_profile,
            }
            for s in roster
        ],
    }
    return result
