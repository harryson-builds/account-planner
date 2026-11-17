# Build this inside a company-managed environment

This file is the implementation guide for taking the **portfolio planner** and running it on **authorized company inputs**. It does not contain employer account lists, employee names, internal caps, or CRM credentials. Those stay in a company-managed checkout (`internal/`, gitignored).

The product you run locally today is CRM-agnostic. Internally you supply CSVs from an approved export, point scenario YAML at your FY plan, and keep HubSpot/Salesforce **writes** on a separate, already-approved path. This app's release ledger is **local SQLite**, not a CRM push.

## What to copy

Into a **new private company repo** (not a fork of a personal GitHub that still has take-home history):

```
planner/
pyproject.toml
.github/workflows/test.yml
.streamlit/config.toml
.gitignore
README.md
planner/docs/
```

Do **not** copy `web/`, `engine/`, `deliverable/`, `data/`, `.env.example` HubSpot tokens, or HTML workbooks. Those are a different project.

## Environment

- Python 3.11+, `pip install -e ".[dev]"`, `python3 -m pytest planner/tests`, `python3 -m planner`
- Binds `127.0.0.1` only. Do not expose to the internet.
- Single-operator trust model: whoever can open the app can import CSVs and write the local ledger. Put it on a laptop or a locked-down internal VM, not a shared public URL.
- Store authorized extracts in `internal/snapshots/YYYY-MM-DD/` (gitignored). Never commit them.

## Data contract (map your CRM export here)

Fill this table in the company repo. Use your RevOps-owned property names; do not invent live writes.

| Planner CSV field | Typical CRM export | Company property (fill internally) | Notes |
| --- | --- | --- | --- |
| account_id | Record ID | | Stable. Do not use display name. |
| display_name | Company name | | Fictional in demo; real names stay in `internal/`. |
| employee_count | Number of employees / enrichment | | Drives Commercial 0–199, MM 200–999, ENT 1,000+. |
| crm_segment | Segment picklist | | Compared to derived segment; flag MM→ENT. |
| country | Country/region | | Missing → `MISSING_GEOGRAPHY`. |
| territory | Territory / overlay | | Must match roster territories. |
| industry | Industry | | Reviewable if blank. |
| tier | A/B/C/D | FitScore or equivalent band | C/D stay in inventory, not named books. |
| qualification_gate | PASS/FAIL/HOLD | Your gate output | Empty → HOLD. |
| fit_score | 0–100 | | Sort only. |
| owner_id | Company owner / AE | Map to `REP-*` via roster | |
| sdr_id | SDR overlay | | MM requires territory SDR coverage. |
| parent_account_id | Parent company ID | | Ambiguous child routing → Exceptions. |
| is_customer | Lifecycle / customer flag | | Protected; excluded from new-logo ARR. |
| has_open_opportunity | Open deal join | | Protected; excluded from new-logo ARR. |
| lock_end_date | Named-account lock | | Unexpired = protected. |

Roster comes from the FY hiring plan (seat, segment, territory, start month, ramp, cap override), not from a random owner list. Activities come from engagement history (calls, emails, meetings) with timestamps.

Templates: `planner/templates/`. Dictionary: `planner/docs/data_dictionary.md`.

## Scenario YAML you must own internally

Copy `planner/config/scenarios/baseline.yaml` to `internal/scenarios/fy27.yaml` (or keep overrides in the UI, which land in gitignored SQLite). Set:

1. **Caps** from the FY named-account plan (ENT / MM / Commercial).
2. **Eligibility** — default PASS + A/B + ENT/MM. Turn on Commercial only when you want to compare book math.
3. **Routing** — ENT named AE; MM AE + SDR coverage.
4. **Viable-book minimums** so empty seats do not count as staffed.
5. **Lock days** (sample 90).
6. **Hiring** via roster `start_date` / `end_date`. Use `hiring_shift_months` only for timing scenarios.
7. **ARR assumptions** from finance/RevOps, not from this demo. Recalibrate worked rate from activity before a hiring decision. The demo's own 90-day touch data implies a **much lower** monthly first-worked rate than the 28% ARR input — Overview will warn when they drift.

Keep historical bookings, CRM pipeline, and modeled ARR as **three labeled numbers**. Do not multiply modeled ARR by quota attainment.

## Operating loop (same as the demo)

1. Export authorized CSVs → CRM Import (validate; last valid snapshot kept on failure).
2. Overview: eligible vs assignable vs uncovered territories.
3. Assignments: books, over-cap retained, field readiness.
4. Exceptions: geo, future seats, SDR gaps, parent-child, stale segment.
5. Decisions: approve / hold / reject (filterable table).
6. Weekly Releases: one transaction, 90-day lock, local audit. Same batch id + same snapshot is idempotent. New snapshot needs a new batch id.
7. Export assignment/exception CSVs. Load owners into CRM through **your approved** import/automation. This app does not write HubSpot.

## What this planner will not do for you

- Live CRM authentication or company-record updates.
- FitScore / enrichment computation (it **consumes** a gate and tier).
- A 12,000-row interactive card per account (Decisions is a table; still expect slower FY27 simulation as n grows — filter to PASS A/B before import if needed).
- A substitute for finance bookings. Modeled ARR is a funnel on assigned new-logo accounts.

## Pressure checks before an FY readout

- [ ] Employee bands 199/200/999/1000 match the company definition.
- [ ] Stale CRM segment count is reviewed with the data owner.
- [ ] Over-cap retained books are a cap/split decision, not a hiring request.
- [ ] EAST-style "eligible but unstaffed" territories have a hire month or an explicit "do not cover" decision.
- [ ] Activity-implied worked rate vs ARR worked rate is documented.
- [ ] `pytest planner/tests` is green on the company clone.
- [ ] No internal CSV is in git status.
