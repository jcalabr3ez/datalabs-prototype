#!/usr/bin/env python3
"""Fail when any ledger's as_of has aged past its publisher cadence.

Run in CI on a schedule and on pull requests. A failure here means a ledger
is stale relative to how often its source publishes, and a refresh (or an
explicit cadence change below) is due.
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ledger -> (as_of format, max age in days, why)
RULES = {
    "netlify/functions/dl03-answers.json": (
        "YYYY-MM", 75, "FTA NTD publishes monthly with roughly a two-month lag"
    ),
    "netlify/functions/dl02-answers.json": (
        "YYYY-MM", 160, "monthly Cursor Automation rechecks the register; this 160-day gate is the backstop"
    ),
    "netlify/functions/dl01-answers.json": (
        "YYYY-MM-DD", 45, "weekly Cursor Automation rechecks the register; this 45-day gate is the backstop"
    ),
    "netlify/functions/dl04-answers.json": (
        "YYYY-MM", 700, "EIA Electric Power Annual / Form EIA-861 publishes the prior calendar year each October"
    ),
    "netlify/functions/dl05-answers.json": (
        "YYYY-MM", 160, "CTHRU updates monthly and as_of is that file month; the 160-day gate is the backstop. Board valuations still move on the research pass."
    ),
    "netlify/functions/dl13-answers.json": (
        "YYYY-MM", 75, "Census BFS publishes monthly; the 75-day gate is the backstop"
    ),
    "netlify/functions/dl14-answers.json": (
        "YYYY-MM", 75, "BLS LAUS publishes monthly with about a one-month lag"
    ),
    "netlify/functions/dl16-answers.json": (
        "YYYY-MM", 75, "Census BPS state year-to-date files publish monthly"
    ),
    "netlify/functions/dl17-answers.json": (
        "YYYY-MM", 400, "Census vintage population estimates publish once a year"
    ),
    "netlify/functions/dl06-answers.json": (
        "YYYY-MM", 2000, "NCES NPEFS per-pupil finance is annual with a multi-year lag"
    ),
    "netlify/functions/dl07-answers.json": (
        "YYYY-MM", 1200, "NCES Digest enrollment is annual with a long lag"
    ),
    "netlify/functions/dl08-answers.json": (
        "YYYY-MM", 1600, "IPEDS Fall Enrollment is annual with a long lag"
    ),
    "netlify/functions/dl09-answers.json": (
        "YYYY-MM", 1400, "NCES Digest charter tables are annual with a long lag"
    ),
    "netlify/functions/dl12-answers.json": (
        "YYYY-MM", 1200, "CMS Medicaid FMR is annual"
    ),
    "netlify/functions/dl15-answers.json": (
        "YYYY-MM", 400, "BEA state GDP annual revision"
    ),
    "netlify/functions/dl19-answers.json": (
        "YYYY-MM", 800, "BEA regional price parities are annual"
    ),
    "netlify/functions/dl20-answers.json": (
        "YYYY-MM", 1200, "IRS SOI migration is annual with a multi-year lag"
    ),
    "netlify/functions/dl21-answers.json": (
        "YYYY-MM", 1600, "IRS SOI historic table 2 is annual with a multi-year lag"
    ),
    "netlify/functions/dl23-answers.json": (
        "YYYY-MM", 1200, "FHWA Highway Statistics are annual"
    ),
    "netlify/functions/dl24-answers.json": (
        "YYYY-MM", 800, "EIA SEDS complete CO2 (TETCE) publishes the prior calendar year each June"
    ),
    "netlify/functions/dl25-answers.json": (
        "YYYY-MM", 900, "Census subcounty population estimates are annual"
    ),
    "netlify/functions/dl26-answers.json": (
        "YYYY-MM", 900, "Census subcounty population estimates are annual"
    ),
    "netlify/functions/dl27-answers.json": (
        "YYYY-MM", 400, "City of Boston earnings report is annual"
    ),
    "netlify/functions/dl28-answers.json": (
        "YYYY-MM", 200, "Census QTAX publishes quarterly"
    ),
    "netlify/functions/dl29-answers.json": (
        "YYYY-MM", 200, "Census QTAX publishes quarterly"
    ),
    "netlify/functions/dl31-answers.json": (
        "YYYY-MM", 1200, "BJS Prisoners statistical tables are annual"
    ),
    "netlify/functions/dl10-answers.json": (
        "YYYY-MM", 400, "CMS Hospital General Information is refreshed periodically"
    ),
    "netlify/functions/dl11-answers.json": (
        "YYYY-MM-DD", 100, "HRSA OPAIS posts a dated daily export; this 100-day gate is the quarterly-ish backstop"
    ),
    "netlify/functions/dl22-answers.json": (
        "YYYY-MM", 75, "FTA NTD monthly ridership publishes with about a two-month lag"
    ),
    "netlify/functions/dl30-answers.json": (
        "YYYY-MM", 400, "CTHRU calendar-year payroll is complete after year-end"
    ),
    "netlify/functions/dl32-answers.json": (
        "YYYY-MM", 400, "CTHRU calendar-year legislator payroll is complete after year-end"
    ),
    "netlify/functions/dl33-answers.json": (
        "YYYY-MM", 900, "CHIA MHIS is biennial; the 2025 survey published in December 2025"
    ),
    "netlify/functions/dl34-answers.json": (
        "YYYY-MM", 400, "DESE / E2C Boston enrollment is annual; FY finance lags one year"
    ),
}


MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"])}


def parse_as_of(value, fmt):
    # accept "YYYY-MM", "YYYY-MM-DD", and "Month YYYY"
    if value.split(" ")[0] in MONTHS:
        name, year = value.split(" ")
        return date(int(year), MONTHS[name], 28)
    parts = [int(x) for x in value.split("-")]
    if fmt == "YYYY-MM" or len(parts) == 2:
        # treat a monthly vintage as fresh through the end of that month
        return date(parts[0], parts[1], 28)
    return date(parts[0], parts[1], parts[2])


def main():
    today = date.today()
    failures = []
    for rel, (fmt, max_days, why) in RULES.items():
        path = ROOT / rel
        if not path.exists():
            print(f"skip   {rel}  missing")
            continue
        ledger = json.loads(path.read_text(encoding="utf-8"))
        if ledger.get("status") == "build":
            print(f"skip   {rel}  status=build")
            continue
        as_of = ledger.get("as_of")
        if not as_of:
            failures.append(f"{rel}: no as_of field")
            continue
        age = (today - parse_as_of(str(as_of), fmt)).days
        status = "STALE" if age > max_days else "fresh"
        print(f"{status:5}  {rel}  as_of {as_of}  age {age}d  (limit {max_days}d: {why})")
        if age > max_days:
            failures.append(f"{rel}: as_of {as_of} is {age} days old, limit {max_days} ({why})")
    if failures:
        print("\nFRESHNESS FAILURES:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\nall ledgers within cadence")


if __name__ == "__main__":
    main()
