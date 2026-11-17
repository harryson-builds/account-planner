"""Propose books: retain protected ownership, then fill least-loaded eligible AEs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from planner.config.schema import ScenarioConfig
from planner.domain.dates import ramp_factor, shift_roster
from planner.domain.models import Account, Seat, Snapshot
from planner.domain.protect import is_protected, protection_reason
from planner.domain.qualify import gate_pass, policy_eligible
from planner.domain.segment import derived_segment, discrepancy, tier_rank

REASON_INVENTORY = "NOT_POLICY_ELIGIBLE"
REASON_HEADCOUNT = "MISSING_HEADCOUNT"
REASON_GEO = "MISSING_GEOGRAPHY"
REASON_NO_AE = "NO_ELIGIBLE_AE"
REASON_FUTURE = "FUTURE_SEAT_ONLY"
REASON_SDR = "REQUIRED_SDR_GAP"
REASON_PARENT = "PARENT_CHILD_AMBIGUOUS"
REASON_FULL = "BOOK_FULL"
REASON_PROTECTED = "PROTECTED_RETAINED"
REASON_PROTECTED_GAP = "PROTECTED_UNASSIGNED"
REASON_PROPOSED = "PROPOSED"
REASON_UNALLOCATED = "UNALLOCATED"


@dataclass
class RepBook:
    seat: Seat
    cap: int
    account_ids: list[str] = field(default_factory=list)
    tier_mix: dict[str, int] = field(default_factory=lambda: {"A": 0, "B": 0, "C": 0, "D": 0, "": 0})

    @property
    def fill_ratio(self) -> float:
        if self.cap <= 0:
            return 999.0
        return len(self.account_ids) / self.cap

    @property
    def open_slots(self) -> int:
        return max(0, self.cap - len(self.account_ids))

    def add(self, account_id: str, tier: str | None) -> None:
        self.account_ids.append(account_id)
        key = tier or ""
        self.tier_mix[key] = self.tier_mix.get(key, 0) + 1

    def as_dict(self) -> dict:
        return {
            "rep_id": self.seat.rep_id,
            "seat_id": self.seat.seat_id,
            "role": self.seat.role,
            "segment": self.seat.segment,
            "territory": self.seat.territory,
            "start_date": self.seat.start_date.isoformat(),
            "end_date": self.seat.end_date.isoformat() if self.seat.end_date else None,
            "ramp_profile": self.seat.ramp_profile,
            "cap": self.cap,
            "book_count": len(self.account_ids),
            "fill_ratio": round(self.fill_ratio, 4),
            "open_slots": self.open_slots,
            "tier_mix": dict(self.tier_mix),
            "account_ids": list(self.account_ids),
            "below_viable": False,
            "over_cap": len(self.account_ids) > self.cap,
        }


@dataclass
class AccountDecision:
    account_id: str
    display_name: str
    employee_count: int | None
    crm_segment: str | None
    derived_segment: str
    discrepancy: str | None
    territory: str | None
    country: str | None
    industry: str | None
    tier: str | None
    qualification_gate: str
    fit_score: float | None
    owner_id: str | None
    sdr_id: str | None
    proposed_owner_id: str | None
    proposed_sdr_id: str | None
    parent_account_id: str | None
    is_customer: bool
    has_open_opportunity: bool
    lock_end_date: date | None
    gate_pass: bool
    policy_eligible: bool
    currently_assignable: bool
    protected: bool
    status: str
    reason_code: str
    explanation: str

    def as_dict(self) -> dict:
        data = self.__dict__.copy()
        if self.lock_end_date is not None:
            data["lock_end_date"] = self.lock_end_date.isoformat()
        return data


def _base_decision(account: Account, config: ScenarioConfig, as_of: date) -> AccountDecision:
    derived = derived_segment(account.employee_count, config)
    eligible = policy_eligible(account, derived, config)
    return AccountDecision(
        account_id=account.account_id,
        display_name=account.display_name,
        employee_count=account.employee_count,
        crm_segment=account.crm_segment,
        derived_segment=derived,
        discrepancy=discrepancy(account, derived),
        territory=account.territory,
        country=account.country,
        industry=account.industry,
        tier=account.tier,
        qualification_gate=account.qualification_gate,
        fit_score=account.fit_score,
        owner_id=account.owner_id,
        sdr_id=account.sdr_id,
        proposed_owner_id=None,
        proposed_sdr_id=account.sdr_id,
        parent_account_id=account.parent_account_id,
        is_customer=account.is_customer,
        has_open_opportunity=account.has_open_opportunity,
        lock_end_date=account.lock_end_date,
        gate_pass=gate_pass(account, config),
        policy_eligible=eligible,
        currently_assignable=False,
        protected=is_protected(account, as_of),
        status="INVENTORY",
        reason_code=REASON_INVENTORY,
        explanation="",
    )


def _fit_key(account: Account) -> float:
    return float(account.fit_score) if account.fit_score is not None else float("-inf")


def sort_accounts(accounts: list[Account]) -> list[Account]:
    return sorted(
        accounts,
        key=lambda a: (tier_rank(a.tier), -_fit_key(a), a.account_id),
    )


def _geo_ok(account: Account) -> bool:
    return bool(account.country) and bool(account.territory)


def _matching_ae_seats(roster: list[Seat], segment: str, territory: str) -> list[Seat]:
    return [
        s
        for s in roster
        if s.role == "AE" and s.segment == segment and s.territory == territory
    ]


def _active_sdrs(roster: list[Seat], territory: str, as_of: date) -> list[Seat]:
    return [
        s
        for s in roster
        if s.role == "SDR" and s.territory == territory and s.is_active_named(as_of)
    ]


def _pick_sdr(account: Account, roster: list[Seat], as_of: date) -> str | None:
    named = [s for s in roster if s.rep_id == account.sdr_id and s.is_active_named(as_of)]
    if named:
        return named[0].rep_id
    pool = _active_sdrs(roster, account.territory or "", as_of)
    if not pool:
        return None
    pool = sorted(pool, key=lambda s: s.rep_id or "")
    return pool[0].rep_id


def _eligible_books(
    books: dict[str, RepBook],
    segment: str,
    territory: str,
    as_of: date,
    require_open_slot: bool,
) -> list[RepBook]:
    out = []
    for book in books.values():
        seat = book.seat
        if seat.role != "AE":
            continue
        if seat.segment != segment or seat.territory != territory:
            continue
        if not seat.is_active_named(as_of):
            continue
        if require_open_slot and book.open_slots <= 0:
            continue
        out.append(book)
    return out


def _choose_book(candidates: list[RepBook]) -> RepBook:
    return sorted(candidates, key=lambda b: (b.fill_ratio, b.seat.rep_id or ""))[0]


def _staffing_block(
    account: Account,
    derived: str,
    roster: list[Seat],
    books: dict[str, RepBook],
    config: ScenarioConfig,
    as_of: date,
) -> tuple[str, str] | None:
    if not _geo_ok(account):
        return REASON_GEO, "Missing country or territory; cannot route to a named book."
    seats = _matching_ae_seats(roster, derived, account.territory or "")
    active = [s for s in seats if s.is_active_named(as_of)]
    future = [s for s in seats if s.is_future(as_of)]
    if not active:
        if future:
            starts = ", ".join(sorted({s.start_date.isoformat() for s in future}))
            return (
                REASON_FUTURE,
                f"No active named AE in {account.territory} {derived}; future seat starts {starts}.",
            )
        return (
            REASON_NO_AE,
            f"No eligible AE seat in {account.territory} {derived}.",
        )
    route = config.route_for(derived)
    if route.requires_sdr and not _active_sdrs(roster, account.territory or "", as_of):
        return (
            REASON_SDR,
            f"{derived} in {account.territory} requires SDR coverage and none is active as of {as_of.isoformat()}.",
        )
    open_books = _eligible_books(books, derived, account.territory or "", as_of, require_open_slot=True)
    if not open_books:
        return REASON_FULL, f"Every active {derived} AE in {account.territory} is at or over cap."
    return None


def _parent_ambiguous(account: Account, by_id: dict[str, Account], as_of: date) -> bool:
    if not account.parent_account_id:
        return False
    parent = by_id.get(account.parent_account_id)
    if parent is None:
        return False
    # Independent named-account child of a live parent is an exception.
    if account.owner_id and parent.owner_id and account.owner_id == parent.owner_id:
        return False
    return True


def allocate(
    snapshot: Snapshot,
    config: ScenarioConfig,
    as_of: date | None = None,
    ownership_overlay: dict[str, str | None] | None = None,
) -> tuple[list[AccountDecision], dict[str, RepBook], list[Seat]]:
    as_of = as_of or snapshot.snapshot_date
    roster = shift_roster(snapshot.roster, config)
    accounts = [a.model_copy() for a in snapshot.accounts]
    if ownership_overlay:
        for account in accounts:
            if account.account_id in ownership_overlay:
                account.owner_id = ownership_overlay[account.account_id]

    books: dict[str, RepBook] = {}
    for seat in roster:
        if seat.role != "AE" or not seat.rep_id:
            continue
        cap = seat.cap_override if seat.cap_override is not None else config.cap_for(seat.segment)
        books[seat.rep_id] = RepBook(seat=seat, cap=int(cap))

    by_id = {a.account_id: a for a in accounts}
    decisions: dict[str, AccountDecision] = {
        a.account_id: _base_decision(a, config, as_of) for a in accounts
    }

    # Retain protected accounts with a still-valid named owner.
    for account in accounts:
        d = decisions[account.account_id]
        if not d.protected:
            continue
        owner = account.owner_id
        book = books.get(owner or "")
        owner_ok = bool(
            book
            and book.seat.is_active_named(as_of)
            and book.seat.segment == d.derived_segment
            and book.seat.territory == (account.territory or book.seat.territory)
        )
        if owner_ok and book is not None:
            book.add(account.account_id, account.tier)
            d.status = "RETAINED"
            d.reason_code = REASON_PROTECTED
            d.proposed_owner_id = owner
            d.explanation = (
                f"Retained on {owner}; {protection_reason(account, as_of)}. "
                f"Counts toward cap {book.cap} ({len(book.account_ids)}/{book.cap})."
            )
        # else handled in the protected-reassign pass

    protected_gaps = [
        a
        for a in sort_accounts(accounts)
        if decisions[a.account_id].protected and decisions[a.account_id].status != "RETAINED"
    ]
    for account in protected_gaps:
        d = decisions[account.account_id]
        if d.derived_segment == "Unknown":
            d.status = "BLOCKED"
            d.reason_code = REASON_HEADCOUNT
            d.explanation = "Protected account is missing employee count; cannot route a segment book."
            continue
        if _parent_ambiguous(account, by_id, as_of):
            d.status = "BLOCKED"
            d.reason_code = REASON_PARENT
            d.explanation = (
                f"Parent {account.parent_account_id} is in the snapshot; child routing needs a reviewer."
            )
            continue
        block = _staffing_block(account, d.derived_segment, roster, books, config, as_of)
        if block and block[0] != REASON_FULL:
            d.status = "BLOCKED"
            d.reason_code = REASON_PROTECTED_GAP
            d.explanation = f"Protected ({protection_reason(account, as_of)}) but {block[1]}"
            continue
        candidates = _eligible_books(
            books, d.derived_segment, account.territory or "", as_of, require_open_slot=False
        )
        # Prefer a slot if any exist; otherwise the least-loaded (may go over cap).
        open_ones = [b for b in candidates if b.open_slots > 0]
        pool = open_ones or candidates
        if not pool:
            d.status = "BLOCKED"
            d.reason_code = REASON_PROTECTED_GAP
            d.explanation = f"Protected ({protection_reason(account, as_of)}) with no named AE to receive it."
            continue
        chosen = _choose_book(pool)
        chosen.add(account.account_id, account.tier)
        d.status = "RETAINED"
        d.reason_code = REASON_PROTECTED
        d.proposed_owner_id = chosen.seat.rep_id
        d.explanation = (
            f"Protected reassignment to {chosen.seat.rep_id} after prior owner "
            f"{account.owner_id or 'none'} was invalid; {protection_reason(account, as_of)}."
        )
        if config.route_for(d.derived_segment).requires_sdr:
            d.proposed_sdr_id = _pick_sdr(account, roster, as_of)

    # Inventory / blocked / allocate remaining policy-eligible
    allocatable: list[Account] = []
    for account in accounts:
        d = decisions[account.account_id]
        if d.status == "RETAINED":
            continue
        if d.derived_segment == "Unknown":
            d.status = "BLOCKED"
            d.reason_code = REASON_HEADCOUNT
            d.explanation = "Unknown headcount; derived segment is review-only."
            continue
        if not d.policy_eligible:
            d.status = "INVENTORY"
            d.reason_code = REASON_INVENTORY
            why = []
            if not d.gate_pass:
                why.append(f"gate {account.qualification_gate}")
            if account.tier not in config.eligibility.tiers:
                why.append(f"tier {account.tier or 'blank'}")
            if d.derived_segment not in config.policy_segments():
                why.append(f"segment {d.derived_segment} excluded by policy")
            d.explanation = "Not policy-eligible (" + "; ".join(why) + ")."
            continue
        if _parent_ambiguous(account, by_id, as_of):
            d.status = "BLOCKED"
            d.reason_code = REASON_PARENT
            d.currently_assignable = False
            d.explanation = (
                f"Parent {account.parent_account_id} is in the snapshot; do not auto-route the child."
            )
            continue
        block = _staffing_block(account, d.derived_segment, roster, books, config, as_of)
        if block:
            d.status = "BLOCKED"
            d.reason_code = block[0]
            d.explanation = block[1]
            continue
        d.currently_assignable = True
        allocatable.append(account)

    for account in sort_accounts(allocatable):
        d = decisions[account.account_id]
        candidates = _eligible_books(
            books, d.derived_segment, account.territory or "", as_of, require_open_slot=True
        )
        if not candidates:
            d.status = "UNALLOCATED"
            d.reason_code = REASON_FULL
            d.currently_assignable = False
            d.explanation = (
                f"Policy-eligible {d.derived_segment} {account.tier} in {account.territory} "
                "but no open slot remained after higher-priority accounts."
            )
            continue
        chosen = _choose_book(candidates)
        before = chosen.fill_ratio
        chosen.add(account.account_id, account.tier)
        d.status = "PROPOSED"
        d.reason_code = REASON_PROPOSED
        d.proposed_owner_id = chosen.seat.rep_id
        if config.route_for(d.derived_segment).requires_sdr:
            d.proposed_sdr_id = _pick_sdr(account, roster, as_of)
        d.explanation = (
            f"Allocated to {chosen.seat.rep_id} (lowest fill {before:.2f}, then rep id); "
            f"tier {account.tier}, fit {account.fit_score if account.fit_score is not None else 'n/a'}."
        )

    ordered = [decisions[a.account_id] for a in accounts]
    return ordered, books, roster


def books_as_dicts(books: dict[str, RepBook], config: ScenarioConfig, as_of: date) -> list[dict]:
    rows = []
    for book in books.values():
        row = book.as_dict()
        row["below_viable"] = (
            book.seat.is_active_named(as_of)
            and len(book.account_ids) < config.viable_min_for(book.seat.segment)
        )
        row["ramp_factor"] = ramp_factor(
            book.seat.start_date, as_of, config.ramp_curve(book.seat.ramp_profile)
        )
        rows.append(row)
    return sorted(rows, key=lambda r: (r["segment"], r["territory"], r["rep_id"] or ""))
