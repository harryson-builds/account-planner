"""Worked-account calibration from qualifying touches."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any

from planner.config.schema import SEGMENTS, ScenarioConfig
from planner.domain.models import Snapshot


def _as_dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


def calibrate(
    snapshot: Snapshot,
    config: ScenarioConfig,
    assignment_rows: list[dict[str, Any]],
    as_of: date | None = None,
) -> dict[str, Any]:
    as_of = as_of or snapshot.snapshot_date
    lookback_start = as_of - timedelta(days=config.activity.lookback_days)
    qualifying = {t.lower() for t in config.activity.qualifying_types}
    min_touches = config.activity.min_touches

    assigned = [
        r
        for r in assignment_rows
        if r.get("status") in {"RETAINED", "PROPOSED"} or r.get("proposed_owner_id") or r.get("owner_id")
    ]
    assigned_ids = {r["account_id"] for r in assigned}
    segment_of = {r["account_id"]: r.get("derived_segment") for r in assignment_rows}

    touches: dict[str, int] = defaultdict(int)
    for act in snapshot.activities:
        ts = act.timestamp
        if ts.date() < lookback_start or ts.date() > as_of:
            continue
        if act.activity_type.lower() not in qualifying:
            continue
        if act.account_id in assigned_ids:
            touches[act.account_id] += 1

    by_seg: dict[str, dict[str, Any]] = {}
    for seg in SEGMENTS:
        ids = [r["account_id"] for r in assigned if r.get("derived_segment") == seg]
        if not ids:
            by_seg[seg] = {
                "n": 0,
                "worked": 0,
                "untouched": 0,
                "untouched_share": None,
                "median_touches": None,
                "sample_size": 0,
            }
            continue
        counts = [touches.get(i, 0) for i in ids]
        worked = sum(1 for c in counts if c >= min_touches)
        untouched = len(ids) - worked
        by_seg[seg] = {
            "n": len(ids),
            "worked": worked,
            "untouched": untouched,
            "untouched_share": round(untouched / len(ids), 4),
            "median_touches": median(counts) if counts else None,
            "sample_size": len(ids),
        }

    worked_ids = [i for i in assigned_ids if touches.get(i, 0) >= min_touches]
    untouched_ids = sorted(assigned_ids - set(worked_ids))
    n = len(assigned_ids)
    overall_untouched = (len(untouched_ids) / n) if n else None
    lookback_days = config.activity.lookback_days
    worked_share = (len(worked_ids) / n) if n else None
    # Convert a lookback worked-share into an implied monthly first-worked rate
    # assuming a constant hazard: 1 - (1 - share)^(30 / lookback_days).
    implied_monthly = None
    if worked_share is not None and lookback_days > 0:
        months = lookback_days / 30.0
        implied_monthly = round(1 - (1 - worked_share) ** (1 / months), 4) if months else None
    arr_rate = config.arr.worked_rate.base
    drift = None
    if implied_monthly is not None:
        drift = round(arr_rate - implied_monthly, 4)
    return {
        "method": "proxy_snapshot_ownership",
        "method_note": (
            "Worked rate uses snapshot/proposed ownership as a proxy because this demo has no "
            "historical ownership timeline. Qualifying types, minimum touches, and lookback "
            "come from the scenario YAML."
        ),
        "lookback_days": config.activity.lookback_days,
        "lookback_start": lookback_start.isoformat(),
        "as_of": as_of.isoformat(),
        "qualifying_types": list(config.activity.qualifying_types),
        "min_touches": min_touches,
        "assigned_accounts": n,
        "worked_accounts": len(worked_ids),
        "untouched_accounts": len(untouched_ids),
        "untouched_share": round(overall_untouched, 4) if overall_untouched is not None else None,
        "median_touches": median([touches.get(i, 0) for i in assigned_ids]) if assigned_ids else None,
        "by_segment": by_seg,
        "untouched_sample": [
            {"account_id": i, "segment": segment_of.get(i)} for i in untouched_ids[:15]
        ],
        "worked_rate_used_in_arr": arr_rate,
        "implied_monthly_worked_rate": implied_monthly,
        "worked_rate_drift": drift,
        "worked_rate_note": (
            "Cap scenarios share this default worked-account rate unless the scenario YAML "
            "sets a documented historical calibration. If implied_monthly_worked_rate is far "
            "from worked_rate_used_in_arr, recalibrate before a hiring decision."
        ),
    }
