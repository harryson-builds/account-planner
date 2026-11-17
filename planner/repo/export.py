"""Spreadsheet-safe CSV exports."""

from __future__ import annotations

import csv
import re
from io import StringIO
from typing import Any, Iterable

_ID = re.compile(r"^[A-Z]{2,}-[A-Z0-9-]+$")


def safe_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if _ID.match(text):
        return f'="{text}"'
    if text[:1] in {"=", "+", "-", "@"}:
        return f"'{text}"
    return text


def rows_to_csv(headers: list[str], rows: Iterable[dict[str, Any]]) -> str:
    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([safe_cell(row.get(h, "")) for h in headers])
    return buf.getvalue()


ASSIGNMENT_HEADERS = [
    "account_id",
    "display_name",
    "derived_segment",
    "crm_segment",
    "discrepancy",
    "tier",
    "territory",
    "qualification_gate",
    "fit_score",
    "status",
    "reason_code",
    "owner_id",
    "proposed_owner_id",
    "proposed_sdr_id",
    "explanation",
]

EXCEPTION_HEADERS = [
    "account_id",
    "display_name",
    "derived_segment",
    "tier",
    "territory",
    "status",
    "reason_code",
    "explanation",
]


def assignment_csv(rows: list[dict[str, Any]]) -> str:
    return rows_to_csv(ASSIGNMENT_HEADERS, rows)


def exception_csv(rows: list[dict[str, Any]]) -> str:
    return rows_to_csv(EXCEPTION_HEADERS, rows)
