"""SQLite persistence for snapshots, scenario runs, reviews, and the release ledger."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

from planner.domain.models import Account, Activity, Seat, Snapshot
from planner.paths import DEFAULT_DB, ensure_runtime_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY,
  snapshot_date TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  source TEXT NOT NULL,
  valid INTEGER NOT NULL,
  account_count INTEGER NOT NULL,
  roster_count INTEGER NOT NULL,
  activity_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshot_accounts (
  snapshot_id INTEGER NOT NULL,
  payload TEXT NOT NULL,
  FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS snapshot_roster (
  snapshot_id INTEGER NOT NULL,
  payload TEXT NOT NULL,
  FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS snapshot_activities (
  snapshot_id INTEGER NOT NULL,
  payload TEXT NOT NULL,
  FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS import_attempts (
  id INTEGER PRIMARY KEY,
  attempted_at TEXT NOT NULL,
  source TEXT NOT NULL,
  ok INTEGER NOT NULL,
  error_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_overrides (
  scenario_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  snapshot_id INTEGER NOT NULL,
  scenario_id TEXT NOT NULL,
  scenario_version TEXT NOT NULL,
  scenario_json TEXT NOT NULL,
  as_of TEXT NOT NULL,
  created_at TEXT NOT NULL,
  result_json TEXT NOT NULL,
  FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS reviews (
  snapshot_id INTEGER NOT NULL,
  account_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  preview_owner_id TEXT,
  proposed_owner_id TEXT,
  PRIMARY KEY (snapshot_id, account_id)
);

CREATE TABLE IF NOT EXISTS release_batches (
  batch_id TEXT PRIMARY KEY,
  snapshot_id INTEGER NOT NULL,
  scenario_id TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  released_at TEXT NOT NULL,
  status TEXT NOT NULL,
  result_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS release_ledger (
  id INTEGER PRIMARY KEY,
  batch_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  prev_owner_id TEXT,
  new_owner_id TEXT,
  lock_end_date TEXT,
  reviewer TEXT NOT NULL,
  ts TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  FOREIGN KEY (batch_id) REFERENCES release_batches(batch_id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class Database:
    def __init__(self, path: Path | None = None) -> None:
        ensure_runtime_dirs()
        self.path = path or DEFAULT_DB
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _connect(self.path) as conn:
            conn.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return _connect(self.path)

    def record_import_attempt(self, source: str, ok: bool, errors: list[dict[str, Any]]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO import_attempts (attempted_at, source, ok, error_json) VALUES (?, ?, ?, ?)",
                (_now(), source, int(ok), json.dumps(errors)),
            )

    def save_snapshot(self, snapshot: Snapshot) -> int:
        payload_accounts = json.dumps([a.model_dump(mode="json") for a in snapshot.accounts])
        payload_roster = json.dumps([s.model_dump(mode="json") for s in snapshot.roster])
        payload_acts = json.dumps([a.model_dump(mode="json") for a in snapshot.activities])
        now = _now()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO snapshots (snapshot_date, imported_at, source, valid, account_count, roster_count, activity_count)
                VALUES (?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_date.isoformat(),
                    now,
                    snapshot.source,
                    len(snapshot.accounts),
                    len(snapshot.roster),
                    len(snapshot.activities),
                ),
            )
            snap_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO snapshot_accounts (snapshot_id, payload) VALUES (?, ?)",
                (snap_id, payload_accounts),
            )
            conn.execute(
                "INSERT INTO snapshot_roster (snapshot_id, payload) VALUES (?, ?)",
                (snap_id, payload_roster),
            )
            conn.execute(
                "INSERT INTO snapshot_activities (snapshot_id, payload) VALUES (?, ?)",
                (snap_id, payload_acts),
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('current_snapshot_id', ?)",
                (str(snap_id),),
            )
        return snap_id

    def latest_valid_snapshot_id(self) -> int | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM snapshots WHERE valid = 1 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return int(row["id"]) if row else None

    def current_snapshot_id(self) -> int | None:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'current_snapshot_id'").fetchone()
            if row:
                return int(row["value"])
        return self.latest_valid_snapshot_id()

    def load_snapshot(self, snapshot_id: int | None = None) -> tuple[int, Snapshot] | None:
        sid = snapshot_id or self.current_snapshot_id()
        if sid is None:
            return None
        with self._conn() as conn:
            meta = conn.execute("SELECT * FROM snapshots WHERE id = ? AND valid = 1", (sid,)).fetchone()
            if meta is None:
                return None
            accounts = conn.execute(
                "SELECT payload FROM snapshot_accounts WHERE snapshot_id = ?", (sid,)
            ).fetchone()
            roster = conn.execute(
                "SELECT payload FROM snapshot_roster WHERE snapshot_id = ?", (sid,)
            ).fetchone()
            acts = conn.execute(
                "SELECT payload FROM snapshot_activities WHERE snapshot_id = ?", (sid,)
            ).fetchone()
        snapshot = Snapshot(
            snapshot_date=date.fromisoformat(meta["snapshot_date"]),
            source=meta["source"],
            accounts=[Account.model_validate(x) for x in json.loads(accounts["payload"])],
            roster=[Seat.model_validate(x) for x in json.loads(roster["payload"])],
            activities=[Activity.model_validate(x) for x in json.loads(acts["payload"])],
        )
        return sid, snapshot

    def list_snapshots(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, snapshot_date, imported_at, source, account_count, roster_count, activity_count "
                "FROM snapshots WHERE valid = 1 ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_overrides(self, scenario_id: str) -> dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM scenario_overrides WHERE scenario_id = ?", (scenario_id,)
            ).fetchone()
        return json.loads(row["payload"]) if row else {}

    def save_overrides(self, scenario_id: str, payload: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scenario_overrides (scenario_id, payload, updated_at) VALUES (?, ?, ?)",
                (scenario_id, json.dumps(payload), _now()),
            )

    def clear_overrides(self, scenario_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM scenario_overrides WHERE scenario_id = ?", (scenario_id,))

    def save_run(
        self,
        snapshot_id: int,
        scenario_id: str,
        scenario_version: str,
        scenario_json: dict[str, Any],
        as_of: date,
        result: dict[str, Any],
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO runs (snapshot_id, scenario_id, scenario_version, scenario_json, as_of, created_at, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    scenario_id,
                    scenario_version,
                    json.dumps(scenario_json),
                    as_of.isoformat(),
                    _now(),
                    json.dumps(result),
                ),
            )
            return int(cur.lastrowid)

    def latest_run(self, snapshot_id: int, scenario_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM runs
                WHERE snapshot_id = ? AND scenario_id = ?
                ORDER BY id DESC LIMIT 1
                """,
                (snapshot_id, scenario_id),
            ).fetchone()
        return dict(row) if row else None

    def get_review(self, snapshot_id: int, account_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE snapshot_id = ? AND account_id = ?",
                (snapshot_id, account_id),
            ).fetchone()
        return dict(row) if row else None

    def list_reviews(self, snapshot_id: int) -> dict[str, dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE snapshot_id = ?", (snapshot_id,)
            ).fetchall()
        return {r["account_id"]: dict(r) for r in rows}

    def upsert_review(
        self,
        snapshot_id: int,
        account_id: str,
        decision: str,
        reason: str,
        reviewer: str,
        preview_owner_id: str | None = None,
        proposed_owner_id: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO reviews (
                  snapshot_id, account_id, decision, reason, reviewer, updated_at,
                  preview_owner_id, proposed_owner_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_id, account_id) DO UPDATE SET
                  decision = excluded.decision,
                  reason = excluded.reason,
                  reviewer = excluded.reviewer,
                  updated_at = excluded.updated_at,
                  preview_owner_id = excluded.preview_owner_id,
                  proposed_owner_id = excluded.proposed_owner_id
                """,
                (
                    snapshot_id,
                    account_id,
                    decision,
                    reason,
                    reviewer,
                    _now(),
                    preview_owner_id,
                    proposed_owner_id,
                ),
            )

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM release_batches WHERE batch_id = ?", (batch_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["result"] = json.loads(data["result_json"])
        return data

    def list_ledger(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM release_ledger ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def active_locks(self, as_of: date) -> dict[str, dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM release_ledger").fetchall()
        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            lock = row["lock_end_date"]
            if lock and date.fromisoformat(lock) >= as_of:
                out[row["account_id"]] = dict(row)
        return out

    def commit_release(
        self,
        batch_id: str,
        snapshot_id: int,
        scenario_id: str,
        rule_version: str,
        reviewer: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Idempotent weekly release. Caller must have already rechecked invariants."""
        existing = self.get_batch(batch_id)
        if existing:
            return existing["result"]
        now = _now()
        result = {
            "batch_id": batch_id,
            "status": "released",
            "released_at": now,
            "count": len(rows),
            "account_ids": [r["account_id"] for r in rows],
        }
        with self._conn() as conn:
            try:
                conn.execute("BEGIN")
                conn.execute(
                    """
                    INSERT INTO release_batches
                      (batch_id, snapshot_id, scenario_id, rule_version, reviewer, released_at, status, result_json)
                    VALUES (?, ?, ?, ?, ?, ?, 'released', ?)
                    """,
                    (
                        batch_id,
                        snapshot_id,
                        scenario_id,
                        rule_version,
                        reviewer,
                        now,
                        json.dumps(result),
                    ),
                )
                for row in rows:
                    conn.execute(
                        """
                        INSERT INTO release_ledger
                          (batch_id, account_id, prev_owner_id, new_owner_id, lock_end_date, reviewer, ts, rule_version)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            batch_id,
                            row["account_id"],
                            row.get("prev_owner_id"),
                            row.get("new_owner_id"),
                            row.get("lock_end_date"),
                            reviewer,
                            now,
                            rule_version,
                        ),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return result

    def ledger_count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM release_ledger").fetchone()
        return int(row["n"])

    def overwrite_snapshot(self, snapshot_id: int, snapshot: Snapshot) -> None:
        """Mutate an existing snapshot in place (tests and conflict simulation)."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE snapshot_accounts SET payload = ? WHERE snapshot_id = ?",
                (json.dumps([a.model_dump(mode="json") for a in snapshot.accounts]), snapshot_id),
            )
            conn.execute(
                "UPDATE snapshot_roster SET payload = ? WHERE snapshot_id = ?",
                (json.dumps([s.model_dump(mode="json") for s in snapshot.roster]), snapshot_id),
            )
            conn.execute(
                "UPDATE snapshot_activities SET payload = ? WHERE snapshot_id = ?",
                (json.dumps([a.model_dump(mode="json") for a in snapshot.activities]), snapshot_id),
            )
            conn.execute(
                """
                UPDATE snapshots SET account_count = ?, roster_count = ?, activity_count = ?
                WHERE id = ?
                """,
                (len(snapshot.accounts), len(snapshot.roster), len(snapshot.activities), snapshot_id),
            )
