#!/usr/bin/env python3
"""Build suite ledgers from public files, and stub apps whose files are blocked.

First-wave live builders live in this file (DL-13, 14, 16, 17). The rest of
the live suite is in suite_builders.py. Apps without a reachable primary
file stay honest stubs. Never invents figures. Never pushes to main.
Re-runs render_suite_pages.py and inject_data.py.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_common import (
    FIPS_TO_ST,
    MONTHS,
    MONTH_ABBR,
    RANKED,
    REVISED,
    ROOT,
    STATE_NAMES,
    ST_TO_FIPS,
    base_ledger,
    commify,
    fetch_text,
    ledger_path,
    load_apps,
    pct,
    rank_rows,
    stub_ledger,
    write_ledger,
    yoy_pct,
)
from suite_builders import BUILDERS as EXTRA_BUILDERS
from suite_later import BUILDERS as LATER_BUILDERS, enrich

TODAY = date(2026, 8, 15)

URL_BFS = "https://www.census.gov/econ/bfs/csv/bfs_monthly.csv"
URL_LAUS = "https://download.bls.gov/pub/time.series/la/la.data.3.AllStatesS"
URL_PEP = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2020-2025/state/totals/NST-EST2025-ALLDATA.csv"
)
URL_BPS = "https://www2.census.gov/econ/bps/State/st{yy}{mm}y.txt"

# Press-release two-path check: Census CB26-130, August 12, 2026.
BFS_VERIFY_US_JUL_2026 = 578926


def app_by_id(apps, tool_id):
    for a in apps:
        if a["id"] == tool_id:
            return a
    raise KeyError(tool_id)


def latest_month_row(row):
    """Return (month_index_1, value) for the last non-empty month in a BFS row."""
    last = None
    for i, key in enumerate(MONTHS, 1):
        raw = (row.get(key) or "").strip()
        if raw:
            last = (i, int(float(raw)))
    return last


def build_bfs(app):
    text = fetch_text(URL_BFS)
    rows = list(csv.DictReader(io.StringIO(text)))
    us_2026 = None
    by_geo = {}
    for r in rows:
        if r["sa"] != "A" or r["naics_sector"] != "TOTAL" or r["series"] != "BA_BA":
            continue
        geo = r["geo"]
        if geo not in STATE_NAMES:
            continue
        year = int(r["year"])
        by_geo.setdefault(geo, {})[year] = r
        if geo == "US" and year == 2026:
            us_2026 = r
    if not us_2026:
        sys.exit("FATAL: BFS missing US 2026 seasonally adjusted BA_BA")
    latest = latest_month_row(us_2026)
    if not latest:
        sys.exit("FATAL: BFS US 2026 has no monthly values")
    month_i, us_val = latest
    if month_i == 7 and us_val != BFS_VERIFY_US_JUL_2026:
        sys.exit(
            f"FATAL: BFS US July 2026 SA applications are {us_val}, "
            f"expected {BFS_VERIFY_US_JUL_2026} (Census CB26-130)"
        )
    year = 2026
    month_key = MONTHS[month_i - 1]
    values = {}
    prev_values = {}
    for st, years in by_geo.items():
        cur = years.get(year)
        if not cur:
            continue
        raw = (cur.get(month_key) or "").strip()
        if raw:
            values[st] = int(float(raw))
        # prior year, same month
        prev = years.get(year - 1)
        if prev:
            praw = (prev.get(month_key) or "").strip()
            if praw:
                prev_values[st] = int(float(praw))
    ranked = rank_rows(values, higher_is_better=True)
    for rec in ranked:
        rec["yoy_pct"] = yoy_pct(rec["v"], prev_values.get(rec["st"]))
    ma = next(r for r in ranked if r["st"] == "MA")
    us_yoy = yoy_pct(values["US"], prev_values.get("US"))
    # monthly US trend, seasonally adjusted, last 8 years
    trend = {"US": [], "MA": []}
    for st in ("US", "MA"):
        for y in sorted(by_geo.get(st, {})):
            if y < 2018:
                continue
            row = by_geo[st][y]
            for i, key in enumerate(MONTHS, 1):
                raw = (row.get(key) or "").strip()
                if not raw:
                    continue
                trend[st].append({"m": f"{y}-{i:02d}", "v": int(float(raw))})
    as_of = f"{year}-{month_i:02d}"
    as_of_label = f"{MONTH_ABBR[month_i]} {year}"
    kpis = [
        {
            "label": f"U.S. applications, {as_of_label}",
            "value": commify(us_val),
            "detail": (
                f"Seasonally adjusted business applications (SRC-613-01). "
                f"{pct(us_yoy)} from {MONTH_ABBR[month_i]} {year - 1}."
            ),
            "why": "This is the national count the rest of the page is measured against.",
            "src": "Census BFS monthly time series (SRC-613-01)",
        },
        {
            "label": "Massachusetts",
            "value": commify(ma["v"]),
            "detail": (
                f"Rank {ma['rank']} of {ma['n']} (derived, SRC-613-01). "
                f"{pct(ma['yoy_pct'])} from {MONTH_ABBR[month_i]} {year - 1}."
            ),
            "why": "Massachusetts applications against the other 50 jurisdictions.",
            "src": "Census BFS monthly time series (SRC-613-01)",
        },
        {
            "label": "Highest / lowest",
            "value": f"{ranked[0]['st']} {commify(ranked[0]['v'])}",
            "detail": (
                f"{ranked[0]['name']} filed the most applications; "
                f"{ranked[-1]['name']} the fewest at {commify(ranked[-1]['v'])} "
                f"(SRC-613-01)."
            ),
            "why": "Large states lead on raw counts; the table also shows the rank.",
            "src": "Census BFS monthly time series (SRC-613-01)",
        },
    ]
    lead = (
        f"Seasonally adjusted business applications were <b>{commify(us_val)}</b> "
        f"in {as_of_label}, {pct(us_yoy)} from a year earlier (SRC-613-01). "
        f"Massachusetts filed <b>{commify(ma['v'])}</b>, rank {ma['rank']} of "
        f"{ma['n']} (derived, SRC-613-01)."
    )
    return base_ledger(
        app,
        "live",
        as_of,
        (
            f"Rebuilt {REVISED} from the Census BFS monthly CSV. "
            f"Headline series is seasonally adjusted BA_BA, TOTAL NAICS. "
            f"U.S. {as_of_label} equals {BFS_VERIFY_US_JUL_2026:,}, matching "
            f"Census press release CB26-130 (August 12, 2026)."
        ),
        {
            "pending": False,
            "metric": "seasonally_adjusted_business_applications",
            "metric_label": "Business applications (seasonally adjusted)",
            "unit": "applications",
            "data_month": as_of,
            "data_month_label": as_of_label,
            "lead": lead,
            "kpis": kpis,
            "latest": {
                "us": {"v": us_val, "yoy_pct": us_yoy},
                "ma": {"v": ma["v"], "rank": ma["rank"], "n": ma["n"], "yoy_pct": ma["yoy_pct"]},
                "highest": {"st": ranked[0]["st"], "name": ranked[0]["name"], "v": ranked[0]["v"]},
                "lowest": {"st": ranked[-1]["st"], "name": ranked[-1]["name"], "v": ranked[-1]["v"]},
            },
            "rows": ranked,
            "trend": trend,
            "derived": {
                "note": "Prefer these over recomputing. All ranks cite (derived, SRC-613-01).",
                "highest_five": ranked[:5],
                "lowest_five": list(reversed(ranked[-5:])),
                "massachusetts_rank": ma["rank"],
                "n_ranked": ma["n"],
            },
        },
    )


def parse_laus(text):
    """Return {(st, year, month): rate} for statewide SA unemployment rates."""
    out = {}
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        sid = parts[0].strip()
        # LASST + 2-digit FIPS + 0000000000003 = SA unemployment rate
        if not (sid.startswith("LASST") and sid.endswith("0000000000003") and len(sid) == 20):
            continue
        fips = sid[5:7]
        st = FIPS_TO_ST.get(fips)
        if not st or st == "US":
            continue
        year = int(parts[1].strip())
        period = parts[2].strip()
        if not period.startswith("M"):
            continue
        month = int(period[1:])
        raw = parts[3].strip()
        if raw in ("", "-"):
            continue
        out[(st, year, month)] = float(raw)
    return out


def build_laus(app):
    text = fetch_text(URL_LAUS, timeout=120)
    series = parse_laus(text)
    if not series:
        sys.exit("FATAL: LAUS parse produced no statewide rates")
    latest_ym = max((y, m) for (_st, y, m) in series)
    year, month = latest_ym
    values = {st: series[(st, year, month)] for st in RANKED if (st, year, month) in series}
    if len(values) < 51:
        sys.exit(f"FATAL: LAUS {year}-{month:02d} has {len(values)} states, expected 51")
    for st, v in values.items():
        if not (0 < v < 30):
            sys.exit(f"FATAL: LAUS {st} {year}-{month:02d} rate {v} is outside 0-30")
    prev = {st: series.get((st, year - 1, month)) for st in values}
    # lower unemployment is "better" for ranking? For a data page, rank highest rate first
    # so the chart shows the problem ranking, matching typical Pioneer presentation.
    ranked = rank_rows(values, higher_is_better=True)
    for rec in ranked:
        rec["yoy_pct"] = yoy_pct(rec["v"], prev.get(rec["st"]))
        rec["v"] = rec["v"]  # already a rate
    ma = next(r for r in ranked if r["st"] == "MA")
    us_rate = None
    # US is not in LAUS statewide file; leave it out of the rank and note it.
    trend = {"MA": []}
    for (st, y, m), v in sorted(series.items()):
        if st == "MA" and y >= 2018:
            trend["MA"].append({"m": f"{y}-{m:02d}", "v": v})
    as_of = f"{year}-{month:02d}"
    as_of_label = f"{MONTH_ABBR[month]} {year}"
    kpis = [
        {
            "label": f"Massachusetts, {as_of_label}",
            "value": f"{ma['v']:.1f}%",
            "detail": (
                f"Seasonally adjusted unemployment rate, rank {ma['rank']} of "
                f"{ma['n']} (highest rate is rank 1) (derived, SRC-614-01). "
                f"{pct(ma['yoy_pct'])} from {MONTH_ABBR[month]} {year - 1}."
            ),
            "why": "The Massachusetts rate against the other 50 jurisdictions.",
            "src": "BLS LAUS statewide seasonally adjusted (SRC-614-01)",
        },
        {
            "label": "Highest rate",
            "value": f"{ranked[0]['st']} {ranked[0]['v']:.1f}%",
            "detail": f"{ranked[0]['name']} had the highest statewide rate (SRC-614-01).",
            "why": "The top of the ranking is the weakest labor-market print that month.",
            "src": "BLS LAUS statewide seasonally adjusted (SRC-614-01)",
        },
        {
            "label": "Lowest rate",
            "value": f"{ranked[-1]['st']} {ranked[-1]['v']:.1f}%",
            "detail": f"{ranked[-1]['name']} had the lowest statewide rate (SRC-614-01).",
            "why": "The bottom of the ranking is the tightest statewide print that month.",
            "src": "BLS LAUS statewide seasonally adjusted (SRC-614-01)",
        },
    ]
    lead = (
        f"Massachusetts seasonally adjusted unemployment was <b>{ma['v']:.1f} percent</b> "
        f"in {as_of_label}, rank {ma['rank']} of {ma['n']} when states are ordered "
        f"from highest rate to lowest (derived, SRC-614-01). "
        f"{ranked[0]['name']} was highest at {ranked[0]['v']:.1f} percent; "
        f"{ranked[-1]['name']} was lowest at {ranked[-1]['v']:.1f} percent (SRC-614-01)."
    )
    return base_ledger(
        app,
        "live",
        as_of,
        (
            f"Rebuilt {REVISED} from BLS LAUS statewide seasonally adjusted file "
            f"la.data.3.AllStatesS. Measure 03 is the unemployment rate. "
            f"The U.S. civilian rate is not in this file and is not invented here."
        ),
        {
            "pending": False,
            "metric": "unemployment_rate_sa",
            "metric_label": "Unemployment rate (seasonally adjusted)",
            "unit": "percent",
            "data_month": as_of,
            "data_month_label": as_of_label,
            "lead": lead,
            "kpis": kpis,
            "latest": {
                "us": None,
                "ma": {"v": ma["v"], "rank": ma["rank"], "n": ma["n"], "yoy_pct": ma["yoy_pct"]},
                "highest": {"st": ranked[0]["st"], "name": ranked[0]["name"], "v": ranked[0]["v"]},
                "lowest": {"st": ranked[-1]["st"], "name": ranked[-1]["name"], "v": ranked[-1]["v"]},
            },
            "rows": ranked,
            "trend": trend,
            "derived": {
                "note": "Prefer these over recomputing. Ranks cite (derived, SRC-614-01).",
                "highest_five": ranked[:5],
                "lowest_five": list(reversed(ranked[-5:])),
                "massachusetts_rank": ma["rank"],
                "n_ranked": ma["n"],
            },
        },
    )


def parse_bps(text):
    """Year-to-date authorized units by state FIPS from a BPS state YTD file."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        # Date is YYYYMM in column 0; FIPS in column 1; name in column 4.
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 17:
            continue
        fips = parts[1].zfill(2)
        st = FIPS_TO_ST.get(fips)
        if not st or st == "US":
            continue
        try:
            u1 = int(parts[6] or 0)
            u2 = int(parts[9] or 0)
            u34 = int(parts[12] or 0)
            u5 = int(parts[15] or 0)
        except ValueError:
            continue
        values[st] = u1 + u2 + u34 + u5
    return values


def build_bps(app):
    # Latest complete YTD month on disk around mid-August 2026 is June 2026.
    year, month = 2026, 6
    cur_text = fetch_text(URL_BPS.format(yy=f"{year % 100:02d}", mm=f"{month:02d}"))
    prev_text = fetch_text(URL_BPS.format(yy=f"{(year - 1) % 100:02d}", mm=f"{month:02d}"))
    values = parse_bps(cur_text)
    prev = parse_bps(prev_text)
    if len(values) < 50:
        sys.exit(f"FATAL: BPS {year}-{month:02d} parsed {len(values)} states")
    ranked = rank_rows(values, higher_is_better=True)
    for rec in ranked:
        rec["yoy_pct"] = yoy_pct(rec["v"], prev.get(rec["st"]))
    ma = next(r for r in ranked if r["st"] == "MA")
    us_val = sum(values.values())
    us_prev = sum(prev.get(st, 0) for st in values)
    us_yoy = yoy_pct(us_val, us_prev)
    as_of = f"{year}-{month:02d}"
    as_of_label = f"{MONTH_ABBR[month]} {year} year-to-date"
    kpis = [
        {
            "label": f"U.S. units, {as_of_label}",
            "value": commify(us_val),
            "detail": (
                f"Authorized units in permit-issuing places, all structures, "
                f"sum of the 50 states and D.C. (derived, SRC-616-01). "
                f"{pct(us_yoy)} from the same months of {year - 1}."
            ),
            "why": "This is the production count behind the housing conversation.",
            "src": "Census Building Permits Survey state YTD file (SRC-616-01)",
        },
        {
            "label": "Massachusetts",
            "value": commify(ma["v"]),
            "detail": (
                f"Rank {ma['rank']} of {ma['n']} (derived, SRC-616-01). "
                f"{pct(ma['yoy_pct'])} from the same months of {year - 1}."
            ),
            "why": "Massachusetts permit volume against the other jurisdictions.",
            "src": "Census Building Permits Survey state YTD file (SRC-616-01)",
        },
        {
            "label": "Highest / lowest",
            "value": f"{ranked[0]['st']} {commify(ranked[0]['v'])}",
            "detail": (
                f"{ranked[0]['name']} authorized the most units; "
                f"{ranked[-1]['name']} the fewest at {commify(ranked[-1]['v'])} "
                f"(SRC-616-01)."
            ),
            "why": "Large, fast-growing states lead on raw unit counts.",
            "src": "Census Building Permits Survey state YTD file (SRC-616-01)",
        },
    ]
    lead = (
        f"Permit-issuing places authorized <b>{commify(us_val)}</b> housing units "
        f"in the United States through {MONTH_ABBR[month]} {year}, {pct(us_yoy)} "
        f"from the same months of {year - 1} (derived, SRC-616-01). Massachusetts "
        f"authorized <b>{commify(ma['v'])}</b>, rank {ma['rank']} of {ma['n']} "
        f"(derived, SRC-616-01)."
    )
    return base_ledger(
        app,
        "live",
        as_of,
        (
            f"Rebuilt {REVISED} from Census BPS state year-to-date files "
            f"st{year % 100:02d}{month:02d}y.txt and the matching {year - 1} file. "
            f"Units are 1-unit + 2-unit + 3-4 unit + 5-or-more, reported buildings' "
            f"units columns. The U.S. total is the sum of published state rows, "
            f"not a separate Census U.S. line."
        ),
        {
            "pending": False,
            "metric": "housing_units_authorized_ytd",
            "metric_label": "Housing units authorized (year-to-date)",
            "unit": "units",
            "data_month": as_of,
            "data_month_label": as_of_label,
            "lead": lead,
            "kpis": kpis,
            "latest": {
                "us": {"v": us_val, "yoy_pct": us_yoy},
                "ma": {"v": ma["v"], "rank": ma["rank"], "n": ma["n"], "yoy_pct": ma["yoy_pct"]},
                "highest": {"st": ranked[0]["st"], "name": ranked[0]["name"], "v": ranked[0]["v"]},
                "lowest": {"st": ranked[-1]["st"], "name": ranked[-1]["name"], "v": ranked[-1]["v"]},
            },
            "rows": ranked,
            "trend": {},
            "derived": {
                "note": "Prefer these over recomputing. Ranks and the U.S. sum cite (derived, SRC-616-01).",
                "highest_five": ranked[:5],
                "lowest_five": list(reversed(ranked[-5:])),
                "massachusetts_rank": ma["rank"],
                "n_ranked": ma["n"],
                "us_sum_of_states": us_val,
            },
        },
    )


def build_pep(app):
    text = fetch_text(URL_PEP)
    rows = list(csv.DictReader(io.StringIO(text)))
    pop = {}
    mig = {}
    names = {}
    us_pop = us_mig = None
    for r in rows:
        name = r["NAME"]
        p = int(r["POPESTIMATE2025"])
        d = int(r["DOMESTICMIG2025"])
        if name == "United States":
            us_pop, us_mig = p, d
            continue
        # skip regions and divisions
        if r["SUMLEV"] != "040":
            continue
        # map name to postal
        st = next((k for k, v in STATE_NAMES.items() if v == name), None)
        if not st:
            continue
        pop[st] = p
        mig[st] = d
        names[st] = name
    if us_pop is None or len(pop) < 51:
        sys.exit(f"FATAL: PEP parsed {len(pop)} states, US pop {us_pop}")
    ranked = rank_rows(mig, higher_is_better=True)
    for rec in ranked:
        rec["pop"] = pop[rec["st"]]
        rec["mig_per_1k"] = round(rec["v"] / pop[rec["st"]] * 1000, 2)
    ma = next(r for r in ranked if r["st"] == "MA")
    as_of = "2025-07"
    kpis = [
        {
            "label": "U.S. population, July 1, 2025",
            "value": commify(us_pop),
            "detail": "Census vintage 2025 estimate (SRC-617-01).",
            "why": "The national stock the state rows add up to.",
            "src": "Census vintage 2025 state population estimates (SRC-617-01)",
        },
        {
            "label": "Massachusetts population",
            "value": commify(pop["MA"]),
            "detail": (
                f"Domestic migration {commify(ma['v'])} in 2025, rank {ma['rank']} "
                f"of {ma['n']} (derived, SRC-617-01)."
            ),
            "why": "The stock and the domestic flow, which is the competitiveness number.",
            "src": "Census vintage 2025 state population estimates (SRC-617-01)",
        },
        {
            "label": "Largest domestic inflow",
            "value": f"{ranked[0]['st']} {commify(ranked[0]['v'])}",
            "detail": (
                f"{ranked[0]['name']} gained the most residents from other states; "
                f"{ranked[-1]['name']} lost the most at {commify(ranked[-1]['v'])} "
                f"(SRC-617-01)."
            ),
            "why": "Domestic migration is a zero-sum ranking across the 50 states and D.C.",
            "src": "Census vintage 2025 state population estimates (SRC-617-01)",
        },
    ]
    lead = (
        f"The Census vintage 2025 estimate put the United States at "
        f"<b>{commify(us_pop)}</b> on July 1, 2025 (SRC-617-01). Massachusetts "
        f"was <b>{commify(pop['MA'])}</b>, with domestic migration of "
        f"<b>{commify(ma['v'])}</b>, rank {ma['rank']} of {ma['n']} "
        f"(derived, SRC-617-01)."
    )
    # population trend 2020-2025
    trend = {"US": [], "MA": []}
    us_row = next(r for r in rows if r["NAME"] == "United States")
    ma_row = next(r for r in rows if r["NAME"] == "Massachusetts")
    for y in range(2020, 2026):
        trend["US"].append({"y": y, "v": int(us_row[f"POPESTIMATE{y}"])})
        trend["MA"].append({"y": y, "v": int(ma_row[f"POPESTIMATE{y}"])})
    return base_ledger(
        app,
        "live",
        as_of,
        (
            f"Rebuilt {REVISED} from Census vintage 2025 NST-EST2025-ALLDATA. "
            f"Population is POPESTIMATE2025 (July 1). The ranking is "
            f"DOMESTICMIG2025, not total population."
        ),
        {
            "pending": False,
            "metric": "domestic_migration_2025",
            "metric_label": "Domestic migration, 2025",
            "unit": "people",
            "data_month": as_of,
            "data_month_label": "July 1, 2025",
            "lead": lead,
            "kpis": kpis,
            "latest": {
                "us": {"pop": us_pop, "domestic_mig": us_mig},
                "ma": {
                    "pop": pop["MA"],
                    "v": ma["v"],
                    "rank": ma["rank"],
                    "n": ma["n"],
                    "mig_per_1k": ma["mig_per_1k"],
                },
                "highest": {"st": ranked[0]["st"], "name": ranked[0]["name"], "v": ranked[0]["v"]},
                "lowest": {"st": ranked[-1]["st"], "name": ranked[-1]["name"], "v": ranked[-1]["v"]},
            },
            "rows": ranked,
            "trend": trend,
            "derived": {
                "note": "Prefer these over recomputing. Ranks cite (derived, SRC-617-01).",
                "highest_five": ranked[:5],
                "lowest_five": list(reversed(ranked[-5:])),
                "massachusetts_rank": ma["rank"],
                "n_ranked": ma["n"],
            },
        },
    )


BUILDERS = {
    "DL-13": build_bfs,
    "DL-14": build_laus,
    "DL-16": build_bps,
    "DL-17": build_pep,
}
BUILDERS.update(EXTRA_BUILDERS)
BUILDERS.update(LATER_BUILDERS)


def upsert_catalog(apps):
    path = ROOT / "catalog.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    by_id = {row.get("id"): i for i, row in enumerate(catalog)}
    insert_i = len(catalog)
    for app in apps:
        ledger = json.loads(ledger_path(app["id"]).read_text())
        vint = ""
        if ledger.get("status") == "live" and ledger.get("data_month_label"):
            vint = ledger["data_month_label"]
        elif ledger.get("status") == "build":
            vint = "in build"
        entry = {
            "id": app["id"],
            "t": app["title"],
            "q": app["q"],
            "g": app["g"],
            "st": "live" if ledger.get("status") == "live" else "build",
            "url": f"/{app['slug']}/",
            "ai": ledger.get("status") == "live",
            "heritage": app["heritage"],
            "group": app["group"],
            "vint": vint,
        }
        if app["id"] in by_id:
            catalog[by_id[app["id"]]] = entry
        else:
            catalog.insert(insert_i, entry)
            insert_i += 1
            by_id = {row.get("id"): i for i, row in enumerate(catalog)}
    path.write_text(json.dumps(catalog, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")


def main():
    apps = load_apps()
    if len(apps) != 26:
        sys.exit(f"FATAL: suite/apps.json has {len(apps)} apps, expected 26")
    for app in apps:
        tool = app["id"]
        if tool in BUILDERS:
            print(f"refresh {tool} {app['title']} ...")
            ledger = BUILDERS[tool](app)
            ledger = enrich(app, ledger)
        else:
            print(f"stub    {tool} {app['title']}")
            ledger = stub_ledger(app)
        path = write_ledger(ledger)
        print(f"  wrote {path.relative_to(ROOT)} status={ledger['status']} as_of={ledger.get('as_of')}")
    upsert_catalog(apps)
    print("catalog.json updated")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "render_suite_pages.py")])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "inject_data.py")])


if __name__ == "__main__":
    main()
