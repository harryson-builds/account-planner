# Walkthrough

Fictional snapshot date: **2026-02-01**. Commands from a clean clone.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python3 -m pytest planner/tests
python3 -m planner
```

The app binds to `127.0.0.1:8517`. CRM credentials are not required.

## Account: Helio Analytics (`ACC-0001`)

| Step | Result (fictional) |
| --- | --- |
| Employees | 1,200 |
| CRM segment | Mid-Market |
| Derived segment | Enterprise (`Mid-Market → Enterprise`) |
| Gate / tier | PASS / A / fit 88 |
| Policy-eligible | yes |
| Blockers | none (country, territory, ENT AE path exist) |
| Proposed owner | `REP-E02` (WEST Enterprise). `REP-E01` is already over cap on retained customers/opps/locks |
| Review | approve |
| Release | batch `WALK-1` writes the local ledger, 90-day lock from snapshot date, previous owner `none` → `REP-E02` |

Reproducing without the UI:

```python
from pathlib import Path
from planner.service import PlannerService

svc = PlannerService(Path("var/walkthrough.sqlite"))
row = next(r for r in svc.assignment("baseline")["rows"] if r["account_id"] == "ACC-0001")
assert row["status"] == "PROPOSED" and row["proposed_owner_id"] == "REP-E02"
svc.upsert_review("ACC-0001", "approve", "named ENT book", "walkthrough")
print(svc.release("baseline", "WALK-1", "walkthrough")["status"])
```

Expected: `released`. A second call with `WALK-1` returns `idempotent` and does not duplicate ledger rows.

## FY27 hiring → ARR (baseline vs delayed hires)

Roster: EAST Enterprise AE `REP-E05` starts **2026-03-01**; EAST Mid-Market SDR starts **2026-08-01**.

| | Baseline | Delayed hires (+2 months) | Tighter books |
| --- | --- | --- | --- |
| Policy-eligible | 84 | 84 | 84 |
| Currently assignable (Feb) | 40 | 40 | 37 |
| Viable AE books (Feb) | 5 | 5 | 5 |
| Base modeled new-logo ARR (USD) | 53,218 | 50,369 | 51,287 |
| FY27 target | 70,000 | 70,000 | 70,000 |
| Gap to target | −16,782 | −19,631 | −18,713 |

Pulling the EAST AE start from March to May (delayed hires) lowers modeled FY ARR because ramp and first-worked cohorts move later; some closes fall outside FY27. Tightening caps does **not** close the gap: EAST is still blocked by staffing/SDR, and WEST/CENTRAL lose a few proposed accounts. The conversion levers (worked rate, win rate, lag) move ARR more than cap cuts on this snapshot.

Month 0 (Feb 2026) capacity, baseline: 9 staffed AE seats, 5 viable books, 25 retained accounts, EAST flagged `shortage_eligible_accounts` (no named ENT AE, no MM SDR).

## Material assumptions

- Worked-account rate is a scenario input. Activity calibration is a **proxy vs snapshot ownership** (18 of 67 assigned accounts touched in 90 days; untouched share 73%).
- Opportunity rate, win rate, average ARR/win, and close lag are cohort conversion assumptions, not historical bookings.
- Sample outputs are fictional. Modeled ARR is a scenario estimate.

## Checks that could not run

- No live CRM, HubSpot, or Sumble connection (by design).
- No production identity or published hosting in this walkthrough.
- GitHub Actions is defined; it runs only after the workflow file is on the default branch of a GitHub remote.
- Do not push this Cursor branch’s git history to a personal GitHub (take-home / workbook files still live in `web/`, `engine/`, `deliverable/`). Pack a clean tree with `python3 planner/scripts/pack_github.py`.
- Recalibrate ARR worked rate from CRM activity before a hiring readout. The demo activity series implies ~10% monthly first-worked vs a 28% ARR input; Overview warns when they drift.
