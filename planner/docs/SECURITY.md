# Security notes

Intended use: **single operator**, process bound to `127.0.0.1`, authorized CSVs, local SQLite.

## Trust boundary

Anyone who can open the app can import snapshots and write the local release ledger. There is no login. Do not publish a public URL.

## Controls in this release

- Scenario YAML paths cannot leave `planner/config/scenarios/`.
- CSV import validates headers, types, enums, duplicate IDs, and foreign keys. Structural failure keeps the last valid snapshot and does not write the ledger.
- Row cap: 100,000 per file. Display names capped at 200 characters.
- SQLite uses parameterized queries.
- Assignment/exception exports neutralize spreadsheet formulas (`=` `+` `-` `@`) and wrap IDs.
- Release rechecks ownership, staff, capacity, and active locks in one transaction. Conflict → pending, ledger unchanged.
- Same `batch_id` is idempotent only for the same snapshot and scenario; reuse after a new import is rejected.
- An account with an unexpired ledger lock cannot be released again.
- Streamlit pages render CSV fields as table cells, not raw HTML.

## Out of scope

- Multi-user authorization
- CRM credential storage
- Server-side CRM writes
