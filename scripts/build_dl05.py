#!/usr/bin/env python3
"""Compile the DL-05 Massachusetts Public Pensions ledger from the partner
workbook extracts.

This is the one-time rebuild path, not a publisher refresh. The Performance
workbook (MA_Pensions_Annual) holds PERAC board valuations and compiled
returns. The State & Teacher Retirees workbook holds the CTHRU named-retiree
file for MSERS and MTRS, calendar years 2011 through 2024.

Primary sources (what the figures are):
  SRC-501  PERAC board actuarial valuations / funded status
  SRC-502  PERAC compiled investment returns (one-year return is calendar 2023)
  SRC-503  CTHRU State and Teachers Retirement Benefits (Comptroller)

The TWBX files stay out of git. Point at extracted Hyper files:

  DL05_ANNUAL_HYPER=/path/to/Sheet1+\\ (Multiple\\ Connections).hyper
  DL05_RETIREES_HYPER=/path/to/2011-2018\\ Retirees.hyper

Writes netlify/functions/dl05-answers.json. Never pushes.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from tableauhyperapi import Connection, HyperProcess, Telemetry

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "netlify/functions/dl05-answers.json"

ANNUAL_DEFAULT = Path(
    "/tmp/twbx-annual/Data/hyper/Sheet1+ (Multiple Connections).hyper"
)
RETIREES_DEFAULT = Path(
    "/tmp/twbx-retirees/Data/Tableau/2011-2018 Retirees.hyper"
)

# Stale duplicate of Boston City (2012 valuation sitting next to the 2022 row).
DROP_BOARDS = {"Boston"}

# Display names and slugs for the two Commonwealth systems the retiree
# file covers, plus the other large boards the page highlights.
BOARD_SLUG_ALIASES = {
    "STATE": "state",
    "STATE RETIREMENT BOARD": "state",
    "MASS TEACHERS MTRS": "mtrs",
    "MASS TEACHERS RETIREMENT SYSTEM MTRS": "mtrs",
    "BOSTON CITY": "boston-city",
    "BOSTON TEACHERS": "boston-teachers",
    "GREATER LAWRENCE": "greater-lawrence",
    "GREATER LAWRENCE SANITARY DISTRICT": "greater-lawrence",
    "MASS HOUSING FINANCE AGENCY MHFA": "mhfa",
    "MASSPORT": "massport",
    "MASS WATER RESOURCES AUTHORITY MWRA": "mwra",
    "HAMPDEN COUNTY REGIONAL": "hampden-county",
    "HAMPDEN COUNTY": "hampden-county",
    "BLUE HILLS REGIONAL": "blue-hills",
    "BLUE HILLS REGIONAL SCHOOL": "blue-hills",
    "MINUTEMAN REGIONAL": "minuteman",
    "MINUTEMAN REGIONAL SCHOOL DISTRICT": "minuteman",
}


def norm_key(name: str) -> str:
    s = name.upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for drop in (
        " RETIREMENT BOARD",
        " RETIREMENT SYSTEM",
        " RETIREMENT",
        " COUNTY REGIONAL",
    ):
        if s.endswith(drop.strip()) and s != "STATE RETIREMENT BOARD":
            pass
    return s


def slugify(name: str) -> str:
    key = norm_key(name)
    if key in BOARD_SLUG_ALIASES:
        return BOARD_SLUG_ALIASES[key]
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s


def money(n) -> int | None:
    if n is None:
        return None
    return int(round(float(n)))


def pct(n, digits=1) -> float | None:
    if n is None:
        return None
    return round(float(n) * 100, digits)


def hyper_rows(path: Path, table_pred=None):
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=str(path)) as conn:
            tables = list(conn.catalog.get_table_names("Extract"))
            picked = []
            for t in tables:
                name = str(t.name).strip('"')
                if table_pred and not table_pred(name):
                    continue
                defn = conn.catalog.get_table_definition(t)
                cols = [str(c.name).strip('"') for c in defn.columns]
                rows = conn.execute_list_query(f"SELECT * FROM {t}")
                picked.append((name, cols, rows))
            return picked


def load_boards(annual_path: Path):
    tables = hyper_rows(annual_path)
    sheet = next(t for t in tables if t[0].startswith("Sheet1"))
    rets = next(t for t in tables if t[0].startswith("Returns"))
    scols, srows = sheet[1], sheet[2]
    rcols, rrows = rets[1], rets[2]
    si = {c: i for i, c in enumerate(scols)}
    ri = {c: i for i, c in enumerate(rcols)}

    # Dedup (board, year): keep the last row (the extract sometimes stores
    # two market-value vintages for the same valuation year).
    hist = {}
    for r in srows:
        name = r[si["Retirement Board"]]
        if name in DROP_BOARDS:
            continue
        year = int(r[si["Date of Last Valuation (1 January)"]] or 0)
        hist[(name, year)] = r

    latest = {}
    history = defaultdict(list)
    for (name, year), r in sorted(hist.items()):
        rec = {
            "y": year,
            "funded_pct": pct(r[si["Funded Ratio"]], 1),
            "ual": money(r[si["Unfunded Liability (000s)"]]),
            "aal": money(r[si["Total Actuarial Liability"]]),
            "active": money(r[si["Number of Members (Active)"]]),
            "retired": money(r[si["Number of Members (Retired)"]]),
            "avg_salary": money(r[si["Average Salary (Active)"]]),
            "avg_benefit": money(r[si["Average Benefit (Retired)"]]),
            "market_value": money(r[si["Market Value"]]),
            "arr_pct": pct(r[si["ARR"]], 2),
            "year_fully_funded": (
                int(r[si["Year Fully Funded"]])
                if r[si["Year Fully Funded"]] is not None
                else None
            ),
            "grade": r[si["Grade"]] or None,
        }
        # Two-path check: published funded ratio vs 1 - UAL/AAL.
        if rec["aal"] and rec["ual"] is not None:
            recomputed = (1 - rec["ual"] / rec["aal"]) * 100
            rec["funded_recomputed_pct"] = round(recomputed, 1)
        history[name].append(rec)
        latest[name] = rec

    # Returns file: column is named Return (2022) in the extract; the
    # Tableau caption and the +11% statewide print are calendar 2023.
    returns = {}
    for r in rrows:
        raw = r[ri["Retirement Board"]]
        returns[norm_key(raw)] = {
            "return_1y_pct": pct(r[ri["Return (2022)"]], 2),
            "return_5y_pct": pct(r[ri["5-Year Return"]], 2),
            "return_10y_pct": pct(r[ri["10-Year Return"]], 2),
            "return_inception_pct": (
                pct(r[ri["38-Year Return"]], 2)
                if r[ri["38-Year Return"]] is not None
                else None
            ),
        }

    returns_by_slug = {}
    for rk, rv in returns.items():
        returns_by_slug[slugify(rk)] = (rk, rv)

    boards = []
    unmatched_returns = set(returns)
    for name, rec in latest.items():
        slug = slugify(name)
        key = norm_key(name)
        ret = None
        hit_key = None
        if key in returns:
            ret = returns[key]
            hit_key = key
        elif slug in returns_by_slug:
            hit_key, ret = returns_by_slug[slug]
        else:
            for rk, rv in returns.items():
                if key in rk or rk in key:
                    ret = rv
                    hit_key = rk
                    break
        if hit_key:
            unmatched_returns.discard(hit_key)
        row = {
            "id": slug,
            "name": name,
            "valuation_year": rec["y"],
            "funded_pct": rec["funded_pct"],
            "funded_recomputed_pct": rec.get("funded_recomputed_pct"),
            "ual": rec["ual"],
            "aal": rec["aal"],
            "market_value": rec["market_value"],
            "active": rec["active"],
            "retired": rec["retired"],
            "avg_salary": rec["avg_salary"],
            "avg_benefit": rec["avg_benefit"],
            "arr_pct": rec["arr_pct"],
            "year_fully_funded": rec["year_fully_funded"],
            "grade": rec["grade"],
        }
        if ret:
            row.update(ret)
        boards.append(row)

    boards.sort(key=lambda b: (-(b["funded_pct"] or 0), b["name"]))
    for i, b in enumerate(boards, 1):
        b["rank"] = i
        b["n"] = len(boards)

    # Funded-ratio history for the page trend (one series per board).
    funded_history = {}
    for name, series in history.items():
        slug = slugify(name)
        # keep one point per year
        by_y = {}
        for rec in series:
            by_y[rec["y"]] = rec["funded_pct"]
        funded_history[slug] = [{"y": y, "v": by_y[y]} for y in sorted(by_y)]

    return boards, funded_history, unmatched_returns


def load_retirees(path: Path):
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=str(path)) as conn:
            t = list(conn.catalog.get_table_names("Extract"))[0]
            yearly_rows = conn.execute_list_query(
                f"""
                SELECT "Year", "Retirement_System",
                       COUNT(*),
                       SUM("Sum (Annual_Amount)"),
                       AVG("Sum (Annual_Amount)"),
                       MAX("Sum (Annual_Amount)")
                FROM {t}
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            )
            max_y = int(conn.execute_scalar_query(f'SELECT MAX("Year") FROM {t}'))
            top = conn.execute_list_query(
                f"""
                SELECT "Full_Name", "Retirement_System",
                       "Department_Last_Worked_In", "Title_At_Retirement",
                       "Date_Of_Retirement", "Sum (Annual_Amount)"
                FROM {t}
                WHERE "Year" = {max_y}
                ORDER BY "Sum (Annual_Amount)" DESC
                LIMIT 15
                """
            )
            depts = conn.execute_list_query(
                f"""
                SELECT "Retirement_System", "Department_Last_Worked_In",
                       COUNT(*), SUM("Sum (Annual_Amount)"),
                       AVG("Sum (Annual_Amount)")
                FROM {t}
                WHERE "Year" = {max_y}
                GROUP BY 1, 2
                ORDER BY SUM("Sum (Annual_Amount)") DESC
                LIMIT 15
                """
            )
            titles = conn.execute_list_query(
                f"""
                SELECT "Retirement_System", "Title_At_Retirement",
                       COUNT(*), SUM("Sum (Annual_Amount)"),
                       AVG("Sum (Annual_Amount)")
                FROM {t}
                WHERE "Year" = {max_y}
                  AND "Title_At_Retirement" IS NOT NULL
                  AND "Title_At_Retirement" <> 'N/A'
                GROUP BY 1, 2
                HAVING COUNT(*) >= 50
                ORDER BY AVG("Sum (Annual_Amount)") DESC
                LIMIT 15
                """
            )
            new_rows = conn.execute_list_query(
                f"""
                SELECT "Retirement_System", COUNT(*),
                       SUM("Sum (Annual_Amount)"), AVG("Sum (Annual_Amount)")
                FROM {t}
                WHERE "Year" = {max_y}
                  AND YEAR("Date_Of_Retirement") = {max_y}
                GROUP BY 1
                """
            )
            n_rows = int(conn.execute_scalar_query(f"SELECT COUNT(*) FROM {t}"))

    yearly = []
    by_year = defaultdict(lambda: {"year": None, "count": 0, "annual_amount": 0.0,
                                   "msers": None, "mtrs": None})
    for y, sysname, n, total, avg, mx in yearly_rows:
        y = int(y)
        rec = {
            "system": sysname,
            "count": int(n),
            "annual_amount": round(float(total), 2),
            "avg_amount": round(float(avg), 2),
            "max_amount": round(float(mx), 2),
        }
        slot = by_year[y]
        slot["year"] = y
        slot["count"] += rec["count"]
        slot["annual_amount"] += rec["annual_amount"]
        if sysname == "MSERS":
            slot["msers"] = rec
        elif sysname == "MTRS":
            slot["mtrs"] = rec
    for y in sorted(by_year):
        slot = by_year[y]
        slot["annual_amount"] = round(slot["annual_amount"], 2)
        slot["avg_amount"] = round(slot["annual_amount"] / slot["count"], 2)
        yearly.append(slot)

    def dstr(d):
        if d is None:
            return None
        return f"{int(d.year):04d}-{int(d.month):02d}-{int(d.day):02d}"

    top_pensions = []
    for name, sysname, dept, title, dt, amt in top:
        top_pensions.append({
            "name": name,
            "system": sysname,
            "department": dept,
            "title": None if title in (None, "N/A") else title,
            "retired": dstr(dt),
            "annual_amount": round(float(amt), 2),
        })

    departments = []
    for sysname, dept, n, total, avg in depts:
        departments.append({
            "system": sysname,
            "department": dept,
            "count": int(n),
            "annual_amount": round(float(total), 2),
            "avg_amount": round(float(avg), 2),
        })

    title_rows = []
    for sysname, title, n, total, avg in titles:
        title_rows.append({
            "system": sysname,
            "title": title,
            "count": int(n),
            "annual_amount": round(float(total), 2),
            "avg_amount": round(float(avg), 2),
        })

    new_by_system = {}
    new_count = 0
    new_amt = 0.0
    for sysname, n, total, avg in new_rows:
        new_by_system[sysname] = {
            "count": int(n),
            "annual_amount": round(float(total), 2),
            "avg_amount": round(float(avg), 2),
        }
        new_count += int(n)
        new_amt += float(total)

    latest = yearly[-1]
    return {
        "row_count": n_rows,
        "first_year": yearly[0]["year"],
        "latest_year": latest["year"],
        "yearly": yearly,
        "latest": {
            "year": latest["year"],
            "count": latest["count"],
            "annual_amount": latest["annual_amount"],
            "avg_amount": latest["avg_amount"],
            "msers": latest["msers"],
            "mtrs": latest["mtrs"],
            "new_retirees": {
                "count": new_count,
                "annual_amount": round(new_amt, 2),
                "by_system": new_by_system,
            },
        },
        "top_pensions": top_pensions,
        "departments": departments,
        "titles": title_rows,
    }


def pick(boards, slug):
    for b in boards:
        if b["id"] == slug:
            return b
    raise KeyError(slug)


def build(annual_path: Path, retirees_path: Path):
    boards, funded_history, unmatched = load_boards(annual_path)
    retirees = load_retirees(retirees_path)

    # Two-path funded-ratio check: published vs 1 - UAL/AAL.
    mismatches = []
    for b in boards:
        pub = b.get("funded_pct")
        rec = b.get("funded_recomputed_pct")
        if pub is None or rec is None:
            continue
        if abs(pub - rec) > 0.6:
            mismatches.append((b["id"], pub, rec))
    if mismatches:
        print("FUNDED RATIO MISMATCHES (>0.6 pp):")
        for row in mismatches:
            print(" ", row)
        sys.exit("FATAL: published funded ratio does not recompute from UAL/AAL")

    if unmatched:
        print("unmatched return rows (informational):", sorted(unmatched))

    state = pick(boards, "state")
    mtrs = pick(boards, "mtrs")
    boston_t = pick(boards, "boston-teachers")
    highest = boards[0]
    lowest = boards[-1]
    at_or_above_100 = [b for b in boards if (b["funded_pct"] or 0) >= 100]
    below_60 = [b for b in boards if (b["funded_pct"] or 0) < 60]

    total_ual = sum(b["ual"] or 0 for b in boards)
    total_aal = sum(b["aal"] or 0 for b in boards)
    # Dollar-weighted funded ratio across every board in the latest file.
    weighted_funded = round((1 - total_ual / total_aal) * 100, 1) if total_aal else None

    ret_1y = [b["return_1y_pct"] for b in boards if b.get("return_1y_pct") is not None]
    median_1y = sorted(ret_1y)[len(ret_1y) // 2] if ret_1y else None

    latest_r = retirees["latest"]
    first_r = retirees["yearly"][0]
    retiree_growth_pct = round(
        (latest_r["annual_amount"] / first_r["annual_amount"] - 1) * 100, 1
    )

    entities = {b["id"]: b["name"] for b in boards}

    ledger = {
        "tool_id": "DL-05",
        "as_of": "2024-12",
        "board_valuation_through": 2023,
        "returns_year": 2023,
        "retiree_year": retirees["latest_year"],
        "scope": (
            "Covers every Massachusetts public retirement board's latest PERAC "
            "actuarial valuation (funded ratio, unfunded liability, actuarial "
            "accrued liability, membership, average salary and benefit, assumed "
            "rate of return) and compiled investment returns (one-year, five-year, "
            "ten-year, and since-inception), plus the compiled State (MSERS) and "
            "Teachers (MTRS) retiree payroll for calendar years 2011 through the "
            "dataset retiree_year: yearly headcount and annual pension totals, "
            "department and title rankings, and the largest individual pensions. "
            "Does NOT cover: looking up a named retiree other than the published "
            "top pensions; municipal or local-board retiree names; retirement "
            "advice, benefit estimates, or what a member will receive; forecasts "
            "of funded status; other states' pension systems; or Commonwealth "
            "payroll and vendor payments."
        ),
        "vintage_note": (
            "Board funded status and membership are the latest PERAC actuarial "
            "valuation on file for each board in the compiled Performance extract "
            "(valuation dates January 1, 2021 through January 1, 2023; most boards "
            "are 2022 or 2023). Investment returns are the compiled PERAC returns "
            "file shipped with that extract; the one-year column is calendar 2023 "
            "(the extract still labels the column 2022; the +11 percent statewide "
            "print is the 2023 year). State and Teacher retiree figures are the "
            "CTHRU named-retiree file, calendar years 2011 through 2024, the same "
            "extract as the partner State & Teacher Retirees app. PERAC issued a "
            "2024 Investment Report (printed May 30, 2025) and has since updated "
            "the live funded-ratios table (through July 2, 2026); those newer "
            "prints are not yet in this ledger and are the next research-pass job. "
            "A stale 2012 'Boston' row that duplicated Boston City was dropped."
        ),
        "page": {"revised": "Aug 15, 2026", "version": "1.0"},
        "source_id_map": {
            "SRC-501": {
                "name": "PERAC retirement-board actuarial valuations",
                "url": "https://www.mass.gov/info-details/funded-ratios",
                "also": "https://www.mass.gov/lists/retirement-board-valuation-reports-perac",
                "cadence": "Each board at least every two years; PERAC posts a compiled funded-ratio table and an annual report",
                "supports": "Funded ratio, unfunded liability, actuarial accrued liability, membership, average salary and benefit, assumed rate of return, year fully funded",
            },
            "SRC-502": {
                "name": "PERAC Investment Report, compiled returns by board",
                "url": "https://www.mass.gov/lists/perac-investment-schedule-7-fee-reports",
                "cadence": "Annual, typically late spring for the prior calendar year",
                "supports": "One-year, five-year, ten-year, and since-inception investment returns",
                "note": "This ledger's one-year return is calendar 2023 from the compiled extract. The 2024 Investment Report is the next vintage.",
            },
            "SRC-503": {
                "name": "CTHRU State and Teachers Retirement Benefits",
                "url": "https://cthrupensions.mass.gov/",
                "publisher": "Office of the Comptroller",
                "cadence": "Annual named-retiree file for MSERS and MTRS",
                "supports": "Yearly retiree counts and annual pension totals, department and title rankings, largest pensions",
                "note": "Each row is a named retiree in one calendar year. Totals are the sum of annual amounts in that year, not a PERAC actuarial headcount (which also counts survivors and uses a January 1 census).",
            },
        },
        "entities": entities,
        "boards": boards,
        "funded_history": funded_history,
        "retirees": retirees,
        "latest": {
            "n_boards": len(boards),
            "valuation_years": {
                "2023": sum(1 for b in boards if b["valuation_year"] == 2023),
                "2022": sum(1 for b in boards if b["valuation_year"] == 2022),
                "2021": sum(1 for b in boards if b["valuation_year"] == 2021),
            },
            "state": {
                "id": "state",
                "name": state["name"],
                "funded_pct": state["funded_pct"],
                "valuation_year": state["valuation_year"],
                "ual": state["ual"],
                "aal": state["aal"],
                "active": state["active"],
                "retired": state["retired"],
                "return_1y_pct": state.get("return_1y_pct"),
                "return_10y_pct": state.get("return_10y_pct"),
                "rank": state["rank"],
            },
            "mtrs": {
                "id": "mtrs",
                "name": mtrs["name"],
                "funded_pct": mtrs["funded_pct"],
                "valuation_year": mtrs["valuation_year"],
                "ual": mtrs["ual"],
                "aal": mtrs["aal"],
                "active": mtrs["active"],
                "retired": mtrs["retired"],
                "return_1y_pct": mtrs.get("return_1y_pct"),
                "return_10y_pct": mtrs.get("return_10y_pct"),
                "rank": mtrs["rank"],
            },
            "boston_teachers": {
                "id": "boston-teachers",
                "name": boston_t["name"],
                "funded_pct": boston_t["funded_pct"],
                "valuation_year": boston_t["valuation_year"],
                "ual": boston_t["ual"],
                "rank": boston_t["rank"],
            },
            "highest": {
                "id": highest["id"],
                "name": highest["name"],
                "funded_pct": highest["funded_pct"],
                "valuation_year": highest["valuation_year"],
            },
            "lowest": {
                "id": lowest["id"],
                "name": lowest["name"],
                "funded_pct": lowest["funded_pct"],
                "valuation_year": lowest["valuation_year"],
            },
            "weighted_funded_pct": weighted_funded,
            "total_ual": total_ual,
            "total_aal": total_aal,
            "n_at_or_above_100": len(at_or_above_100),
            "n_below_60": len(below_60),
            "median_return_1y_pct": median_1y,
            "retirees": {
                "year": latest_r["year"],
                "count": latest_r["count"],
                "annual_amount": latest_r["annual_amount"],
                "avg_amount": latest_r["avg_amount"],
                "msers_count": latest_r["msers"]["count"],
                "msers_annual_amount": latest_r["msers"]["annual_amount"],
                "mtrs_count": latest_r["mtrs"]["count"],
                "mtrs_annual_amount": latest_r["mtrs"]["annual_amount"],
            },
        },
        "derived": {
            "note": "Prefer these precomputed values over your own arithmetic.",
            "n_boards": len(boards),
            "n_at_or_above_100": len(at_or_above_100),
            "at_or_above_100": [
                {"id": b["id"], "name": b["name"], "funded_pct": b["funded_pct"]}
                for b in at_or_above_100
            ],
            "n_below_60": len(below_60),
            "below_60": [
                {"id": b["id"], "name": b["name"], "funded_pct": b["funded_pct"]}
                for b in below_60
            ],
            "highest_five": [
                {"id": b["id"], "name": b["name"], "funded_pct": b["funded_pct"]}
                for b in boards[:5]
            ],
            "lowest_five": [
                {"id": b["id"], "name": b["name"], "funded_pct": b["funded_pct"]}
                for b in boards[-5:][::-1]
            ],
            "state_funded_pct": state["funded_pct"],
            "mtrs_funded_pct": mtrs["funded_pct"],
            "boston_teachers_funded_pct": boston_t["funded_pct"],
            "weighted_funded_pct": weighted_funded,
            "total_ual": total_ual,
            "state_ual": state["ual"],
            "mtrs_ual": mtrs["ual"],
            "commonwealth_ual": state["ual"] + mtrs["ual"] + boston_t["ual"],
            "state_rank": state["rank"],
            "mtrs_rank": mtrs["rank"],
            "median_return_1y_pct": median_1y,
            "state_return_1y_pct": state.get("return_1y_pct"),
            "mtrs_return_1y_pct": mtrs.get("return_1y_pct"),
            "retiree_year": latest_r["year"],
            "retiree_count": latest_r["count"],
            "retiree_annual_amount": latest_r["annual_amount"],
            "retiree_avg_amount": latest_r["avg_amount"],
            "retiree_amount_change_from_2011_pct": retiree_growth_pct,
            "largest_pension": {
                "name": retirees["top_pensions"][0]["name"],
                "system": retirees["top_pensions"][0]["system"],
                "annual_amount": retirees["top_pensions"][0]["annual_amount"],
            },
            "new_retirees_2024": latest_r["new_retirees"]["count"],
        },
        "pending": [
            {
                "id": "PERAC-2024-IR",
                "what": "Transcribe the PERAC 2024 Investment Report (printed May 30, 2025) and the live funded-ratios table (updated July 2, 2026) so board funded ratios and returns move off the 2022/2023 extract.",
                "plan": "scripts/dl05-research-pass.md",
            },
            {
                "id": "CTHRU-VS-PERAC-HEADCOUNT",
                "what": "CTHRU 2023 MSERS annual-amount sum is $2.784 billion across 64,384 named retirees; an MSRB retiree bulletin cited $2.934 billion in total benefits issued for 2023 and 69,750 benefit recipients as of January 1, 2024. Different universes (named CTHRU payroll vs actuarial recipients including survivors). Do not treat them as the same cell.",
                "plan": "Keep CTHRU as the retiree-payroll source; cite PERAC/MSRB headcounts only when the valuation report is the source.",
            },
        ],
        "verification": {
            "funded_ratio": (
                "For every board, funded_pct equals 1 minus unfunded liability "
                "divided by actuarial accrued liability, within 0.6 percentage "
                "points (UAL and AAL in the extract are rounded, so a 0.1 to 0.5 "
                "point gap is expected on small boards). build_dl05.py fails if "
                "any board exceeds that band."
            ),
            "retiree_yearly": (
                "Yearly MSERS and MTRS counts and annual-amount sums are "
                "recomputed from the 1,694,037-row CTHRU extract. Combined 2024: "
                "134,205 named retirees and $6.407 billion in annual pensions."
            ),
            "twbx": (
                "Board cells match the MA_Pensions_Annual extract; retiree "
                "aggregates match the MA_Pensions_Retirees extract. The TWBX "
                "files are verification inputs and are not committed."
            ),
        },
    }
    return ledger


def main():
    annual = Path(os.environ.get("DL05_ANNUAL_HYPER", ANNUAL_DEFAULT))
    retirees = Path(os.environ.get("DL05_RETIREES_HYPER", RETIREES_DEFAULT))
    if not annual.exists():
        sys.exit(f"missing annual hyper: {annual}")
    if not retirees.exists():
        sys.exit(f"missing retirees hyper: {retirees}")
    ledger = build(annual, retirees)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(
        json.dumps(ledger, ensure_ascii=True, indent=1) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {LEDGER}  boards={ledger['latest']['n_boards']}  "
        f"state={ledger['latest']['state']['funded_pct']}%  "
        f"mtrs={ledger['latest']['mtrs']['funded_pct']}%  "
        f"retirees={ledger['latest']['retirees']['count']:,}  "
        f"${ledger['latest']['retirees']['annual_amount']:,.0f}"
    )


if __name__ == "__main__":
    main()
