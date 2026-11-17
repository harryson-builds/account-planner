"""Generate fictional demo CSVs. Run from repo root: python -m planner.demo.build_seed"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent

ACCOUNT_FIELDS = [
    "account_id",
    "display_name",
    "employee_count",
    "crm_segment",
    "country",
    "territory",
    "industry",
    "tier",
    "qualification_gate",
    "fit_score",
    "intent_score",
    "owner_id",
    "sdr_id",
    "parent_account_id",
    "is_customer",
    "has_open_opportunity",
    "lock_end_date",
]

ROSTER_FIELDS = [
    "seat_id",
    "rep_id",
    "role",
    "segment",
    "territory",
    "start_date",
    "end_date",
    "ramp_profile",
    "eligibility_status",
    "cap_override",
]

ACTIVITY_FIELDS = [
    "activity_id",
    "account_id",
    "timestamp",
    "activity_type",
    "rep_id",
    "outcome",
]

NAMES = [
    "Helio Analytics",
    "Pebble Logistics",
    "Amberline Freight",
    "Northwind Clinics",
    "Cedar Stack",
    "Lumen Harbor Software",
    "Brightpine Health",
    "Quarry Lane Robotics",
    "Solstice Payroll",
    "Nimbus Ledger",
    "Ironclad Payments",
    "Maple Circuit",
    "Harborline Insurance",
    "Redwood Fleet",
    "Atlas Loom",
    "Silverpine Analytics",
    "Cove & Grain",
    "Westridge Bio",
    "Kite & Cable",
    "Orchard Grid",
    "Bluebell Capital",
    "Fathom Retail OS",
    "Granite Motive",
    "Sable Cloud",
    "Pinecrest Legal",
    "Driftwood Energy",
    "Copperline HR",
    "Vesper Markets",
    "Fieldstone Med",
    "Alder & Co Commerce",
    "Marrow Tech",
    "Glasswing Security",
    "Northfork Payments",
    "Cinder Analytics",
    "Boreal Freight",
    "Larkspur Health",
    "Tidepool Software",
    "Emberline CRM",
    "Holloway Industrial",
    "Summit Birch",
    "Calico Banks",
    "Windfall Ops",
    "Peregrine Labs",
    "Oakline Media",
    "Brinewater Shipping",
    "Hearthstone Foods",
    "Kestrel Networks",
    "Mosaic Payroll",
    "Juniper Claims",
    "Rivertown Clinics",
    "Ashlar Construction OS",
    "Nightingale Staffing",
    "Polaris Warehouse",
    "Crescent Dental Group",
    "Lowland Semiconductors",
    "Thistle Finance",
    "Gilded Rail",
    "Umber Systems",
    "Shoal Creek Software",
    "Barrow & Finch",
    "Ivy League Apparel Co",
    "Flatiron Genomics",
    "Wren Logistics",
    "Saffron Hotels",
    "Cobalt Mutual",
    "Dune & Drift",
    "Harborwell Pharma",
    "Tinderbox Games",
    "Elm Street Payments",
    "Quartzline Energy",
    "Paperkite Education",
    "Stormglass Marine",
    "Fennel Health",
    "Ridgeback Auto",
    "Candlewick Media",
    "Yarrow Biotech",
    "Spire & Lantern",
    "Mudlark Commerce",
    "Beacon Hill Tools",
    "Cinderella Freight",
    "Northlight Semicon",
    "Plover Insurance",
    "Sandbar Credit",
    "Trestle Analytics",
    "Willowbend Hospitals",
    "Gannet Cloud",
    "Redcliff Mining OS",
    "Softwood ERP",
    "Anvil Public Safety",
    "Mirth & Co",
    "Bluehorn Dairy",
    "Cartwright Legal",
    "Dewpoint Climate",
    "Evergreen Tolling",
    "Falconet Security",
    "Gingerbread POS",
    "Halcyon Banks",
    "Inkcap Software",
    "Jasper Transit",
    "Keelhaul Shipping",
]


def _acct(
    n: int,
    name: str,
    employees: int | None,
    crm: str,
    country: str | None,
    territory: str | None,
    industry: str,
    tier: str,
    gate: str,
    fit: int | None,
    intent: int | None,
    owner: str,
    sdr: str,
    parent: str,
    customer: str,
    opp: str,
    lock: str,
) -> dict[str, str]:
    return {
        "account_id": f"ACC-{n:04d}",
        "display_name": name,
        "employee_count": "" if employees is None else str(employees),
        "crm_segment": crm,
        "country": country or "",
        "territory": territory or "",
        "industry": industry,
        "tier": tier,
        "qualification_gate": gate,
        "fit_score": "" if fit is None else str(fit),
        "intent_score": "" if intent is None else str(intent),
        "owner_id": owner,
        "sdr_id": sdr,
        "parent_account_id": parent,
        "is_customer": customer,
        "has_open_opportunity": opp,
        "lock_end_date": lock,
    }


def build_accounts() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    name_i = 0

    def next_name() -> str:
        nonlocal name_i
        name = NAMES[name_i % len(NAMES)]
        name_i += 1
        return name

    # ACC-0001 Helio Analytics: stale CRM MM, 1200 employees = ENT, PASS A, WEST, unowned → walkthrough
    rows.append(
        _acct(
            1,
            "Helio Analytics",
            1200,
            "Mid-Market",
            "US",
            "WEST",
            "Software",
            "A",
            "PASS",
            88,
            72,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )
    name_i = 1
    # ACC-0002 Pebble Logistics: MM missing country
    rows.append(
        _acct(
            2,
            "Pebble Logistics",
            450,
            "Mid-Market",
            None,
            "WEST",
            "Logistics",
            "A",
            "PASS",
            81,
            60,
            "",
            "REP-S01",
            "",
            "false",
            "false",
            "",
        )
    )
    # ACC-0003 Northwind Clinics: ENT EAST staffing gap
    rows.append(
        _acct(
            3,
            "Northwind Clinics",
            2100,
            "Enterprise",
            "US",
            "EAST",
            "Healthcare",
            "A",
            "PASS",
            91,
            55,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )
    # ACC-0004 Amberline Freight: MM EAST SDR gap
    rows.append(
        _acct(
            4,
            "Amberline Freight",
            320,
            "Mid-Market",
            "US",
            "EAST",
            "Logistics",
            "A",
            "PASS",
            77,
            48,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )
    # ACC-0005 parent customer WEST ENT on over-cap REP-E01
    rows.append(
        _acct(
            5,
            "Cedar Stack Holdings",
            5400,
            "Enterprise",
            "US",
            "WEST",
            "Software",
            "A",
            "PASS",
            70,
            40,
            "REP-E01",
            "",
            "",
            "true",
            "false",
            "2026-08-01",
        )
    )
    # ACC-0006 child of 0005 — ambiguous parent routing
    rows.append(
        _acct(
            6,
            "Cedar Stack Payments",
            1800,
            "Enterprise",
            "US",
            "WEST",
            "Software",
            "A",
            "PASS",
            84,
            66,
            "",
            "",
            "ACC-0005",
            "false",
            "false",
            "",
        )
    )
    # ACC-0007 unexpired lock
    rows.append(
        _acct(
            7,
            "Lumen Harbor Software",
            1600,
            "Enterprise",
            "US",
            "WEST",
            "Software",
            "B",
            "PASS",
            62,
            33,
            "REP-E01",
            "",
            "",
            "false",
            "false",
            "2026-06-15",
        )
    )
    # ACC-0008 expired lock — allocatable
    rows.append(
        _acct(
            8,
            "Brightpine Health",
            1400,
            "Enterprise",
            "US",
            "WEST",
            "Healthcare",
            "A",
            "PASS",
            79,
            51,
            "",
            "",
            "",
            "false",
            "false",
            "2025-12-01",
        )
    )
    # ACC-0009 open opportunity protected
    rows.append(
        _acct(
            9,
            "Quarry Lane Robotics",
            2300,
            "Enterprise",
            "US",
            "WEST",
            "Manufacturing",
            "A",
            "PASS",
            86,
            70,
            "REP-E01",
            "",
            "",
            "false",
            "true",
            "",
        )
    )
    # ACC-0010 missing headcount
    rows.append(
        _acct(
            10,
            "Solstice Payroll",
            None,
            "Enterprise",
            "US",
            "WEST",
            "Software",
            "A",
            "PASS",
            80,
            40,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )
    # ACC-0011 Commercial PASS A — inventory only unless policy includes commercial
    rows.append(
        _acct(
            11,
            "Nimbus Ledger",
            85,
            "Commercial",
            "US",
            "WEST",
            "Software",
            "A",
            "PASS",
            74,
            22,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )
    # ACC-0012 Tier C ENT
    rows.append(
        _acct(
            12,
            "Ironclad Payments",
            3100,
            "Enterprise",
            "US",
            "WEST",
            "Finance",
            "C",
            "PASS",
            44,
            10,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )
    # ACC-0013 assigned MM never touched (activity gap)
    rows.append(
        _acct(
            13,
            "Maple Circuit",
            410,
            "Mid-Market",
            "US",
            "WEST",
            "Software",
            "A",
            "PASS",
            83,
            61,
            "REP-M01",
            "REP-S01",
            "",
            "false",
            "false",
            "2026-04-01",
        )
    )
    # ACC-0014 heavily worked MM
    rows.append(
        _acct(
            14,
            "Harborline Insurance",
            680,
            "Mid-Market",
            "US",
            "WEST",
            "Insurance",
            "A",
            "PASS",
            90,
            80,
            "REP-M01",
            "REP-S01",
            "",
            "false",
            "false",
            "2026-03-01",
        )
    )
    # ACC-0015 FAIL gate
    rows.append(
        _acct(
            15,
            "Redwood Fleet",
            1900,
            "Enterprise",
            "US",
            "CENTRAL",
            "Logistics",
            "A",
            "FAIL",
            71,
            20,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )

    n = 16
    # 13 more protected ENT WEST on REP-E01 → 16 retained vs cap 14 (over-cap)
    # already 0005, 0007, 0009 = 3; add 13 more = 16
    for i in range(13):
        rows.append(
            _acct(
                n,
                next_name() if n != 16 else "Atlas Loom",
                1100 + (i * 40),
                "Enterprise",
                "US",
                "WEST",
                "Software" if i % 2 == 0 else "Manufacturing",
                "A" if i % 3 else "B",
                "PASS",
                60 + (i % 20),
                30 + i,
                "REP-E01",
                "",
                "",
                "true" if i % 2 == 0 else "false",
                "true" if i % 2 else "false",
                "2026-07-01" if i % 3 == 0 else "",
            )
        )
        n += 1

    # Eligible ENT WEST unowned (allocatable to REP-E02; E01 is over cap)
    for i in range(8):
        rows.append(
            _acct(
                n,
                next_name(),
                1250 + i * 55,
                "Enterprise",
                "US",
                "WEST",
                "Software",
                "A" if i < 5 else "B",
                "PASS",
                92 - i,
                50 + i,
                "",
                "",
                "",
                "false",
                "false",
                "",
            )
        )
        n += 1

    # ENT CENTRAL — mix retained and new
    for i in range(10):
        owner = "REP-E04" if i < 4 else ""
        customer = "true" if i < 2 else "false"
        opp = "true" if i == 2 else "false"
        rows.append(
            _acct(
                n,
                next_name(),
                1500 + i * 80,
                "Enterprise",
                "US",
                "CENTRAL",
                "Healthcare" if i % 2 else "Finance",
                "A" if i < 7 else "B",
                "PASS",
                85 - i,
                40 + i,
                owner,
                "",
                "",
                customer,
                opp,
                "2026-05-01" if i == 3 else "",
            )
        )
        n += 1

    # ENT EAST — no active AE (staffing gap). Mix A/B.
    for i in range(7):
        rows.append(
            _acct(
                n,
                next_name(),
                2000 + i * 100,
                "Enterprise",
                "US",
                "EAST",
                "Healthcare",
                "A" if i < 4 else "B",
                "PASS",
                80 - i,
                35 + i,
                "",
                "",
                "",
                "false",
                "false",
                "",
            )
        )
        n += 1

    # MM WEST allocatable / some retained
    for i in range(16):
        owner = "REP-M01" if i < 5 else ("REP-M02" if i < 8 else "")
        sdr = "REP-S01" if i % 2 == 0 else "REP-S02"
        rows.append(
            _acct(
                n,
                next_name(),
                220 + i * 30,
                "Mid-Market",
                "US",
                "WEST",
                "Software" if i % 3 else "Insurance",
                "A" if i < 10 else "B",
                "PASS",
                88 - i,
                45 + i,
                owner,
                sdr,
                "",
                "true" if i < 2 else "false",
                "false",
                "2026-04-15" if i == 1 else "",
            )
        )
        n += 1

    # MM CENTRAL
    for i in range(10):
        owner = "REP-M03" if i < 3 else ""
        rows.append(
            _acct(
                n,
                next_name(),
                250 + i * 40,
                "Mid-Market",
                "US",
                "CENTRAL",
                "Manufacturing",
                "A" if i < 6 else "B",
                "PASS",
                82 - i,
                38 + i,
                owner,
                "REP-S03",
                "",
                "false",
                "true" if i == 0 else "false",
                "",
            )
        )
        n += 1

    # MM EAST — SDR gap (no active SDR). Extra rows besides 0004.
    for i in range(8):
        rows.append(
            _acct(
                n,
                next_name(),
                300 + i * 25,
                "Mid-Market",
                "US",
                "EAST",
                "Logistics",
                "A" if i < 5 else "B",
                "PASS",
                76 - i,
                30 + i,
                "",
                "",
                "",
                "false",
                "false",
                "",
            )
        )
        n += 1

    # Commercial inventory WEST
    for i in range(8):
        rows.append(
            _acct(
                n,
                next_name(),
                20 + i * 15,
                "Commercial",
                "US",
                "WEST",
                "Software",
                "A" if i < 3 else ("B" if i < 6 else "C"),
                "PASS",
                70 - i,
                20 + i,
                "REP-C01" if i < 2 else "",
                "",
                "",
                "false",
                "false",
                "",
            )
        )
        n += 1

    # C/D nurture + HOLD
    for i, (tier, gate, emp, seg, terr) in enumerate(
        [
            ("C", "PASS", 1700, "Enterprise", "CENTRAL"),
            ("D", "PASS", 900, "Mid-Market", "WEST"),
            ("C", "HOLD", 400, "Mid-Market", "CENTRAL"),
            ("D", "FAIL", 80, "Commercial", "EAST"),
            ("B", "HOLD", 2200, "Enterprise", "WEST"),
        ]
    ):
        rows.append(
            _acct(
                n,
                next_name(),
                emp,
                seg,
                "US",
                terr,
                "Software",
                tier,
                gate,
                35 + i * 5,
                10,
                "",
                "",
                "",
                "false",
                "false",
                "",
            )
        )
        n += 1

    # Stale MM picklist already 0001; add one more MM→ENT CENTRAL
    rows.append(
        _acct(
            n,
            next_name(),
            1450,
            "Mid-Market",
            "US",
            "CENTRAL",
            "Finance",
            "A",
            "PASS",
            87,
            64,
            "",
            "",
            "",
            "false",
            "false",
            "",
        )
    )
    n += 1

    assert n - 1 == len(rows)
    return rows


def build_roster() -> list[dict[str, str]]:
    def seat(
        sid: str,
        rid: str,
        role: str,
        segment: str,
        territory: str,
        start: str,
        end: str,
        ramp: str,
        status: str,
        cap: str = "",
    ) -> dict[str, str]:
        return {
            "seat_id": sid,
            "rep_id": rid,
            "role": role,
            "segment": segment,
            "territory": territory,
            "start_date": start,
            "end_date": end,
            "ramp_profile": ramp,
            "eligibility_status": status,
            "cap_override": cap,
        }

    return [
        seat("SEAT-E01", "REP-E01", "AE", "Enterprise", "WEST", "2025-03-01", "", "experienced", "active"),
        seat("SEAT-E02", "REP-E02", "AE", "Enterprise", "WEST", "2025-09-01", "", "standard", "active"),
        seat("SEAT-E03", "REP-E03", "AE", "Enterprise", "WEST", "2026-05-01", "", "standard", "future"),
        seat("SEAT-E04", "REP-E04", "AE", "Enterprise", "CENTRAL", "2025-01-15", "", "experienced", "active"),
        seat("SEAT-E05", "REP-E05", "AE", "Enterprise", "EAST", "2026-03-01", "", "standard", "future"),
        seat("SEAT-E06", "", "AE", "Enterprise", "EAST", "2026-09-01", "", "standard", "future"),
        seat("SEAT-M01", "REP-M01", "AE", "Mid-Market", "WEST", "2025-02-01", "", "experienced", "active"),
        seat("SEAT-M02", "REP-M02", "AE", "Mid-Market", "WEST", "2025-07-01", "", "standard", "active"),
        seat("SEAT-M03", "REP-M03", "AE", "Mid-Market", "CENTRAL", "2025-04-01", "", "standard", "active"),
        seat("SEAT-M04", "REP-M04", "AE", "Mid-Market", "EAST", "2025-06-01", "", "standard", "active"),
        seat("SEAT-M05", "REP-M05", "AE", "Mid-Market", "EAST", "2026-06-01", "", "standard", "future"),
        seat("SEAT-M06", "REP-M06", "AE", "Mid-Market", "CENTRAL", "2024-11-01", "2026-04-30", "standard", "active"),
        seat("SEAT-C01", "REP-C01", "AE", "Commercial", "WEST", "2025-05-01", "", "standard", "active"),
        seat("SEAT-S01", "REP-S01", "SDR", "Mid-Market", "WEST", "2025-01-01", "", "standard", "active"),
        seat("SEAT-S02", "REP-S02", "SDR", "Mid-Market", "WEST", "2025-08-01", "", "standard", "active"),
        seat("SEAT-S03", "REP-S03", "SDR", "Mid-Market", "CENTRAL", "2025-03-01", "", "standard", "active"),
        seat("SEAT-S04", "REP-S04", "SDR", "Mid-Market", "EAST", "2026-08-01", "", "standard", "future"),
        seat("SEAT-S05", "REP-S05", "SDR", "Enterprise", "WEST", "2025-02-01", "", "standard", "active"),
    ]


def build_activities(accounts: list[dict[str, str]]) -> list[dict[str, str]]:
    as_of = datetime(2026, 2, 1)
    rows: list[dict[str, str]] = []
    aid = 1

    def add(account_id: str, days_ago: int, kind: str, rep: str, outcome: str) -> None:
        nonlocal aid
        ts = as_of - timedelta(days=days_ago)
        rows.append(
            {
                "activity_id": f"ACT-{aid:05d}",
                "account_id": account_id,
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "activity_type": kind,
                "rep_id": rep,
                "outcome": outcome,
            }
        )
        aid += 1

    # Heavy work on ACC-0014
    for d, kind in [
        (5, "call"),
        (8, "email"),
        (12, "meeting"),
        (20, "call"),
        (33, "email"),
        (40, "call"),
    ]:
        add("ACC-0014", d, kind, "REP-M01", "connected" if kind == "call" else "sent")

    # Some work on retained ENT WEST
    for acc, owner in [
        ("ACC-0005", "REP-E01"),
        ("ACC-0007", "REP-E01"),
        ("ACC-0009", "REP-E01"),
        ("ACC-0016", "REP-E01"),
        ("ACC-0018", "REP-E01"),
        ("ACC-0020", "REP-E01"),
    ]:
        add(acc, 7, "call", owner, "connected")
        add(acc, 18, "email", owner, "sent")

    # MM WEST worked (not ACC-0013 — activity gap)
    owned_mm = [r for r in accounts if r["account_id"] not in {"ACC-0013", "ACC-0014"} and r["owner_id"] in {"REP-M01", "REP-M02", "REP-M03"}]
    for i, acc in enumerate(owned_mm):
        if i % 3 == 0:
            continue  # leave some untouched besides 0013
        add(acc["account_id"], 6 + i, "call", acc["owner_id"], "connected")
        if i % 2 == 0:
            add(acc["account_id"], 15 + i, "email", acc["owner_id"], "sent")

    # CENTRAL ENT retained
    for acc in accounts:
        if acc["owner_id"] == "REP-E04" and acc["account_id"] != "ACC-0015":
            add(acc["account_id"], 11, "meeting", "REP-E04", "held")

    # Non-qualifying types should not count
    add("ACC-0013", 4, "note", "REP-M01", "logged")
    add("ACC-0002", 9, "linkedin", "REP-S01", "viewed")

    return rows


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    accounts = build_accounts()
    roster = build_roster()
    activities = build_activities(accounts)
    write_csv(HERE / "accounts.csv", ACCOUNT_FIELDS, accounts)
    write_csv(HERE / "roster.csv", ROSTER_FIELDS, roster)
    write_csv(HERE / "activities.csv", ACTIVITY_FIELDS, activities)
    print(f"accounts={len(accounts)} roster={len(roster)} activities={len(activities)}")


if __name__ == "__main__":
    main()
