# Scenario model reference

Every saved run stores `scenario_id`, `scenario_version`, and the merged YAML (including UI overrides). Source CSVs are not rewritten. Scenario runs never write the release ledger.

Currency is **USD**. ARR is **modeled new-logo ARR** (scenario estimate). Do not read it as historical bookings or CRM pipeline.

## Segments

| Segment | Employees |
| --- | --- |
| Commercial | 0–199 |
| Mid-Market | 200–999 |
| Enterprise | 1,000+ |

Missing headcount → `Unknown` (review, not policy-eligible). CRM segment is kept and compared; `Mid-Market → Enterprise` is an explicit discrepancy.

## Qualification vs assignment

| Measure | Definition |
| --- | --- |
| Raw inventory | Every account in the snapshot |
| Gate pass | `qualification_gate` in the scenario list (default `PASS`) |
| Policy-eligible | Gate pass, tier A/B, Enterprise or Mid-Market. Commercial only if `include_commercial` |
| Currently assignable | Policy-eligible and not blocked by geo, staff, SDR, parent routing, or a full book |
| Proposed | New named-owner recommendation this cut |
| Retained | Protected ownership (customer, open opportunity, unexpired lock) counted toward cap |
| Released | Local ledger row with an active lock |

Enterprise routes to a named AE. Mid-Market requires an AE plus active SDR coverage in the territory. Future seats are not named owners until `start_date`.

## Allocation heuristic

1. Retain protected accounts on a still-valid named AE.
2. Sort remaining eligible accounts by tier (A→D), then fit score descending (`null` last), then `account_id` ascending.
3. Assign to the eligible active AE in the same segment and territory with the **lowest fill ratio** (`book / cap`), then lowest `rep_id`.
4. Stop when the book is full. Leftovers are `UNALLOCATED` / `BOOK_FULL`.

## Activity calibration

A worked account has at least `min_touches` of `qualifying_types` inside `lookback_days`. Demo results use **snapshot/proposed ownership as a proxy** (no historical ownership timeline). Cap scenarios share the default worked-account rate unless the YAML documents a calibration.

## ARR bridge

For each fiscal month, unique assigned **new-logo** accounts (exclude customers and open opportunities) keep a remaining mass starting at `1.0`.

```
expected first-worked = remaining × monthly worked-account rate × owner ramp
remaining := remaining − expected first-worked
opportunities = first-worked × opportunity rate
wins = opportunities × win rate
close month = first-worked month + close lag
FY ARR = wins closing in FY × average new-logo ARR per win
```

Fractional counts are expected. Owner changes do not reset remaining mass. Closes after FY27 are reported separately. There is no quota-attainment multiplier.

Levers (conservative / base / upside) live under `arr` in the scenario YAML: worked rate, opportunity rate, win rate, average ARR per win, close lag. Sensitivity changes one lever at a time versus base.

## Shipped scenarios

| ID | What it changes |
| --- | --- |
| `baseline` | Sample caps ENT 14 / MM 18 / COM 30, roster start dates as loaded |
| `tight_books` | Lower caps ENT 9 / MM 12 / COM 20; same worked rate |
| `delayed_hires` | Baseline caps; FY27 start dates shift +2 months |

Hiring plan is the roster (`start_date`, `end_date`, `eligibility_status`). `hiring_shift_months` delays seats that start on or after FY27 start.
