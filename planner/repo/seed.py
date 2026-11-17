"""Load the fictional demo snapshot when the local database is empty."""

from __future__ import annotations

from datetime import date

import yaml

from planner.paths import DEMO_DIR
from planner.repo.db import Database
from planner.repo.validator import validate_csv_bundle


def demo_snapshot_date() -> date:
    meta = yaml.safe_load((DEMO_DIR / "snapshot.yaml").read_text())
    return date.fromisoformat(str(meta["snapshot_date"]))


def load_demo(db: Database) -> int:
    result = validate_csv_bundle(
        DEMO_DIR / "accounts.csv",
        DEMO_DIR / "roster.csv",
        DEMO_DIR / "activities.csv",
        demo_snapshot_date(),
        source="demo",
    )
    if not result.ok or result.snapshot is None:
        msgs = "; ".join(f"{e.file}:{e.row} {e.message}" for e in result.errors[:8])
        raise RuntimeError(f"demo seed failed validation: {msgs}")
    return db.save_snapshot(result.snapshot)


def ensure_seeded(db: Database) -> int:
    existing = db.latest_valid_snapshot_id()
    if existing is not None:
        return existing
    return load_demo(db)
