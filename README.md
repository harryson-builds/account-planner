# Account Assignment & Capacity Planner

A CRM-agnostic RevOps planner for turning an annual hiring plan into territory-level account books, reviewing exceptions, and estimating the **new-logo ARR** each scenario can support.

This repository’s runnable product is the Python app under `planner/`. It uses **fictional** accounts, roster, and activity. Sample outputs below are labeled fictional. Modeled ARR is a **scenario estimate**, not historical bookings or CRM pipeline.

---

## Executive brief

**Planning decision.** A qualification gate protects book quality. Assignment rules enforce ownership and capacity. Scenario modeling shows where a hiring or allocation change would move coverage and revenue potential.

Figures are from the shipped demo snapshot (`2026-02-01`, 101 accounts, three territories). They are not a customer book.

### 1. How many accounts qualify, how many can be staffed, and where is eligible demand uncovered?

| Measure | Fictional count | Denominator |
| --- | --- | --- |
| Raw inventory | 101 | Snapshot accounts |
| Gate pass (`PASS`) | 97 | Raw inventory |
| Policy-eligible (PASS, A/B, ENT/MM) | 84 | Named-account policy |
| Currently assignable | 40 | Eligible and not blocked |
| Proposed new named owners | 40 | Assignable that received a slot |
| Retained (customer / open opp / lock) | 25 | Protected ownership, counts toward cap |
| Blocked eligible demand | 20 | Geo, future seat, SDR gap, parent routing, missing headcount |

**Uncovered eligible demand (fictional):** EAST Enterprise **8** (no active named AE until March), EAST Mid-Market **9** (SDR coverage starts August), WEST Mid-Market **1** (missing country), WEST Enterprise **1** (parent-child routing). Commercial and C/D remain in the inventory matrix so they are not dumped into named-account lists.

### 2. Given current staffed reps and FY27 hiring, which seats get a viable book?

February 2026 (month 0), baseline caps (ENT 14 / MM 18): **9** staffed AE seats, **5** viable books, **0** FY27 hires started yet. Future seats are listed and are **not** named owners.

| Territory | What the demo shows |
| --- | --- |
| WEST | `REP-E01` is **over cap** (16 retained vs cap 14). New ENT names go to `REP-E02`. Need a higher cap, a split, or a later lock — not more hiring in WEST ENT. |
| CENTRAL | Surplus capacity after retained + proposals. The departing MM AE (`REP-M06`, end 2026-04-30) is the timing risk. |
| EAST | Eligible accounts exist; the AE seat starts March and the MM SDR starts August. Until then, usable accounts go uncovered. Pulling those starts later (`delayed_hires`) does not create February coverage. |

Tighter books (ENT 9 / MM 12) drop assignable from 40 to 37 and leave 3 unallocated. They do **not** staff EAST. If the problem is missing owners, change hiring timing or SDR coverage; if the problem is over-cap retained demand, change the cap.

### 3. Would tighter books improve coverage while preserving pipeline and new-logo ARR?

Activity calibration (90-day lookback, qualifying `call` / `email` / `meeting`, snapshot ownership **proxy**): **18 of 67** assigned accounts worked; **untouched share 73%**. Median touches are in the Assumptions view.

Cap scenarios **share the same default worked-account rate** (base 28% per month) because this demo does not have a documented historical calibration that would justify a different rate for smaller books. Tighter caps slightly reduce proposed accounts and modeled ARR (see table). They do not, on this snapshot, raise the worked share enough to close the ARR gap. The assigned-but-unworked population is flagged on Assumptions (`ACC-0013` Maple Circuit is the seeded activity gap: lock + owner, only a non-qualifying `note`).

### 4. What is the modeled ARR gap, what drives it, and which decision would change it?

| Scenario | Caps ENT/MM | Hire shift | Base modeled new-logo ARR (USD) | FY27 target | Gap |
| --- | --- | --- | --- | --- | --- |
| Baseline | 14 / 18 | 0 | 53,218 | 70,000 | −16,782 |
| Tighter books | 9 / 12 | 0 | 51,287 | 70,000 | −18,713 |
| Delayed FY27 hires | 14 / 18 | +2 months | 50,369 | 70,000 | −19,631 |

Conservative / base / upside on baseline: **14,906 / 53,218 / 143,884**. Upside (higher worked rate, win rate, shorter lag) is the only variant that clears the $70k target on this seed. Closes that fall after Jan 2027 are reported separately (~$2.3k in baseline).

**Worked example (fictional).** Helio Analytics (`ACC-0001`) is CRM Mid-Market with 1,200 employees → Enterprise, PASS A. It is proposed to `REP-E02` because `REP-E01` is over cap. That named owner puts Helio in the new-logo remaining pool. Each month: remaining × 0.28 worked rate × AE ramp → expected first-worked → × opportunity rate × win rate → lag 2 months → × $24,000 ARR/win. A **March EAST AE** adds EAST accounts to that pool two months earlier than a **May** start (`delayed_hires`), which is why delayed hiring costs ~$2.8k of modeled FY ARR. Cutting WEST/CENTRAL caps removes a few proposed names and costs ~$1.9k; it does not unlock EAST.

Drivers, inspectable on Assumptions: **account supply** (eligible vs blocked), **staffing/ramp** (hire month, departures), **conversion** (worked / opp / win rates), **deal size** (average ARR per win). The model does not multiply by quota attainment. Historical bookings and CRM pipeline are not inputs.

---

## Setup

Python 3.11+. From a clean clone:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python3 -m pytest planner/tests
python3 -m planner
```

The app listens on **127.0.0.1:8517**. First launch loads the fictional demo into gitignored `var/planner.sqlite`.

CSV templates: [`planner/templates/`](planner/templates/). Data dictionary: [`planner/docs/data_dictionary.md`](planner/docs/data_dictionary.md). Model math: [`planner/docs/scenario_model.md`](planner/docs/scenario_model.md). Seeded walkthrough: [`planner/docs/walkthrough.md`](planner/docs/walkthrough.md).

Internal inputs belong in gitignored `internal/` or `var/` — not in this checkout. Do not commit SQLite files, exports, or credentials.

### This repository

This is the planner-only tree (no take-home workbook). Keep it **private**. Invite your work GitHub user as a collaborator rather than making it public.

Authorized company CSVs belong in gitignored `internal/` or `var/`. See [planner/docs/COMPANY_BRINGUP.md](planner/docs/COMPANY_BRINGUP.md) and [planner/docs/SECURITY.md](planner/docs/SECURITY.md).

### Views

| Page | Use |
| --- | --- |
| Overview | Four planning questions, KPIs, segment × tier matrix |
| Assignments | Books by rep, field readiness, proposed vs retained |
| Decisions | Approve / hold / reject with reasons |
| Weekly Releases | Transactional batch, conflicts, local audit ledger |
| Exceptions | Blocked rows and over-cap books |
| Assumptions | Caps, hiring shift, ARR levers, sensitivity |
| CRM Import | Read-only CSV validate/load; last valid snapshot on failure |

### Architecture

Streamlit pages call pure domain functions (segment, qualify, allocate, release, capacity, activity, ARR) through SQLite repositories. Same snapshot + config → same proposals and forecasts. GitHub Actions runs `pytest planner/tests`.
