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
        "YYYY-MM", 160, "FL OIR files are quarterly with a processing lag"
    ),
    "netlify/functions/dl01-answers.json": (
        "YYYY-MM-DD", 45, "the atlas tracks sessions, dockets, and ballots; re-verify at least every six weeks"
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
        ledger = json.loads((ROOT / rel).read_text(encoding="utf-8"))
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
