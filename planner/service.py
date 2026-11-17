"""Application service used by Streamlit pages and tests."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from planner.config.schema import ScenarioConfig, list_scenarios, load_scenario, merge_overrides
from planner.domain.activity import calibrate
from planner.domain.arr import model_arr, sensitivity, three_variants
from planner.domain.capacity import simulate_year
from planner.domain.dates import shift_roster
from planner.domain.models import Account, Snapshot
from planner.domain.pipeline import run_assignment
from planner.domain.release import approved_for_release, apply_reviews, build_ledger_rows, recheck_batch
from planner.paths import DEFAULT_DB
from planner.repo.db import Database
from planner.repo.export import assignment_csv, exception_csv
from planner.repo.seed import ensure_seeded
from planner.repo.validator import ValidationResult, validate_csv_bundle


class PlannerService:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db = Database(db_path or DEFAULT_DB)
        ensure_seeded(self.db)

    def snapshot_record(self) -> tuple[int, Snapshot]:
        loaded = self.db.load_snapshot()
        if loaded is None:
            ensure_seeded(self.db)
            loaded = self.db.load_snapshot()
        assert loaded is not None
        sid, snap = loaded
        return sid, self._apply_locks(snap)

    def _apply_locks(self, snap: Snapshot) -> Snapshot:
        locks = self.db.active_locks(snap.snapshot_date)
        if not locks:
            return snap
        accounts: list[Account] = []
        for account in snap.accounts:
            copy = account.model_copy()
            lock = locks.get(account.account_id)
            if lock:
                copy.owner_id = lock.get("new_owner_id") or copy.owner_id
                if lock.get("lock_end_date"):
                    copy.lock_end_date = date.fromisoformat(lock["lock_end_date"])
            accounts.append(copy)
        return snap.model_copy(update={"accounts": accounts})

    def raw_snapshot(self) -> tuple[int, Snapshot]:
        loaded = self.db.load_snapshot()
        assert loaded is not None
        return loaded

    def scenario(self, scenario_id: str) -> ScenarioConfig:
        base = load_scenario(scenario_id)
        return merge_overrides(base, self.db.get_overrides(scenario_id))

    def scenarios(self) -> list[ScenarioConfig]:
        return list_scenarios()

    def save_overrides(self, scenario_id: str, payload: dict[str, Any]) -> None:
        self.db.save_overrides(scenario_id, payload)

    def clear_overrides(self, scenario_id: str) -> None:
        self.db.clear_overrides(scenario_id)

    def assignment(self, scenario_id: str) -> dict[str, Any]:
        sid, snap = self.snapshot_record()
        config = self.scenario(scenario_id)
        released = set(self.db.active_locks(snap.snapshot_date))
        result = run_assignment(snap, config, released_ids=released)
        result["snapshot_id"] = sid
        result["snapshot_date"] = snap.snapshot_date.isoformat()
        result["snapshot_source"] = snap.source
        reviews = self.db.list_reviews(sid)
        result["rows"] = apply_reviews(result["rows"], reviews)
        return result

    def persist_run(self, scenario_id: str, result: dict[str, Any]) -> int:
        sid, _ = self.snapshot_record()
        config = self.scenario(scenario_id)
        slim = {k: result[k] for k in ("as_of", "kpis", "matrix", "scenario_id", "scenario_version") if k in result}
        return self.db.save_run(
            sid,
            config.id,
            config.version,
            config.model_dump(mode="json"),
            date.fromisoformat(result["as_of"]),
            slim,
        )

    def fy27(self, scenario_id: str) -> dict[str, Any]:
        _, snap = self.snapshot_record()
        config = self.scenario(scenario_id)
        released = set(self.db.active_locks(snap.snapshot_date))
        cap = simulate_year(snap, config, released_ids=released)
        roster = shift_roster(snap.roster, config)
        arrs = three_variants(cap, config, roster)
        sens = sensitivity(cap, config, roster)
        act = calibrate(snap, config, self.assignment(scenario_id)["rows"], snap.snapshot_date)
        return {
            "capacity": cap,
            "arr": arrs,
            "sensitivity": sens,
            "activity": act,
            "scenario_id": config.id,
            "scenario_version": config.version,
        }

    def compare_scenarios(self) -> dict[str, Any]:
        out = {}
        for cfg in self.scenarios():
            fy = self.fy27(cfg.id)
            assign = self.assignment(cfg.id)
            out[cfg.id] = {
                "name": cfg.name,
                "kpis": assign["kpis"],
                "viable_seats_m0": fy["capacity"]["months"][0]["viable_seats"] if fy["capacity"]["months"] else 0,
                "modeled_arr_base": fy["arr"]["base"]["modeled_arr_fy"],
                "gap_base": fy["arr"]["base"]["gap_to_target"],
                "untouched_share": fy["activity"]["untouched_share"],
                "caps": cfg.caps,
                "hiring_shift_months": cfg.hiring_shift_months,
            }
        return out

    def upsert_review(
        self,
        account_id: str,
        decision: str,
        reason: str,
        reviewer: str,
        scenario_id: str = "baseline",
    ) -> None:
        sid, _ = self.snapshot_record()
        row = next((r for r in self.assignment(scenario_id)["rows"] if r["account_id"] == account_id), None)
        self.db.upsert_review(
            sid,
            account_id,
            decision,
            reason,
            reviewer,
            preview_owner_id=None if row is None else row.get("owner_id"),
            proposed_owner_id=None if row is None else row.get("proposed_owner_id"),
        )

    def release(
        self,
        scenario_id: str,
        batch_id: str,
        reviewer: str,
    ) -> dict[str, Any]:
        existing = self.db.get_batch(batch_id)
        sid, snap = self.snapshot_record()
        config = self.scenario(scenario_id)
        if existing:
            same_context = (
                int(existing["snapshot_id"]) == sid and existing["scenario_id"] == config.id
            )
            if same_context:
                return {
                    "status": "idempotent",
                    "result": existing["result"],
                    "conflicts": [],
                }
            return {
                "status": "batch_id_in_use",
                "result": existing["result"],
                "conflicts": [],
                "message": (
                    f"Batch id {batch_id} already committed for snapshot "
                    f"{existing['snapshot_id']} / scenario {existing['scenario_id']}. "
                    "Choose a new batch id; the earlier ledger rows were not overwritten."
                ),
            }
        assignment = self.assignment(scenario_id)
        reviews = self.db.list_reviews(sid)
        live = approved_for_release(assignment["rows"])
        approved: list[dict[str, Any]] = []
        pre_conflicts: list[dict[str, Any]] = []
        for row in live:
            review = reviews.get(row["account_id"]) or {}
            frozen_owner = review.get("proposed_owner_id")
            if frozen_owner and frozen_owner != row.get("proposed_owner_id"):
                pre_conflicts.append(
                    {
                        "account_id": row["account_id"],
                        "code": "PREVIEW_STALE",
                        "detail": (
                            f"Approved owner was {frozen_owner}; current proposal is "
                            f"{row.get('proposed_owner_id')}. Re-review before release."
                        ),
                    }
                )
                continue
            approved.append(
                {
                    "account_id": row["account_id"],
                    "owner_id": review.get("preview_owner_id"),
                    "proposed_owner_id": row.get("proposed_owner_id"),
                    "status": "PROPOSED",
                }
            )
        if pre_conflicts:
            return {
                "status": "pending_conflict",
                "result": None,
                "conflicts": pre_conflicts,
                "message": "Current state conflicts with the preview. Batch left pending; ledger unchanged.",
            }
        if not approved:
            return {"status": "empty", "result": None, "conflicts": [], "message": "No approved proposed rows."}
        locks = self.db.active_locks(snap.snapshot_date)
        conflicts = recheck_batch(snap, config, approved, snap.snapshot_date, locks)
        if conflicts:
            return {
                "status": "pending_conflict",
                "result": None,
                "conflicts": conflicts,
                "message": "Current state conflicts with the preview. Batch left pending; ledger unchanged.",
            }
        ledger_rows = build_ledger_rows(approved, snap.snapshot_date, config.lock_days)
        result = self.db.commit_release(
            batch_id=batch_id,
            snapshot_id=sid,
            scenario_id=config.id,
            rule_version=config.version,
            reviewer=reviewer,
            rows=ledger_rows,
        )
        self.persist_run(scenario_id, self.assignment(scenario_id))
        return {"status": "released", "result": result, "conflicts": []}

    def ledger(self) -> list[dict[str, Any]]:
        return self.db.list_ledger()

    def import_csv(
        self,
        accounts_src: Any,
        roster_src: Any,
        activities_src: Any,
        snapshot_date: date,
        source: str = "csv",
    ) -> ValidationResult:
        ledger_before = self.db.ledger_count()
        result = validate_csv_bundle(accounts_src, roster_src, activities_src, snapshot_date, source=source)
        self.db.record_import_attempt(source, result.ok, result.error_table())
        if result.ok and result.snapshot is not None:
            self.db.save_snapshot(result.snapshot)
        assert self.db.ledger_count() == ledger_before
        return result

    def assignment_export(self, scenario_id: str) -> str:
        return assignment_csv(self.assignment(scenario_id)["rows"])

    def exception_export(self, scenario_id: str) -> str:
        return exception_csv(self.assignment(scenario_id)["exceptions"])

    def cache_key(self, scenario_id: str) -> str:
        sid, snap = self.snapshot_record()
        overrides = self.db.get_overrides(scenario_id)
        raw = json.dumps(
            {"sid": sid, "scenario": scenario_id, "ov": overrides, "n": len(snap.accounts)},
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
