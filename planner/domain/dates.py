"""Calendar helpers for FY months and ramp."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from planner.config.schema import Fiscal, ScenarioConfig
from planner.domain.models import Seat


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def month_end(d: date) -> date:
    return add_months(month_start(d), 1) - timedelta(days=1)


def fiscal_months(fiscal: Fiscal) -> list[date]:
    """First day of each fiscal month, inclusive."""
    months: list[date] = []
    cursor = month_start(fiscal.start)
    last = month_start(fiscal.end)
    while cursor <= last:
        months.append(cursor)
        cursor = add_months(cursor, 1)
    return months


def months_between(start: date, as_of: date) -> int:
    return (as_of.year - start.year) * 12 + (as_of.month - start.month)


def ramp_factor(start: date, as_of: date, curve: list[float]) -> float:
    if as_of < start or not curve:
        return 0.0
    idx = months_between(start, as_of)
    if idx < 0:
        return 0.0
    return curve[min(idx, len(curve) - 1)]


def shift_roster(roster: list[Seat], config: ScenarioConfig) -> list[Seat]:
    """Delay FY27+ start dates without mutating source seats."""
    shift = config.hiring_shift_months
    if not shift:
        return [s.model_copy() for s in roster]
    fy_start = config.fiscal.start
    out: list[Seat] = []
    for seat in roster:
        copy = seat.model_copy()
        if copy.start_date >= fy_start:
            copy.start_date = add_months(copy.start_date, shift)
            if copy.end_date is not None and copy.end_date >= fy_start:
                copy.end_date = add_months(copy.end_date, shift)
        out.append(copy)
    return out
