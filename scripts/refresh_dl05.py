#!/usr/bin/env python3
"""Refresh DL-05 retiree figures and the name-search index from CTHRU.

Source (SRC-503): Office of the Comptroller, CTHRU State and Teachers
Retirement Benefits, Socrata dataset pni4-392n. The Comptroller updates
this file monthly. Same columns as the partner State & Teacher Retirees
extract.

This script:
  1. Pulls yearly MSERS/MTRS totals for every calendar year on the API.
  2. Pulls every named row for the latest CTHRU year (the search year).
  3. Rebuilds retiree blocks in netlify/functions/dl05-answers.json.
  4. Writes compact last-name shards under pensions/search/.
  5. Re-runs inject_data.py.

Board funded status and returns (SRC-501 / SRC-502) are left alone; those
still come from the PERAC extract and the research pass.

Never pushes to main. Exits nonzero when sanity checks fail.
"""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "netlify/functions/dl05-answers.json"
SEARCH_DIR = ROOT / "pensions/search"
API = "https://cthru.data.socrata.com/resource/pni4-392n.json"
UA = "PioneerDataLabs/1.0 (jcalabrese@pioneerinstitute.org)"
PAGE = 50000

# 2024 extract cells, used as a two-path check against the live API.
VERIFY_2024 = {
    "count": 134205,
    "count_slop": 20,
    "annual_amount": 6407446500.96,
    "amount_slop": 5_000_000,
}


def soda(params: dict, timeout=180):
    q = urllib.parse.urlencode(params, safe="(),'=<>")
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_yearly():
    rows = soda({
        "$select": "year,retirement_system,count(*),sum(annual_amount),avg(annual_amount),max(annual_amount)",
        "$group": "year,retirement_system",
        "$order": "year,retirement_system",
        "$limit": 100,
    })
    by_year = defaultdict(lambda: {"year": None, "count": 0, "annual_amount": 0.0,
                                   "msers": None, "mtrs": None})
    for r in rows:
        y = int(r["year"])
        rec = {
            "system": r["retirement_system"],
            "count": int(r["count"]),
            "annual_amount": round(float(r["sum_annual_amount"]), 2),
            "avg_amount": round(float(r["avg_annual_amount"]), 2),
            "max_amount": round(float(r["max_annual_amount"]), 2),
        }
        slot = by_year[y]
        slot["year"] = y
        slot["count"] += rec["count"]
        slot["annual_amount"] += rec["annual_amount"]
        if rec["system"] == "MSERS":
            slot["msers"] = rec
        elif rec["system"] == "MTRS":
            slot["mtrs"] = rec
    yearly = []
    for y in sorted(by_year):
        slot = by_year[y]
        slot["annual_amount"] = round(slot["annual_amount"], 2)
        slot["avg_amount"] = round(slot["annual_amount"] / slot["count"], 2)
        yearly.append(slot)
    return yearly


def fetch_year_rows(year: int):
    rows, offset = [], 0
    while True:
        page = soda({
            "$where": f"year={year}",
            "$order": "trans_no",
            "$limit": PAGE,
            "$offset": offset,
        }, timeout=180)
        rows.extend(page)
        print(f"  fetched {len(rows)} rows for {year}", flush=True)
        if len(page) < PAGE:
            return rows
        offset += PAGE


def display_name(r):
    last = (r.get("last_name") or "").strip()
    first = (r.get("first_name") or "").strip()
    if last and first:
        return f"{last}, {first}"
    return last or first


def dstr(iso):
    if not iso:
        return ""
    return iso[:10]


def money(n):
    return round(float(n or 0), 2)


def last_initial(name: str) -> str:
    last = name.split(",")[0].strip()
    ch = (last[:1] or "#").upper()
    return ch if "A" <= ch <= "Z" else "#"


def compact_row(r):
    name = display_name(r)
    title = r.get("title_at_retirement") or ""
    if title == "N/A":
        title = ""
    return [
        name,
        r.get("retirement_system") or "",
        r.get("department_last_worked_in") or "",
        title,
        dstr(r.get("date_of_retirement")),
        money(r.get("annual_amount")),
    ]


def write_shards(year: int, as_of: str, rows: list, complete: bool):
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    for old in SEARCH_DIR.glob("*.json.gz"):
        old.unlink()
    shards = defaultdict(list)
    for r in rows:
        rec = compact_row(r)
        shards[last_initial(rec[0])].append(rec)
    letters = []
    for letter, items in shards.items():
        items.sort(key=lambda x: (x[0].lower(), -x[5]))
        raw = json.dumps(items, ensure_ascii=True, separators=(",", ":")).encode()
        dest = SEARCH_DIR / f"{letter}.json.gz"
        dest.write_bytes(gzip.compress(raw, mtime=0))
        letters.append(letter)
        print(f"  shard {letter} {len(items)} rows {dest.stat().st_size} B gzip")
    letters.sort()
    manifest = {
        "year": year,
        "as_of": as_of,
        "count": len(rows),
        "complete": complete,
        "letters": letters,
        "source_id": "SRC-503",
    }
    (SEARCH_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8"
    )
    return manifest


def top_from(rows, n=15):
    ranked = sorted(rows, key=lambda r: float(r.get("annual_amount") or 0), reverse=True)
    out = []
    for r in ranked[:n]:
        title = r.get("title_at_retirement")
        if title == "N/A":
            title = None
        out.append({
            "name": display_name(r),
            "system": r.get("retirement_system"),
            "department": r.get("department_last_worked_in") or None,
            "title": title or None,
            "retired": dstr(r.get("date_of_retirement")) or None,
            "annual_amount": money(r.get("annual_amount")),
        })
    return out


def depts_from(rows, n=15):
    agg = defaultdict(lambda: {"count": 0, "annual_amount": 0.0})
    for r in rows:
        key = (r.get("retirement_system"), r.get("department_last_worked_in") or "")
        agg[key]["count"] += 1
        agg[key]["annual_amount"] += float(r.get("annual_amount") or 0)
    ranked = sorted(agg.items(), key=lambda kv: -kv[1]["annual_amount"])[:n]
    out = []
    for (sys, dept), v in ranked:
        out.append({
            "system": sys,
            "department": dept,
            "count": v["count"],
            "annual_amount": round(v["annual_amount"], 2),
            "avg_amount": round(v["annual_amount"] / v["count"], 2),
        })
    return out


def titles_from(rows, n=15, min_n=50):
    agg = defaultdict(lambda: {"count": 0, "annual_amount": 0.0})
    for r in rows:
        title = r.get("title_at_retirement")
        if not title or title == "N/A":
            continue
        key = (r.get("retirement_system"), title)
        agg[key]["count"] += 1
        agg[key]["annual_amount"] += float(r.get("annual_amount") or 0)
    ranked = [
        (k, v) for k, v in agg.items() if v["count"] >= min_n
    ]
    ranked.sort(key=lambda kv: -kv[1]["annual_amount"] / kv[1]["count"])
    out = []
    for (sys, title), v in ranked[:n]:
        out.append({
            "system": sys,
            "title": title,
            "count": v["count"],
            "annual_amount": round(v["annual_amount"], 2),
            "avg_amount": round(v["annual_amount"] / v["count"], 2),
        })
    return out


def new_retirees(rows, year: int):
    by = defaultdict(lambda: {"count": 0, "annual_amount": 0.0})
    for r in rows:
        if dstr(r.get("date_of_retirement"))[:4] != str(year):
            continue
        sys = r.get("retirement_system")
        by[sys]["count"] += 1
        by[sys]["annual_amount"] += float(r.get("annual_amount") or 0)
    out = {}
    total_n, total_a = 0, 0.0
    for sys, v in by.items():
        out[sys] = {
            "count": v["count"],
            "annual_amount": round(v["annual_amount"], 2),
            "avg_amount": round(v["annual_amount"] / v["count"], 2) if v["count"] else 0,
        }
        total_n += v["count"]
        total_a += v["annual_amount"]
    return {
        "count": total_n,
        "annual_amount": round(total_a, 2),
        "by_system": out,
    }


def main():
    old = json.loads(LEDGER.read_text(encoding="utf-8"))
    print("fetching yearly totals from CTHRU", flush=True)
    yearly = fetch_yearly()
    if len(yearly) < 10:
        sys.exit(f"FATAL: only {len(yearly)} years from CTHRU")
    years = [y["year"] for y in yearly]
    search_year = max(years)
    # Last complete calendar year is the newest year that is not the
    # in-progress CTHRU year, or the search year if we are in January
    # and CTHRU has not opened the new year yet.
    today = date.today()
    complete_year = search_year - 1 if search_year in years and search_year >= today.year else search_year
    if complete_year not in years:
        complete_year = search_year
    search_complete = search_year < today.year

    y2024 = next((y for y in yearly if y["year"] == 2024), None)
    if not y2024:
        sys.exit("FATAL: CTHRU has no 2024 rows; cannot verify against the extract")
    if abs(y2024["count"] - VERIFY_2024["count"]) > VERIFY_2024["count_slop"]:
        sys.exit(f"FATAL: 2024 count {y2024['count']} vs extract {VERIFY_2024['count']}")
    if abs(y2024["annual_amount"] - VERIFY_2024["annual_amount"]) > VERIFY_2024["amount_slop"]:
        sys.exit(
            f"FATAL: 2024 amount {y2024['annual_amount']} vs extract {VERIFY_2024['annual_amount']}"
        )
    print(f"  2024 check ok  count {y2024['count']}  amount {y2024['annual_amount']}")

    print(f"fetching named rows for search year {search_year}", flush=True)
    named = fetch_year_rows(search_year)
    if len(named) < 100000:
        sys.exit(f"FATAL: only {len(named)} named rows for {search_year}")

    # as_of is the month we pulled CTHRU. A complete prior year stamps
    # December; an open year stamps the fetch month so the freshness
    # gate moves with the monthly workflow.
    as_of = f"{search_year}-12" if search_complete else f"{today.year}-{today.month:02d}"
    month_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    revised = f"{month_abbr[today.month - 1]} {today.day}, {today.year}"

    chart_years = [y for y in yearly if y["year"] <= complete_year]
    complete = next(y for y in yearly if y["year"] == complete_year)
    search_slot = next(y for y in yearly if y["year"] == search_year)

    top = top_from(named)
    depts = depts_from(named)
    titles = titles_from(named)
    newbie = new_retirees(named, search_year)
    first = chart_years[0]
    growth = round((complete["annual_amount"] / first["annual_amount"] - 1) * 100, 1)

    print("writing search shards", flush=True)
    manifest = write_shards(search_year, as_of, named, search_complete)

    old["as_of"] = as_of
    old["retiree_year"] = complete_year
    old["search_year"] = search_year
    old["page"]["revised"] = revised
    old["page"]["version"] = old["page"].get("version") or "1.1"
    old["scope"] = (
        "Covers every Massachusetts public retirement board's latest PERAC "
        "actuarial valuation (funded ratio, unfunded liability, actuarial "
        "accrued liability, membership, average salary and benefit, assumed "
        "rate of return) and compiled investment returns (one-year, five-year, "
        "ten-year, and since-inception), plus the compiled State (MSERS) and "
        "Teachers (MTRS) retiree payroll for calendar years 2011 through the "
        "dataset retiree_year: yearly headcount and annual pension totals, "
        "department and title rankings, the largest individual pensions, and "
        "a page-side name search of the latest CTHRU year (search_year). "
        "Does NOT cover: answering a named-retiree lookup in the ask box "
        "(use the Retirees search on the page); municipal or local-board "
        "retiree names; retirement advice, benefit estimates, or what a "
        "member will receive; forecasts of funded status; other states' "
        "pension systems; or Commonwealth payroll and vendor payments."
    )
    old["vintage_note"] = (
        "Board funded status and membership are the latest PERAC actuarial "
        "valuation on file for each board in the compiled Performance extract "
        "(valuation dates January 1, 2021 through January 1, 2023; most boards "
        "are 2022 or 2023). Investment returns are the compiled PERAC returns "
        "file shipped with that extract; the one-year column is calendar 2023. "
        f"State and Teacher retiree figures are rebuilt from the live CTHRU "
        f"Socrata file (dataset pni4-392n). Yearly payroll totals and the "
        f"headline run through calendar {complete_year}, the last complete "
        f"year. Name search, the largest pensions, and department rankings "
        f"use calendar {search_year}"
        + (" (year-to-date)" if not search_complete else "")
        + f", CTHRU as_of {as_of}. The 2024 CTHRU year matches the partner "
        "extract within 20 rows and $5 million. PERAC's 2024 Investment "
        "Report and the July 2026 funded-ratios table are still the next "
        "board-side research-pass job."
    )
    old["source_id_map"]["SRC-503"]["url"] = "https://cthrupensions.mass.gov/"
    old["source_id_map"]["SRC-503"]["api"] = API
    old["source_id_map"]["SRC-503"]["dataset"] = "pni4-392n"
    old["source_id_map"]["SRC-503"]["cadence"] = "Monthly named-retiree file for MSERS and MTRS"
    old["source_id_map"]["SRC-503"]["note"] = (
        "Each row is a named retiree in one calendar year. Totals are the sum "
        "of annual amounts in that year, not a PERAC actuarial headcount. "
        f"Name search uses {search_year}; the payroll chart uses complete "
        f"years through {complete_year}."
    )

    old["retirees"] = {
        "row_count": sum(y["count"] for y in yearly),
        "first_year": yearly[0]["year"],
        "latest_year": complete_year,
        "search_year": search_year,
        "search_complete": search_complete,
        "as_of": as_of,
        "yearly": chart_years,
        "yearly_including_search": yearly,
        "latest": {
            "year": complete["year"],
            "count": complete["count"],
            "annual_amount": complete["annual_amount"],
            "avg_amount": complete["avg_amount"],
            "msers": complete["msers"],
            "mtrs": complete["mtrs"],
            "new_retirees": newbie if search_year == complete_year else {
                "count": None,
                "note": f"new-retiree count is computed on the search year ({search_year})",
            },
        },
        "search": {
            "year": search_year,
            "count": search_slot["count"],
            "annual_amount": search_slot["annual_amount"],
            "avg_amount": search_slot["avg_amount"],
            "msers": search_slot["msers"],
            "mtrs": search_slot["mtrs"],
            "complete": search_complete,
            "as_of": as_of,
            "new_retirees": newbie,
        },
        "top_pensions": top,
        "departments": depts,
        "titles": titles,
        "manifest": manifest,
    }

    d = old["derived"]
    d["retiree_year"] = complete_year
    d["search_year"] = search_year
    d["retiree_count"] = complete["count"]
    d["retiree_annual_amount"] = complete["annual_amount"]
    d["retiree_avg_amount"] = complete["avg_amount"]
    d["retiree_amount_change_from_2011_pct"] = growth
    d["largest_pension"] = {
        "name": top[0]["name"],
        "system": top[0]["system"],
        "annual_amount": top[0]["annual_amount"],
        "year": search_year,
    }
    d["new_retirees_search_year"] = newbie["count"]
    d.pop("new_retirees_2024", None)

    old["latest"]["retirees"] = {
        "year": complete["year"],
        "count": complete["count"],
        "annual_amount": complete["annual_amount"],
        "avg_amount": complete["avg_amount"],
        "msers_count": complete["msers"]["count"],
        "msers_annual_amount": complete["msers"]["annual_amount"],
        "mtrs_count": complete["mtrs"]["count"],
        "mtrs_annual_amount": complete["mtrs"]["annual_amount"],
        "search_year": search_year,
        "search_count": search_slot["count"],
    }

    old["verification"]["retiree_yearly"] = (
        f"Yearly MSERS and MTRS counts and annual-amount sums are rebuilt "
        f"from CTHRU dataset pni4-392n. 2024 matched the partner extract "
        f"within {VERIFY_2024['count_slop']} rows and "
        f"${VERIFY_2024['amount_slop']:,.0f}. Complete year {complete_year}: "
        f"{complete['count']:,} named retirees and "
        f"${complete['annual_amount']:,.2f}. Search year {search_year}: "
        f"{search_slot['count']:,} rows."
    )
    old["verification"]["twbx"] = (
        "Board cells still match the MA_Pensions_Annual extract. Retiree "
        "aggregates now come from the live CTHRU API, checked against the "
        "2024 extract year."
    )

    LEDGER.write_text(json.dumps(old, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")
    print(
        f"wrote {LEDGER}  complete={complete_year} {complete['count']:,} "
        f"${complete['annual_amount']:,.0f}  search={search_year} "
        f"{search_slot['count']:,}"
    )
    subprocess.check_call([sys.executable, str(ROOT / "scripts/inject_data.py")])


if __name__ == "__main__":
    main()
