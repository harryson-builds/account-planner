"""CSV contract validation. Structural failures reject the import."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from os import PathLike
from typing import Any, TextIO

from planner.domain.models import Account, Activity, Seat, Snapshot, parse_optional_date

ACCOUNT_HEADERS = [
    "account_id",
    "display_name",
    "employee_count",
    "crm_segment",
    "country",
    "territory",
    "industry",
    "tier",
    "qualification_gate",
    "fit_score",
    "intent_score",
    "owner_id",
    "sdr_id",
    "parent_account_id",
    "is_customer",
    "has_open_opportunity",
    "lock_end_date",
]
ROSTER_HEADERS = [
    "seat_id",
    "rep_id",
    "role",
    "segment",
    "territory",
    "start_date",
    "end_date",
    "ramp_profile",
    "eligibility_status",
    "cap_override",
]
ACTIVITY_HEADERS = [
    "activity_id",
    "account_id",
    "timestamp",
    "activity_type",
    "rep_id",
    "outcome",
]

MAX_ROWS = 100_000
MAX_NAME_LEN = 200

TIERS = {"A", "B", "C", "D"}
GATES = {"PASS", "FAIL", "HOLD"}
CRM_SEGMENTS = {"Commercial", "Mid-Market", "Enterprise"}
ROLES = {"AE", "SDR"}
STATUSES = {"active", "future", "departed"}
SEAT_SEGMENTS = {"Commercial", "Mid-Market", "Enterprise"}


@dataclass
class RowError:
    file: str
    row: int
    field: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"file": self.file, "row": self.row, "field": self.field, "message": self.message}


@dataclass
class ValidationResult:
    ok: bool
    errors: list[RowError] = field(default_factory=list)
    snapshot: Snapshot | None = None

    def error_table(self) -> list[dict[str, Any]]:
        return [e.as_dict() for e in self.errors]


def _as_text(source: str | PathLike | TextIO) -> str:
    if hasattr(source, "read"):
        data = source.read()
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return str(data)
    if hasattr(source, "getvalue"):
        data = source.getvalue()
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return str(data)
    path = str(source)
    return open(path, newline="").read()


def _reader(source: str | PathLike | TextIO) -> tuple[list[str], list[dict[str, str]]]:
    text = _as_text(source)
    stream = io.StringIO(text)
    reader = csv.DictReader(stream)
    headers = reader.fieldnames or []
    rows = []
    for raw in reader:
        rows.append({k: ("" if v is None else str(v).strip()) for k, v in raw.items() if k is not None})
    return list(headers), rows


def _missing_headers(file: str, headers: list[str], required: list[str], errors: list[RowError]) -> None:
    missing = [h for h in required if h not in headers]
    extra_ok = True  # extra columns ignored
    _ = extra_ok
    if missing:
        errors.append(RowError(file, 1, ",".join(missing), f"missing required headers: {missing}"))


def _dupes(file: str, rows: list[dict[str, str]], field: str, errors: list[RowError]) -> None:
    seen: dict[str, int] = {}
    for i, row in enumerate(rows, start=2):
        key = row.get(field, "")
        if not key:
            continue
        if key in seen:
            errors.append(RowError(file, i, field, f"duplicate id {key} (also row {seen[key]})"))
        else:
            seen[key] = i


def validate_csv_bundle(
    accounts_src: str | PathLike | TextIO,
    roster_src: str | PathLike | TextIO,
    activities_src: str | PathLike | TextIO,
    snapshot_date: date,
    source: str = "csv",
) -> ValidationResult:
    errors: list[RowError] = []
    acc_headers, acc_rows = _reader(accounts_src)
    ros_headers, ros_rows = _reader(roster_src)
    act_headers, act_rows = _reader(activities_src)

    _missing_headers("accounts.csv", acc_headers, ACCOUNT_HEADERS, errors)
    _missing_headers("roster.csv", ros_headers, ROSTER_HEADERS, errors)
    _missing_headers("activities.csv", act_headers, ACTIVITY_HEADERS, errors)
    if errors:
        return ValidationResult(ok=False, errors=errors)

    for file, rows in (("accounts.csv", acc_rows), ("roster.csv", ros_rows), ("activities.csv", act_rows)):
        if len(rows) > MAX_ROWS:
            errors.append(
                RowError(file, 1, "rows", f"exceeds {MAX_ROWS} row limit ({len(rows)} rows)")
            )
    if errors:
        return ValidationResult(ok=False, errors=errors)

    _dupes("accounts.csv", acc_rows, "account_id", errors)
    _dupes("roster.csv", ros_rows, "seat_id", errors)
    _dupes("activities.csv", act_rows, "activity_id", errors)

    account_ids: set[str] = set()
    for i, row in enumerate(acc_rows, start=2):
        if not row.get("account_id"):
            errors.append(RowError("accounts.csv", i, "account_id", "required"))
        else:
            account_ids.add(row["account_id"])
        if not row.get("display_name"):
            errors.append(RowError("accounts.csv", i, "display_name", "required"))
        elif len(row["display_name"]) > MAX_NAME_LEN:
            errors.append(RowError("accounts.csv", i, "display_name", f"longer than {MAX_NAME_LEN} characters"))
        tier = row.get("tier") or ""
        if tier and tier not in TIERS:
            errors.append(RowError("accounts.csv", i, "tier", f"unknown enum {tier}"))
        gate = row.get("qualification_gate") or ""
        if gate and gate not in GATES:
            errors.append(RowError("accounts.csv", i, "qualification_gate", f"unknown enum {gate}"))
        seg = row.get("crm_segment") or ""
        if seg and seg not in CRM_SEGMENTS:
            errors.append(RowError("accounts.csv", i, "crm_segment", f"unknown enum {seg}"))
        if row.get("employee_count"):
            try:
                int(float(row["employee_count"]))
            except ValueError:
                errors.append(RowError("accounts.csv", i, "employee_count", "not an integer"))
        for num_field in ("fit_score", "intent_score"):
            if row.get(num_field):
                try:
                    float(row[num_field])
                except ValueError:
                    errors.append(RowError("accounts.csv", i, num_field, "not a number"))
        if row.get("lock_end_date"):
            try:
                parse_optional_date(row["lock_end_date"])
            except ValueError:
                errors.append(RowError("accounts.csv", i, "lock_end_date", "expected YYYY-MM-DD"))
        for flag in ("is_customer", "has_open_opportunity"):
            val = (row.get(flag) or "").lower()
            if val and val not in {"true", "false", "1", "0", "yes", "no", "y", "n"}:
                errors.append(RowError("accounts.csv", i, flag, "expected boolean"))

    for i, row in enumerate(acc_rows, start=2):
        parent = row.get("parent_account_id") or ""
        if parent and parent not in account_ids:
            errors.append(RowError("accounts.csv", i, "parent_account_id", f"unknown account {parent}"))

    for i, row in enumerate(ros_rows, start=2):
        if not row.get("seat_id"):
            errors.append(RowError("roster.csv", i, "seat_id", "required"))
        role = row.get("role") or ""
        if role not in ROLES:
            errors.append(RowError("roster.csv", i, "role", f"unknown enum {role}"))
        seg = row.get("segment") or ""
        if seg not in SEAT_SEGMENTS:
            errors.append(RowError("roster.csv", i, "segment", f"unknown enum {seg}"))
        status = row.get("eligibility_status") or ""
        if status not in STATUSES:
            errors.append(RowError("roster.csv", i, "eligibility_status", f"unknown enum {status}"))
        if not row.get("territory"):
            errors.append(RowError("roster.csv", i, "territory", "required"))
        try:
            parse_optional_date(row.get("start_date"))
            if not row.get("start_date"):
                raise ValueError("empty")
        except ValueError:
            errors.append(RowError("roster.csv", i, "start_date", "expected YYYY-MM-DD"))
        if row.get("end_date"):
            try:
                parse_optional_date(row["end_date"])
            except ValueError:
                errors.append(RowError("roster.csv", i, "end_date", "expected YYYY-MM-DD"))
        if row.get("cap_override"):
            try:
                int(float(row["cap_override"]))
            except ValueError:
                errors.append(RowError("roster.csv", i, "cap_override", "not an integer"))

    for i, row in enumerate(act_rows, start=2):
        if not row.get("activity_id"):
            errors.append(RowError("activities.csv", i, "activity_id", "required"))
        acc = row.get("account_id") or ""
        if acc not in account_ids:
            errors.append(RowError("activities.csv", i, "account_id", f"unknown account {acc}"))
        if not row.get("activity_type"):
            errors.append(RowError("activities.csv", i, "activity_type", "required"))
        try:
            Activity.model_validate(row)
        except Exception as exc:  # noqa: BLE001 — collect parse errors per row
            errors.append(RowError("activities.csv", i, "timestamp", str(exc)))

    if errors:
        return ValidationResult(ok=False, errors=errors)

    accounts = [Account.model_validate(r) for r in acc_rows]
    roster = [Seat.model_validate(r) for r in ros_rows]
    activities = [Activity.model_validate(r) for r in act_rows]
    snapshot = Snapshot(
        snapshot_date=snapshot_date,
        source=source,
        accounts=accounts,
        roster=roster,
        activities=activities,
    )
    return ValidationResult(ok=True, snapshot=snapshot)


def validate_paths(accounts: Any, roster: Any, activities: Any, snapshot_date: date, source: str = "csv") -> ValidationResult:
    return validate_csv_bundle(accounts, roster, activities, snapshot_date, source=source)
