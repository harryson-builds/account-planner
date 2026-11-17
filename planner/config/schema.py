"""Versioned scenario configuration."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from planner.paths import SCENARIO_DIR

SEGMENTS = ("Commercial", "Mid-Market", "Enterprise")
TIERS = ("A", "B", "C", "D")
TERRITORIES = ("WEST", "CENTRAL", "EAST")


class Band(BaseModel):
    min: int
    max: int | None = None


class Eligibility(BaseModel):
    qualification_gates: list[str] = Field(default_factory=lambda: ["PASS"])
    tiers: list[str] = Field(default_factory=lambda: ["A", "B"])
    segments: list[str] = Field(default_factory=lambda: ["Enterprise", "Mid-Market"])
    include_commercial: bool = False


class RouteRule(BaseModel):
    requires_ae: bool = True
    requires_sdr: bool = False


class Fiscal(BaseModel):
    label: str = "FY27"
    start: date
    end: date


class ActivityRules(BaseModel):
    qualifying_types: list[str] = Field(default_factory=lambda: ["call", "email", "meeting"])
    min_touches: int = 1
    lookback_days: int = 90


class VariantTriple(BaseModel):
    conservative: float
    base: float
    upside: float


class ArrAssumptions(BaseModel):
    currency: str = "USD"
    unit: str = "new-logo ARR"
    worked_rate: VariantTriple
    opportunity_rate: VariantTriple
    win_rate: VariantTriple
    avg_arr_per_win: VariantTriple
    close_lag_months: VariantTriple
    new_logo_arr_target: dict[str, float]


class ScenarioConfig(BaseModel):
    id: str
    version: str
    name: str
    description: str = ""
    fiscal: Fiscal
    segments: dict[str, Band]
    eligibility: Eligibility
    routing: dict[str, RouteRule]
    caps: dict[str, int]
    viable_book_minimums: dict[str, int]
    lock_days: int = 90
    hiring_shift_months: int = 0
    activity: ActivityRules
    ramp: dict[str, list[float]]
    arr: ArrAssumptions

    def band_for(self, employees: int | None) -> str:
        if employees is None:
            return "Unknown"
        for name, band in self.segments.items():
            hi = band.max
            if employees >= band.min and (hi is None or employees <= hi):
                return name
        return "Unknown"

    def cap_for(self, segment: str) -> int:
        return int(self.caps[segment])

    def viable_min_for(self, segment: str) -> int:
        return int(self.viable_book_minimums[segment])

    def route_for(self, segment: str) -> RouteRule:
        return self.routing[segment]

    def policy_segments(self) -> set[str]:
        segs = set(self.eligibility.segments)
        if self.eligibility.include_commercial:
            segs.add("Commercial")
        return segs

    def ramp_curve(self, profile: str) -> list[float]:
        if profile in self.ramp:
            return self.ramp[profile]
        return self.ramp.get("standard", [1.0])


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f)


def list_scenarios() -> list[ScenarioConfig]:
    items = []
    for path in sorted(SCENARIO_DIR.glob("*.yaml")):
        items.append(ScenarioConfig.model_validate(_read_yaml(path)))
    return items


def load_scenario(scenario_id: str) -> ScenarioConfig:
    if not scenario_id or any(ch in scenario_id for ch in ("/", "\\", "..")):
        raise FileNotFoundError(f"Unknown scenario: {scenario_id}")
    root = SCENARIO_DIR.resolve()
    path = (SCENARIO_DIR / f"{scenario_id}.yaml").resolve()
    if path.parent != root or not path.exists():
        raise FileNotFoundError(f"Unknown scenario: {scenario_id}")
    return ScenarioConfig.model_validate(_read_yaml(path))


def merge_overrides(base: ScenarioConfig, overrides: dict[str, Any] | None) -> ScenarioConfig:
    """Apply UI/session overrides without mutating the YAML on disk."""
    if not overrides:
        return base
    data = base.model_dump()
    _deep_update(data, overrides)
    return ScenarioConfig.model_validate(data)


def _deep_update(target: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = deepcopy(value)
