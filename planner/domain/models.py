"""Typed records for a planning snapshot."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["AE", "SDR"]
EligibilityStatus = Literal["active", "future", "departed"]
Gate = Literal["PASS", "FAIL", "HOLD"]
Tier = Literal["A", "B", "C", "D"]


def parse_bool(value: object) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(float(str(value).strip()))


def parse_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(str(value).strip())


def parse_optional_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value).strip()[:10])


def parse_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class Account(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str
    display_name: str
    employee_count: int | None = None
    crm_segment: str | None = None
    country: str | None = None
    territory: str | None = None
    industry: str | None = None
    tier: str | None = None
    qualification_gate: str = "HOLD"
    fit_score: float | None = None
    intent_score: float | None = None
    owner_id: str | None = None
    sdr_id: str | None = None
    parent_account_id: str | None = None
    is_customer: bool = False
    has_open_opportunity: bool = False
    lock_end_date: date | None = None

    @field_validator("account_id", "display_name", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("required")
        return text

    @field_validator("employee_count", mode="before")
    @classmethod
    def _emp(cls, value: object) -> int | None:
        return parse_optional_int(value)

    @field_validator(
        "crm_segment",
        "country",
        "territory",
        "industry",
        "tier",
        "owner_id",
        "sdr_id",
        "parent_account_id",
        mode="before",
    )
    @classmethod
    def _opt_str(cls, value: object) -> str | None:
        return parse_optional_str(value)

    @field_validator("qualification_gate", mode="before")
    @classmethod
    def _gate(cls, value: object) -> str:
        text = parse_optional_str(value)
        return text or "HOLD"

    @field_validator("fit_score", "intent_score", mode="before")
    @classmethod
    def _opt_float(cls, value: object) -> float | None:
        return parse_optional_float(value)

    @field_validator("is_customer", "has_open_opportunity", mode="before")
    @classmethod
    def _flag(cls, value: object) -> bool:
        return parse_bool(value)

    @field_validator("lock_end_date", mode="before")
    @classmethod
    def _lock(cls, value: object) -> date | None:
        return parse_optional_date(value)


class Seat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    seat_id: str
    rep_id: str | None = None
    role: str
    segment: str
    territory: str
    start_date: date
    end_date: date | None = None
    ramp_profile: str = "standard"
    eligibility_status: str = "active"
    cap_override: int | None = None

    @field_validator("seat_id", "role", "segment", "territory", "ramp_profile", "eligibility_status", mode="before")
    @classmethod
    def _req(cls, value: object) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("required")
        return text

    @field_validator("rep_id", mode="before")
    @classmethod
    def _rep(cls, value: object) -> str | None:
        return parse_optional_str(value)

    @field_validator("start_date", mode="before")
    @classmethod
    def _start(cls, value: object) -> date:
        parsed = parse_optional_date(value)
        if parsed is None:
            raise ValueError("start_date required")
        return parsed

    @field_validator("end_date", mode="before")
    @classmethod
    def _end(cls, value: object) -> date | None:
        return parse_optional_date(value)

    @field_validator("cap_override", mode="before")
    @classmethod
    def _cap(cls, value: object) -> int | None:
        return parse_optional_int(value)

    def is_staffed(self) -> bool:
        return bool(self.rep_id)

    def is_open_on(self, as_of: date) -> bool:
        if self.eligibility_status == "departed":
            return False
        if as_of < self.start_date:
            return False
        if self.end_date is not None and as_of > self.end_date:
            return False
        return True

    def is_active_named(self, as_of: date) -> bool:
        """Staffed and started; 'future' seats become named owners once start_date arrives."""
        return self.is_staffed() and self.is_open_on(as_of)

    def is_future(self, as_of: date) -> bool:
        if self.eligibility_status == "departed":
            return False
        return as_of < self.start_date


class Activity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    activity_id: str
    account_id: str
    timestamp: datetime
    activity_type: str
    rep_id: str | None = None
    outcome: str | None = None

    @field_validator("activity_id", "account_id", "activity_type", mode="before")
    @classmethod
    def _req(cls, value: object) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("required")
        return text

    @field_validator("rep_id", "outcome", mode="before")
    @classmethod
    def _opt(cls, value: object) -> str | None:
        return parse_optional_str(value)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ts(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
        if " " in text:
            return datetime.fromisoformat(text)
        return datetime.fromisoformat(f"{text}T00:00:00")


class Snapshot(BaseModel):
    snapshot_date: date
    source: str = "demo"
    accounts: list[Account] = Field(default_factory=list)
    roster: list[Seat] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)

    def account_map(self) -> dict[str, Account]:
        return {a.account_id: a for a in self.accounts}

    def seat_by_rep(self, as_of: date | None = None) -> dict[str, Seat]:
        out: dict[str, Seat] = {}
        for seat in self.roster:
            if not seat.rep_id:
                continue
            if as_of is not None and not seat.is_open_on(as_of) and not seat.is_future(as_of):
                continue
            out[seat.rep_id] = seat
        return out
