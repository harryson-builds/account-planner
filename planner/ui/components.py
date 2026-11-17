from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from planner.config.schema import SEGMENTS, TIERS


def kpis(items: list[tuple[str, object, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, hint) in zip(cols, items):
        with col:
            st.metric(label, value, help=hint)


def matrix_table(matrix: dict[str, dict[str, dict[str, int]]]) -> pd.DataFrame:
    records = []
    for seg in SEGMENTS:
        row: dict[str, Any] = {"Segment": seg}
        for tier in TIERS:
            cell = matrix[seg][tier]
            row[f"Tier {tier}"] = (
                f"{cell['assignable']} assignable · {cell['policy_eligible']} eligible · "
                f"{cell['gate_pass']} pass · {cell['raw']} raw"
            )
        records.append(row)
    return pd.DataFrame(records)


def status_label(status: str) -> str:
    return {
        "PROPOSED": "Proposed",
        "RETAINED": "Retained",
        "BLOCKED": "Blocked",
        "UNALLOCATED": "Unallocated",
        "INVENTORY": "Inventory",
        "OVER_CAP": "Over cap",
        "BELOW_VIABLE": "Below viable",
        "DISCREPANCY": "Stale segment",
    }.get(status, status)


def decisions_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    keep = [
        c
        for c in [
            "account_id",
            "display_name",
            "derived_segment",
            "tier",
            "territory",
            "status",
            "reason_code",
            "proposed_owner_id",
            "owner_id",
            "fit_score",
            "review_decision",
            "explanation",
        ]
        if c in df.columns
    ]
    return df[keep]


def books_frame(books: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for b in books:
        mix = b.get("tier_mix") or {}
        rows.append(
            {
                "rep_id": b.get("rep_id"),
                "segment": b.get("segment"),
                "territory": b.get("territory"),
                "book": b.get("book_count"),
                "cap": b.get("cap"),
                "fill": b.get("fill_ratio"),
                "A": mix.get("A", 0),
                "B": mix.get("B", 0),
                "C": mix.get("C", 0),
                "D": mix.get("D", 0),
                "over_cap": b.get("over_cap"),
                "below_viable": b.get("below_viable"),
                "ramp": b.get("ramp_factor"),
            }
        )
    return pd.DataFrame(rows)
