# Data dictionary

Fictional demo identifiers use the prefixes `ACC-`, `SEAT-`, `REP-`, `ACT-`. Nulls are empty cells. Dates are ISO-8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`). Booleans are `true` / `false` (also `1` / `0` / `yes` / `no`).

A structurally valid import can still contain **review exceptions** (missing country, missing headcount, blank owner). Those rows load. Duplicate IDs, unknown enums, broken foreign keys, and unparseable types **reject the file** and keep the last valid snapshot.

## Snapshot

| Field | Type | Notes |
| --- | --- | --- |
| snapshot_date | date | Required. Planning as-of date. Demo uses `2026-02-01`. |

## Accounts (`templates/accounts.csv`)

| Field | Type | Required | Allowed / units | Null |
| --- | --- | --- | --- | --- |
| account_id | string | yes | Stable ID, unique in the file | reject |
| display_name | string | yes | Fictional display name | reject |
| employee_count | integer | no | Headcount. Drives segment bands | empty → Unknown segment, review |
| crm_segment | string | no | Commercial / Mid-Market / Enterprise | compared to derived segment |
| country | string | no | ISO-style or name | empty → `MISSING_GEOGRAPHY` if eligible |
| territory | string | no | Must match a roster territory to route | empty → `MISSING_GEOGRAPHY` |
| industry | string | no | Free text | empty is reviewable, not a load error |
| tier | enum | no | `A`, `B`, `C`, `D` | empty → not policy-eligible |
| qualification_gate | enum | no | `PASS`, `FAIL`, `HOLD` | empty → `HOLD` |
| fit_score | number | no | 0–100, used as allocation sort | empty sorts last |
| intent_score | number | no | 0–100, display only | |
| owner_id | string | no | `REP-*` of a staffed AE | empty if unassigned |
| sdr_id | string | no | `REP-*` of an SDR | |
| parent_account_id | string | no | Must be an `account_id` in the same file | empty OK; unknown ID rejects |
| is_customer | bool | no | Protected ownership | default false |
| has_open_opportunity | bool | no | Protected; excluded from new-logo ARR | default false |
| lock_end_date | date | no | Unexpired lock is protected | empty = no lock |

## Roster (`templates/roster.csv`)

| Field | Type | Required | Allowed / units | Null |
| --- | --- | --- | --- | --- |
| seat_id | string | yes | Unique | reject duplicates |
| rep_id | string | no | Named person when staffed | empty = vacant seat, not a named owner |
| role | enum | yes | `AE`, `SDR` | reject |
| segment | enum | yes | Commercial / Mid-Market / Enterprise | reject |
| territory | string | yes | Planning territory | reject if empty |
| start_date | date | yes | Seat start (hire / ramp clock) | reject |
| end_date | date | no | Departure; open if empty | |
| ramp_profile | string | yes | Key in scenario `ramp` (`standard`, `experienced`, `ramp_fast`) | |
| eligibility_status | enum | yes | `active`, `future`, `departed` | future seats are not named owners |
| cap_override | integer | no | Accounts; else scenario cap for the segment | |

## Activities (`templates/activities.csv`)

| Field | Type | Required | Allowed / units | Null |
| --- | --- | --- | --- | --- |
| activity_id | string | yes | Unique | reject duplicates |
| account_id | string | yes | Must exist in the accounts file | reject |
| timestamp | datetime | yes | ISO-8601 | reject |
| activity_type | string | yes | Qualifying types are scenario-config (`call`, `email`, `meeting` by default) | |
| rep_id | string | no | Actor | |
| outcome | string | no | Free text | |

## Scenario config

See [scenario_model.md](scenario_model.md) for employee bands, eligibility, caps, lock duration, activity rules, ramp, and ARR assumptions. Scenario YAML is versioned (`id` + `version`) and stored with every saved run.
