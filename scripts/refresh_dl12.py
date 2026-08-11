#!/usr/bin/env python3
"""Refresh the DL-12 MBTA ridership ledger from the FTA NTD Socrata API.

Source: Complete Monthly Ridership (with adjustments and estimates),
dataset 8bui-9xvu on data.transportation.gov, ntd_id 10003 (MBTA).
This is the same source and agency id the ledger was verified against.

Recomputes every ridership-derived field (monthly totals, annual by mode,
latest month, recovery vs 2019, YoY, derived rollups) and the verified
cost/farebox series from NTD Annual Metrics (dataset ekg5-frzt, SRC-302):
operating expenses per unlinked trip and fare revenues over operating
expenses, by mode and report year.

Writes netlify/functions/dl12-answers.json and re-runs inject_data.py so
every embedded copy follows. Designed to run in CI and open a PR: it
never pushes to main itself, and a human reviews the diff (the NTD
occasionally revises history; the diff is where that shows up).

Exits nonzero when the fetched data fails sanity checks.
"""
import json
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "netlify/functions/dl12-answers.json"
API = "https://data.transportation.gov/resource/8bui-9xvu.json"
METRICS_API = "https://data.transportation.gov/resource/ekg5-frzt.json"
NTD_ID = "10003"


def fetch_rows():
    rows, offset, limit = [], 0, 50000
    while True:
        url = f"{API}?ntd_id={NTD_ID}&$limit={limit}&$offset={offset}"
        with urllib.request.urlopen(url, timeout=120) as r:
            page = json.load(r)
        rows.extend(page)
        if len(page) < limit:
            return rows
        offset += limit


def fetch_metrics():
    url = f"{METRICS_API}?ntd_id={NTD_ID}&$limit=500"
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def month_key(iso):
    return iso[:7]  # "2026-06-01T00:00:00.000" -> "2026-06"


MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def main():
    old = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = fetch_rows()
    if len(rows) < 1000:
        sys.exit(f"FATAL: only {len(rows)} rows fetched; expected thousands")

    monthly = defaultdict(int)              # "YYYY-MM" -> total upt
    annual_mode = defaultdict(lambda: defaultdict(int))  # year -> mode -> upt
    latest_mode = defaultdict(int)
    for r in rows:
        upt = int(float(r.get("upt") or 0))
        if upt <= 0:
            continue
        mk = month_key(r["date"])
        monthly[mk] += upt
        annual_mode[mk[:4]][r["mode"]] += upt

    months = sorted(monthly)
    months = [m for m in months if m >= "2014-01"]  # ledger series starts 2014
    if not months:
        sys.exit("FATAL: no months after 2014-01")
    as_of = months[-1]

    # ---- sanity checks ----
    # continuity: no missing month in the series
    y, m = map(int, months[0].split("-"))
    for mk in months:
        want = f"{y:04d}-{m:02d}"
        if mk != want:
            sys.exit(f"FATAL: month gap, expected {want}, found {mk}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    # never move backwards
    if as_of < old["as_of"]:
        sys.exit(f"FATAL: fetched as_of {as_of} is older than ledger {old['as_of']}")
    # totals look like the MBTA (tens of millions in normal months)
    if not (1_000_000 < monthly[as_of] < 60_000_000):
        sys.exit(f"FATAL: implausible latest-month total {monthly[as_of]}")

    # latest month by-mode split
    for r in rows:
        if month_key(r["date"]) == as_of:
            upt = int(float(r.get("upt") or 0))
            if upt > 0:
                latest_mode[r["mode"]] += upt

    # recovery vs same month 2019, per mode and total
    base_month = "2019-" + as_of[5:]
    base_mode = defaultdict(int)
    for r in rows:
        if month_key(r["date"]) == base_month:
            upt = int(float(r.get("upt") or 0))
            if upt > 0:
                base_mode[r["mode"]] += upt
    if not base_mode:
        sys.exit(f"FATAL: no baseline data for {base_month}")
    recovery = {"TOTAL": round(100 * monthly[as_of] / monthly[base_month], 1)}
    for mode, v in latest_mode.items():
        if base_mode.get(mode):
            recovery[mode] = round(100 * v / base_mode[mode], 1)

    # YoY change
    prev_year_month = f"{int(as_of[:4]) - 1}-{as_of[5:]}"
    yoy = round(100 * (monthly[as_of] / monthly[prev_year_month] - 1), 1) if monthly.get(prev_year_month) else None

    # ---- assemble the new ledger ----
    new = dict(old)
    new["as_of"] = as_of
    new["monthly_total_upt"] = [{"m": mk, "v": monthly[mk]} for mk in months]
    # annual by mode: full years only, matching the ledger's existing style of
    # including the current partial year is avoided (old ledger stops at last full year)
    last_full_year = as_of[:4] if as_of.endswith("-12") else str(int(as_of[:4]) - 1)
    new["annual_upt_by_mode"] = {
        yr: dict(sorted(annual_mode[yr].items()))
        for yr in sorted(annual_mode) if "2014" <= yr <= last_full_year
    }
    new["latest_month"] = {
        "month": as_of,
        "total_upt": monthly[as_of],
        "by_mode": dict(sorted(latest_mode.items())),
    }
    new["recovery_vs_2019_same_month_pct"] = recovery
    new["recovery_baseline"] = "Same month 2019 (" + MONTH_NAMES[int(as_of[5:7]) - 1] + ")"
    if yoy is not None:
        new["yoy_change_pct"] = yoy
    # ---- cost and farebox series from NTD Annual Metrics (SRC-302) ----
    metrics = fetch_metrics()
    cost_series = {}
    for r in metrics:
        opexp = float(r.get("total_operating_expenses") or 0)
        fares = float(r.get("fare_revenues_earned") or 0)
        upt = float(r.get("unlinked_passenger_trips") or 0)
        if not (opexp and upt):
            continue
        cost_series.setdefault(r["report_year"], []).append({
            "mode": r["mode_name"], "code": r["mode"], "tos": r["type_of_service"],
            "cost_per_trip": round(opexp / upt, 2),
            "farebox_recovery_pct": round(100 * fares / opexp, 1),
            "operating_expenses": int(opexp), "fare_revenues": int(fares), "upt": int(upt),
        })
    if not cost_series:
        sys.exit("FATAL: no cost rows from NTD Annual Metrics")
    for y in cost_series:
        cost_series[y].sort(key=lambda e: (e["code"], e["tos"]))
    cost_first, cost_latest = min(cost_series), max(cost_series)
    if len(cost_series[cost_latest]) < 6:
        sys.exit(f"FATAL: only {len(cost_series[cost_latest])} mode rows for {cost_latest}")
    if cost_latest < new.get("cost_report_year", "2024"):
        sys.exit(f"FATAL: metrics latest year {cost_latest} older than ledger {new.get('cost_report_year')}")
    new["cost_source_id"] = "SRC-302"
    new["cost_report_year"] = cost_latest
    new["annual_cost_series"] = cost_series
    new["annual_cost_and_farebox"] = [
        {"mode": e["mode"], "tos": e["tos"], "cost_per_trip": e["cost_per_trip"],
         "recovery_ratio": e["farebox_recovery_pct"]}
        for e in sorted(cost_series[cost_latest], key=lambda e: (e["mode"], e["tos"]))
    ]
    new["annual_cost_note"] = (
        "VERIFIED: cost per trip and farebox recovery are computed from FTA NTD Annual "
        f"Metrics (dataset ekg5-frzt, data.transportation.gov), report years {cost_first} "
        f"to {cost_latest}, as operating expenses / unlinked trips and fare revenues / "
        "operating expenses (SRC-302). The recovered legacy extract (LEG-MBTA-01) was "
        "identified as report year 2024 and is superseded."
    )
    first_ix = {(e["code"], e["tos"]): e for e in cost_series[cost_first]}
    cost_trend = sorted(
        ({"mode": e["mode"], "tos": e["tos"],
          "cost_per_trip_" + cost_first: first_ix[(e["code"], e["tos"])]["cost_per_trip"],
          "cost_per_trip_" + cost_latest: e["cost_per_trip"],
          "change_pct": round(100 * (e["cost_per_trip"] / first_ix[(e["code"], e["tos"])]["cost_per_trip"] - 1), 1)}
         for e in cost_series[cost_latest] if (e["code"], e["tos"]) in first_ix),
        key=lambda t: -t["change_pct"],
    )

    new["vintage_note"] = (
        "Ridership rebuilt from FTA NTD Complete Monthly Ridership (dataset 8bui-9xvu, "
        f"data.transportation.gov), refreshed to {as_of} on {date.today().isoformat()} "
        "by scripts/refresh_dl12.py; monthly totals, annual mode cells, and the latest "
        "mode split are computed directly from the live dataset. Cost and farebox "
        f"figures are verified against NTD Annual Metrics report years {cost_first} "
        f"to {cost_latest} (SRC-302)."
    )

    # derived rollups (mirror of the engine's expectations)
    def name_of(c):
        return new["mode_names"].get(c, c)
    modes = [m for m in recovery if m != "TOTAL"]
    by_rec = sorted(modes, key=lambda c: -recovery[c])
    cost = new["annual_cost_and_farebox"]
    new["derived"] = {
        "note": ("Precomputed from the series above; prefer these over recomputing. "
                 "Recovery and ridership cite (derived, SRC-301); cost and farebox cite (derived, SRC-302)."),
        ("cost_per_trip_trend_" + cost_first + "_to_" + cost_latest): cost_trend,
        "modes_ranked_by_recovery_vs_2019": [
            {"code": c, "mode": name_of(c), "pct_of_2019": recovery[c]} for c in by_rec
        ],
        "modes_above_2019": [name_of(c) for c in by_rec if recovery[c] >= 100],
        "modes_ranked_by_cost_per_trip_cheapest_first": [
            {"mode": r["mode"], "tos": r["tos"], "cost_per_trip": r["cost_per_trip"]}
            for r in sorted(cost, key=lambda r: r["cost_per_trip"])
        ],
        "modes_ranked_by_farebox_recovery": [
            {"mode": r["mode"], "tos": r["tos"], "recovery_ratio_pct": r["recovery_ratio"]}
            for r in sorted(cost, key=lambda r: -r["recovery_ratio"])
        ],
        "latest_month_modes_ranked_by_riders": [
            {"code": c, "mode": name_of(c), "upt": v}
            for c, v in sorted(latest_mode.items(), key=lambda kv: -kv[1])
        ],
        "annual_total_upt": {
            yr: sum(annual_mode[yr].values())
            for yr in sorted(annual_mode) if "2014" <= yr <= last_full_year
        },
    }

    LEDGER.write_text(json.dumps(new, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")

    # summary for the PR body / logs
    changed_months = sum(
        1 for mk in months
        if not any(e["m"] == mk and e["v"] == monthly[mk] for e in old["monthly_total_upt"])
    )
    print(f"refresh_dl12: as_of {old['as_of']} -> {as_of}; "
          f"{len(months)} months in series; {changed_months} month values new or revised")

    subprocess.run([sys.executable, str(ROOT / "scripts/inject_data.py")], check=True)


if __name__ == "__main__":
    main()
