"""Monthly first-worked cohort ARR bridge. Modeled new-logo ARR only."""

from __future__ import annotations

from typing import Any, Literal

from planner.config.schema import ScenarioConfig
from planner.domain.dates import add_months, fiscal_months, month_start
from planner.domain.models import Seat

Variant = Literal["conservative", "base", "upside"]


def _rate(triple, variant: Variant) -> float:
    return float(getattr(triple, variant))


def _ramp_for(rep_id: str | None, as_of_month: str, roster: list[Seat], config: ScenarioConfig) -> float:
    if not rep_id:
        return 0.0
    seat = next((s for s in roster if s.rep_id == rep_id), None)
    if seat is None:
        return 0.0
    as_of = month_start(date_from_month(as_of_month))
    # use month end-ish: first of month is enough for months_between
    from planner.domain.dates import month_end, ramp_factor

    return ramp_factor(seat.start_date, month_end(as_of), config.ramp_curve(seat.ramp_profile))


def date_from_month(yyyy_mm: str):
    from datetime import date

    y, m = yyyy_mm.split("-")
    return date(int(y), int(m), 1)


def new_logo_pool(month_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in month_rows
        if r.get("proposed_owner_id")
        and r.get("policy_eligible")
        and not r.get("is_customer")
        and not r.get("has_open_opportunity")
    ]


def model_arr(
    capacity_result: dict[str, Any],
    config: ScenarioConfig,
    roster: list[Seat],
    variant: Variant = "base",
    overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Cohort remaining mass starts at 1.0 per unique assigned new-logo account.

    remaining × monthly worked rate × owner ramp = expected first-worked.
    Deduct from remaining. Owner changes do not reset remaining (unique accounts).
    """
    overrides = overrides or {}
    worked_rate = float(overrides.get("worked_rate", _rate(config.arr.worked_rate, variant)))
    opp_rate = float(overrides.get("opportunity_rate", _rate(config.arr.opportunity_rate, variant)))
    win_rate = float(overrides.get("win_rate", _rate(config.arr.win_rate, variant)))
    avg_arr = float(overrides.get("avg_arr_per_win", _rate(config.arr.avg_arr_per_win, variant)))
    lag = int(overrides.get("close_lag_months", _rate(config.arr.close_lag_months, variant)))

    fy_months = [d.isoformat()[:7] for d in fiscal_months(config.fiscal)]
    fy_set = set(fy_months)
    remaining: dict[str, float] = {}
    owner_of: dict[str, str | None] = {}
    meta: dict[str, dict[str, Any]] = {}

    monthly_out: list[dict[str, Any]] = []
    closes: dict[str, float] = {m: 0.0 for m in fy_months}
    closes_outside = 0.0
    pipeline_opps = 0.0

    by_month = {item["month"]: item for item in capacity_result["assignment_by_month"]}

    for month in fy_months:
        payload = by_month[month]
        pool_rows = new_logo_pool(payload["rows"])
        for row in pool_rows:
            acc = row["account_id"]
            if acc not in remaining:
                remaining[acc] = 1.0
                meta[acc] = {
                    "segment": row.get("derived_segment"),
                    "territory": row.get("territory"),
                }
            owner_of[acc] = row.get("proposed_owner_id")

        first_worked = 0.0
        first_worked_by_terr: dict[str, float] = {}
        first_worked_by_seg: dict[str, float] = {}
        for acc, mass in list(remaining.items()):
            if mass <= 0:
                continue
            owner = owner_of.get(acc)
            if not owner:
                continue
            ramp = _ramp_for(owner, month, roster, config)
            expected = mass * worked_rate * ramp
            if expected <= 0:
                continue
            expected = min(expected, mass)
            remaining[acc] = mass - expected
            first_worked += expected
            terr = meta[acc].get("territory") or "UNKNOWN"
            seg = meta[acc].get("segment") or "Unknown"
            first_worked_by_terr[terr] = first_worked_by_terr.get(terr, 0.0) + expected
            first_worked_by_seg[seg] = first_worked_by_seg.get(seg, 0.0) + expected

        opps = first_worked * opp_rate
        wins = opps * win_rate
        pipeline_opps += opps
        close_month_date = add_months(date_from_month(month), lag)
        close_key = close_month_date.isoformat()[:7]
        arr_value = wins * avg_arr
        in_fy = close_key in fy_set
        if in_fy:
            closes[close_key] = closes.get(close_key, 0.0) + arr_value
        else:
            closes_outside += arr_value

        monthly_out.append(
            {
                "month": month,
                "remaining_pool": round(sum(max(0.0, v) for v in remaining.values()), 6),
                "unique_assigned_new_logo": sum(1 for v in remaining.values() if v > 0),
                "expected_first_worked": round(first_worked, 6),
                "expected_opportunities": round(opps, 6),
                "expected_wins": round(wins, 6),
                "close_month": close_key,
                "close_in_fy": in_fy,
                "expected_arr": round(arr_value if in_fy else 0.0, 2),
                "expected_arr_outside_fy": round(0.0 if in_fy else arr_value, 2),
                "by_territory": {k: round(v, 6) for k, v in first_worked_by_terr.items()},
                "by_segment": {k: round(v, 6) for k, v in first_worked_by_seg.items()},
            }
        )

    arr_by_month = {m: round(closes.get(m, 0.0), 2) for m in fy_months}
    total_arr = round(sum(arr_by_month.values()), 2)
    target = float(config.arr.new_logo_arr_target.get("total", 0))
    arr_by_terr = {k: 0.0 for k in config.arr.new_logo_arr_target if k != "total"}
    # Approximate territory ARR by sharing each month's first-worked mix onto that month's ARR that closes in FY
    # Simpler: allocate FY ARR in proportion to first-worked by territory across the year.
    terr_worked: dict[str, float] = {}
    for row in monthly_out:
        for terr, val in row["by_territory"].items():
            terr_worked[terr] = terr_worked.get(terr, 0.0) + val
    worked_total = sum(terr_worked.values()) or 1.0
    for terr, val in terr_worked.items():
        arr_by_terr[terr] = round(total_arr * (val / worked_total), 2)

    target_by_terr = {k: float(v) for k, v in config.arr.new_logo_arr_target.items() if k != "total"}
    gap_by_terr = {k: round(arr_by_terr.get(k, 0.0) - target_by_terr.get(k, 0.0), 2) for k in target_by_terr}

    return {
        "label": "modeled new-logo ARR (scenario estimate)",
        "currency": config.arr.currency,
        "unit": config.arr.unit,
        "variant": variant,
        "inputs": {
            "worked_rate": worked_rate,
            "opportunity_rate": opp_rate,
            "win_rate": win_rate,
            "avg_arr_per_win": avg_arr,
            "close_lag_months": lag,
            "source": "scenario YAML" if not overrides else "override",
        },
        "monthly": monthly_out,
        "arr_by_close_month": arr_by_month,
        "modeled_arr_fy": total_arr,
        "modeled_arr_outside_fy": round(closes_outside, 2),
        "pipeline_opportunities": round(pipeline_opps, 4),
        "target_fy": target,
        "gap_to_target": round(total_arr - target, 2),
        "arr_by_territory": arr_by_terr,
        "target_by_territory": target_by_terr,
        "gap_by_territory": gap_by_terr,
        "notes": [
            "Excludes preexisting customers and open-opportunity accounts.",
            "Opportunity and win rates are cohort conversion assumptions, not historical bookings.",
            "Does not multiply by quota attainment.",
            "Fractional expected counts are intentional.",
        ],
    }


def three_variants(
    capacity_result: dict[str, Any],
    config: ScenarioConfig,
    roster: list[Seat],
) -> dict[str, Any]:
    return {
        variant: model_arr(capacity_result, config, roster, variant=variant)  # type: ignore[arg-type]
        for variant in ("conservative", "base", "upside")
    }


def sensitivity(
    capacity_result: dict[str, Any],
    config: ScenarioConfig,
    roster: list[Seat],
) -> list[dict[str, Any]]:
    """One-at-a-time vs base: conservative and upside on each lever."""
    base = model_arr(capacity_result, config, roster, variant="base")
    levers = [
        ("worked_rate", config.arr.worked_rate),
        ("opportunity_rate", config.arr.opportunity_rate),
        ("win_rate", config.arr.win_rate),
        ("avg_arr_per_win", config.arr.avg_arr_per_win),
        ("close_lag_months", config.arr.close_lag_months),
    ]
    rows = []
    for name, triple in levers:
        for direction, value in (("conservative", triple.conservative), ("upside", triple.upside)):
            modeled = model_arr(
                capacity_result,
                config,
                roster,
                variant="base",
                overrides={name: value},
            )
            rows.append(
                {
                    "lever": name,
                    "direction": direction,
                    "value": value,
                    "modeled_arr_fy": modeled["modeled_arr_fy"],
                    "delta_vs_base": round(modeled["modeled_arr_fy"] - base["modeled_arr_fy"], 2),
                    "gap_to_target": modeled["gap_to_target"],
                }
            )
    return rows
