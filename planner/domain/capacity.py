"""Month-by-month FY27 capacity using the same allocator."""

from __future__ import annotations

from typing import Any

from planner.config.schema import ScenarioConfig
from planner.domain.dates import fiscal_months, month_end, ramp_factor, shift_roster
from planner.domain.models import Snapshot
from planner.domain.pipeline import run_assignment


def _territory_keys(roster_view: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[str]:
    keys = {s["territory"] for s in roster_view}
    keys |= {r.get("territory") or "UNKNOWN" for r in rows}
    return sorted(k for k in keys if k)


def simulate_year(
    snapshot: Snapshot,
    config: ScenarioConfig,
    released_ids: set[str] | None = None,
) -> dict[str, Any]:
    months = fiscal_months(config.fiscal)
    ownership: dict[str, str | None] = {a.account_id: a.owner_id for a in snapshot.accounts}
    ever_assigned: set[str] = set()
    monthly: list[dict[str, Any]] = []
    assignment_by_month: list[dict[str, Any]] = []

    for start in months:
        as_of = month_end(start)
        result = run_assignment(
            snapshot,
            config,
            as_of=as_of,
            ownership_overlay=ownership,
            released_ids=released_ids,
        )
        rows = result["rows"]
        books = result["books"]
        roster = shift_roster(snapshot.roster, config)

        previously = set(ever_assigned)
        retained_now = sum(1 for r in rows if r["status"] == "RETAINED")
        net_new = sum(
            1 for r in rows if r["status"] == "PROPOSED" and r["account_id"] not in previously
        )
        for row in rows:
            owner = row.get("proposed_owner_id")
            if not owner:
                continue
            ever_assigned.add(row["account_id"])
            ownership[row["account_id"]] = owner

        by_terr: dict[str, dict[str, Any]] = {}
        for terr in _territory_keys(result["roster_view"], rows):
            ae = [
                s
                for s in roster
                if s.role == "AE" and s.territory == terr and s.is_active_named(as_of)
            ]
            future_hires = [
                s
                for s in roster
                if s.role == "AE"
                and s.territory == terr
                and s.start_date.year == start.year
                and s.start_date.month == start.month
            ]
            sdr_active = [
                s
                for s in roster
                if s.role == "SDR" and s.territory == terr and s.is_active_named(as_of)
            ]
            terr_books = [b for b in books if b["territory"] == terr]
            terr_rows = [r for r in rows if (r.get("territory") or "UNKNOWN") == terr]
            gross = sum(b["cap"] for b in terr_books if b.get("rep_id"))
            retained_n = sum(1 for r in terr_rows if r["status"] == "RETAINED")
            open_slots = sum(b["open_slots"] for b in terr_books)
            unallocated = sum(1 for r in terr_rows if r["status"] in {"UNALLOCATED", "BLOCKED"} and r.get("policy_eligible"))
            fillable = sum(1 for b in terr_books if not b["below_viable"] and b["book_count"] > 0)
            viable_seats = sum(
                1
                for b in terr_books
                if b["book_count"] >= config.viable_min_for(b["segment"]) and b.get("rep_id")
            )
            ramp_adj = sum(
                ramp_factor(s.start_date, as_of, config.ramp_curve(s.ramp_profile))
                for s in ae
            )
            mm_assigned = any(
                r.get("derived_segment") == "Mid-Market" and r.get("proposed_owner_id")
                for r in terr_rows
            )
            sdr_required = 1 if mm_assigned and config.routing["Mid-Market"].requires_sdr else 0
            status = "balanced"
            if unallocated > 0:
                status = "shortage_eligible_accounts"
            elif open_slots > 0:
                status = "surplus_capacity"
            by_terr[terr] = {
                "staffed_ae_seats": len(ae),
                "ramp_adjusted_ae_seats": round(ramp_adj, 4),
                "planned_hires": len(future_hires),
                "sdr_required": sdr_required,
                "sdr_available": len(sdr_active),
                "gross_book_slots": gross,
                "retained_accounts": retained_n,
                "open_slots": open_slots,
                "net_new_eligible": sum(
                    1
                    for r in terr_rows
                    if r["status"] == "PROPOSED" and r["account_id"] in ever_assigned
                ),
                "fillable_seats": fillable,
                "viable_seats": viable_seats,
                "unallocated_accounts": unallocated,
                "supply_status": status,
            }

        # net_new at territory grain: proposed this month that just entered ever_assigned
        # The loop above already added them; recompute proposed counts that are new this month.
        monthly.append(
            {
                "month": start.isoformat()[:7],
                "as_of": as_of.isoformat(),
                "staffed_ae_seats": sum(v["staffed_ae_seats"] for v in by_terr.values()),
                "ramp_adjusted_ae_seats": round(sum(v["ramp_adjusted_ae_seats"] for v in by_terr.values()), 4),
                "planned_hires": sum(v["planned_hires"] for v in by_terr.values()),
                "sdr_required": sum(v["sdr_required"] for v in by_terr.values()),
                "sdr_available": sum(v["sdr_available"] for v in by_terr.values()),
                "gross_book_slots": sum(v["gross_book_slots"] for v in by_terr.values()),
                "retained_accounts": retained_now,
                "open_slots": sum(v["open_slots"] for v in by_terr.values()),
                "net_new_eligible": net_new,
                "fillable_seats": sum(v["fillable_seats"] for v in by_terr.values()),
                "viable_seats": sum(v["viable_seats"] for v in by_terr.values()),
                "unallocated_accounts": result["kpis"]["unallocated"] + result["kpis"]["blocked"],
                "by_territory": by_terr,
            }
        )
        assignment_by_month.append(
            {
                "month": start.isoformat()[:7],
                "as_of": as_of.isoformat(),
                "rows": [
                    {
                        "account_id": r["account_id"],
                        "derived_segment": r["derived_segment"],
                        "territory": r.get("territory"),
                        "status": r["status"],
                        "proposed_owner_id": r.get("proposed_owner_id"),
                        "is_customer": r.get("is_customer"),
                        "has_open_opportunity": r.get("has_open_opportunity"),
                        "policy_eligible": r.get("policy_eligible"),
                    }
                    for r in rows
                ],
                "books": books,
            }
        )

    shortage = [
        f"{m['month']} {terr}"
        for m in monthly
        for terr, v in m["by_territory"].items()
        if v["supply_status"] == "shortage_eligible_accounts"
    ]
    surplus = [
        f"{m['month']} {terr}"
        for m in monthly
        for terr, v in m["by_territory"].items()
        if v["supply_status"] == "surplus_capacity"
    ]
    return {
        "scenario_id": config.id,
        "scenario_version": config.version,
        "months": monthly,
        "assignment_by_month": assignment_by_month,
        "shortage_territory_months": shortage,
        "surplus_territory_months": surplus,
        "ever_assigned": sorted(ever_assigned),
    }
