#!/usr/bin/env python3
"""Refresh the DL-03 reliability block from the MBTA Open Data Portal (SRC-303).

Sources (mbta-massdot.opendata.arcgis.com, published by MassDOT/MBTA):
  - Bus reliability CSV            item 5627613b1e2e446a884db42bc7226db3
  - Commuter Rail reliability CSV  item ec18161c237d419698abc767f1be6a50
  - Ferry reliability layer        MBTA_Ferry_Reliability FeatureServer
  - The RIDE reliability layer     MBTA_The_RIDE_Reliabilit FeatureServer

Reliability is the share of trips that met the MBTA's headway or
schedule-adherence standard (for The RIDE, on-time pickups; for ferry, on-time
trips). Bus, commuter rail, and The RIDE carry trip-count numerators and
denominators, so their figures are volume weighted; the ferry layer publishes
only a monthly on-time rate per line, so ferry is an unweighted mean of line
months and is labeled as such.

Subway (Red, Orange, Blue) and the Green Line are deliberately NOT covered: the
MBTA measures rapid transit reliability with Excess Trip Time, a different
method adopted December 2024, which is not comparable to this headway series.

Reads the existing ledger, replaces ONLY the "reliability" block, writes it
back, and re-runs inject_data.py. It never touches ridership, cost, or service
keys. Companion to refresh_dl03.py and refresh_dl03_service.py.

Exits nonzero when the fetched data fails sanity checks.
"""
import csv
import io
import json
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "netlify/functions/dl03-answers.json"
ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}/data"
LAYER = "https://services1.arcgis.com/ceiitspzDAHrdGO1/arcgis/rest/services/{}/FeatureServer/0/query"
BUS_ITEM = "5627613b1e2e446a884db42bc7226db3"
CR_ITEM = "ec18161c237d419698abc767f1be6a50"
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
BUS_ROUTE_MIN_TRIPS = 200000  # trailing-year trip-metrics floor for the route leaderboard


def fetch_csv(item):
    url = ITEM.format(item)
    with urllib.request.urlopen(url, timeout=120) as r:
        text = r.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def fetch_layer(service):
    feats, offset = [], 0
    while True:
        url = (LAYER.format(service) + "?where=1%3D1&outFields=*"
               + f"&resultOffset={offset}&resultRecordCount=2000&f=json")
        with urllib.request.urlopen(url, timeout=120) as r:
            page = json.load(r)
        fs = page.get("features", [])
        feats.extend(fs)
        if len(fs) < 2000:
            return feats
        offset += 2000


def norm_month(d):
    """Return YYYY-MM from either YYYY-MM-DD or M/D/YYYY."""
    if "-" in d:
        return d[:7]
    mo, _, yr = d.split("/")
    return f"{yr}-{int(mo):02d}"


def window_months(latest_ym, n=12):
    y, m = int(latest_ym[:4]), int(latest_ym[5:7])
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return set(out)


def pct(num, den):
    return round(100 * num / den, 1) if den else None


def weighted_series(rows, route_key, name_key):
    """rows: list of (ym, route_id, route_name, num, den). Returns aggregates."""
    by_month = defaultdict(lambda: [0.0, 0.0])
    by_year = defaultdict(lambda: [0.0, 0.0])
    by_route_ttm = defaultdict(lambda: [0.0, 0.0, ""])
    latest = max(ym for ym, *_ in rows)
    ttm = window_months(latest)
    for ym, rid, rname, num, den in rows:
        by_month[ym][0] += num
        by_month[ym][1] += den
        by_year[ym[:4]][0] += num
        by_year[ym[:4]][1] += den
        if ym in ttm:
            rec = by_route_ttm[rid]
            rec[0] += num
            rec[1] += den
            rec[2] = rname or rec[2] or rid
    ttm_num = sum(by_month[m][0] for m in ttm if m in by_month)
    ttm_den = sum(by_month[m][1] for m in ttm if m in by_month)
    return {
        "latest": latest, "ttm": ttm, "ttm_pct": pct(ttm_num, ttm_den),
        "by_year": by_year, "by_route_ttm": by_route_ttm,
    }


def annual_list(by_year, latest_ym):
    """Calendar-year reliability, oldest first; flags a partial final year."""
    out = []
    for y in sorted(by_year):
        num, den = by_year[y]
        if not den:
            continue
        row = {"y": y, "pct": pct(num, den)}
        if y == latest_ym[:4] and not latest_ym.endswith("-12"):
            row["partial"] = True
        out.append(row)
    return out


def load_csv_rows(records):
    out = []
    for r in records:
        num, den = r.get("otp_numerator"), r.get("otp_denominator")
        if den in (None, "", "NA", "0") or num in (None, "", "NA"):
            continue
        rid = r.get("gtfs_route_id") or ""
        rname = (r.get("gtfs_route_long_name") or "").strip() or (r.get("gtfs_route_short_name") or "").strip()
        out.append((norm_month(r["service_date"]), rid, rname, float(num), float(den)))
    return out


def main():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    # ---- Bus and Commuter Rail: weighted from daily trip-count CSVs ----
    bus = weighted_series(load_csv_rows(fetch_csv(BUS_ITEM)), "rid", "rname")
    cr = weighted_series(load_csv_rows(fetch_csv(CR_ITEM)), "rid", "rname")

    # ---- The RIDE: weighted from daily on-time pickup counts ----
    ride_by_month = defaultdict(lambda: [0.0, 0.0])
    for f in fetch_layer("MBTA_The_RIDE_Reliabilit"):
        a = f["attributes"]
        ts, on, tot = a.get("trip_date"), a.get("ontime_trip_count"), a.get("trip_count")
        if not (ts and tot):
            continue
        ym = date.fromtimestamp(ts / 1000).strftime("%Y-%m")
        ride_by_month[ym][0] += float(on or 0)
        ride_by_month[ym][1] += float(tot)
    ride_by_year = defaultdict(lambda: [0.0, 0.0])
    for ym, (on, tot) in ride_by_month.items():
        ride_by_year[ym[:4]][0] += on
        ride_by_year[ym[:4]][1] += tot
    ride_latest = max(ride_by_month)
    ride_ttm = window_months(ride_latest)
    ride_ttm_pct = pct(sum(ride_by_month[m][0] for m in ride_ttm if m in ride_by_month),
                       sum(ride_by_month[m][1] for m in ride_ttm if m in ride_by_month))

    # ---- Ferry: unweighted mean of line-level monthly on-time rate ----
    ferry_line_month = []  # (ym, line_name, otp)
    for f in fetch_layer("MBTA_Ferry_Reliability"):
        a = f["attributes"]
        y, mo = a.get("service_year"), MONTHS.get(a.get("service_month"))
        otp = a.get("on_time_performance")
        if otp is None or not y or not mo:
            continue
        ferry_line_month.append((f"{int(y):04d}-{mo:02d}", (a.get("line_name") or "").strip(), float(otp)))
    ferry_latest = max(ym for ym, *_ in ferry_line_month)
    ferry_by_year = defaultdict(list)
    for ym, ln, otp in ferry_line_month:
        ferry_by_year[ym[:4]].append(otp)
    ferry_annual = [{"y": y, "pct": round(100 * sum(v) / len(v), 1)} for y, v in sorted(ferry_by_year.items())]
    if ferry_annual and not ferry_latest.endswith("-12") and ferry_annual[-1]["y"] == ferry_latest[:4]:
        ferry_annual[-1]["partial"] = True
    ferry_latest_year = ferry_latest[:4]
    ferry_line_latest = defaultdict(list)
    for ym, ln, otp in ferry_line_month:
        if ym[:4] == ferry_latest_year and ln:
            ferry_line_latest[ln].append(otp)
    ferry_by_line = sorted(
        ({"line": ln, "pct": round(100 * sum(v) / len(v), 1)} for ln, v in ferry_line_latest.items()),
        key=lambda e: -e["pct"])
    ferry_ttm_pct = ([r["pct"] for r in ferry_annual if r["y"] == ferry_latest_year] or [None])[0]

    def fy(series):
        """latest full year value from a weighted by_year map."""
        latest = series["latest"]
        lfy = latest[:4] if latest.endswith("-12") else str(int(latest[:4]) - 1)
        num, den = series["by_year"].get(lfy, [0, 0])
        return lfy, pct(num, den)

    bus_lfy, bus_lfy_pct = fy(bus)
    cr_lfy, cr_lfy_pct = fy(cr)
    bus_2019 = pct(*bus["by_year"].get("2019", [0, 0]))
    cr_2019 = pct(*cr["by_year"].get("2019", [0, 0]))

    if not (40 < (bus["ttm_pct"] or 0) < 95 and 70 < (cr["ttm_pct"] or 0) < 100):
        sys.exit(f"FATAL: implausible reliability: bus {bus['ttm_pct']}, cr {cr['ttm_pct']}")

    # bus route leaderboard over the trailing year, with a volume floor
    bus_routes = sorted(
        ({"route": rid, "name": rec[2], "pct": pct(rec[0], rec[1])}
         for rid, rec in bus["by_route_ttm"].items() if rec[1] >= BUS_ROUTE_MIN_TRIPS),
        key=lambda e: e["pct"])
    cr_by_line = sorted(
        ({"line": rec[2], "pct": pct(rec[0], rec[1])} for rec in cr["by_route_ttm"].values() if rec[1]),
        key=lambda e: -e["pct"])

    def win_label(ym):
        s = sorted(window_months(ym))
        return s[0] + " to " + s[-1]

    as_of = max(bus["latest"], cr["latest"], ride_latest, ferry_latest)
    modes = {
        "MB": {
            "mode": "Bus", "as_of": bus["latest"], "ttm_pct": bus["ttm_pct"],
            "ttm_window": win_label(bus["latest"]), "latest_full_year": bus_lfy,
            "latest_full_year_pct": bus_lfy_pct, "pct_2019": bus_2019,
            "method": ("Volume weighted share of trips meeting the headway or "
                       "schedule-adherence standard. The adjusted metric applies from "
                       "August 2025 with the Bus Network Redesign."),
            "annual": annual_list(bus["by_year"], bus["latest"]),
        },
        "CR": {
            "mode": "Commuter Rail", "as_of": cr["latest"], "ttm_pct": cr["ttm_pct"],
            "ttm_window": win_label(cr["latest"]), "latest_full_year": cr_lfy,
            "latest_full_year_pct": cr_lfy_pct, "pct_2019": cr_2019,
            "method": "Volume weighted share of trips meeting the schedule-adherence standard.",
            "annual": annual_list(cr["by_year"], cr["latest"]),
        },
        "FB": {
            "mode": "Ferry", "as_of": ferry_latest, "ttm_pct": ferry_ttm_pct,
            "ttm_window": ferry_latest_year, "latest_full_year": ferry_latest_year,
            "latest_full_year_pct": ferry_ttm_pct, "pct_2019": None,
            "method": ("Unweighted mean of line-level monthly on-time performance. "
                       "Ferry data begins in 2021, so there is no 2019 baseline."),
            "annual": ferry_annual,
        },
        "DR": {
            "mode": "The RIDE", "as_of": ride_latest, "ttm_pct": ride_ttm_pct,
            "ttm_window": win_label(ride_latest),
            "latest_full_year": (ride_latest[:4] if ride_latest.endswith("-12") else str(int(ride_latest[:4]) - 1)),
            "latest_full_year_pct": pct(*ride_by_year.get(
                ride_latest[:4] if ride_latest.endswith("-12") else str(int(ride_latest[:4]) - 1), [0, 0])),
            "pct_2019": pct(*ride_by_year.get("2019", [0, 0])),
            "method": "Volume weighted share of on-time pickups for The RIDE paratransit service.",
            "annual": annual_list(ride_by_year, ride_latest),
        },
    }
    ranked = sorted(
        ({"code": c, "mode": m["mode"], "pct": m["ttm_pct"]} for c, m in modes.items() if m["ttm_pct"]),
        key=lambda e: -e["pct"])

    ledger["reliability"] = {
        "as_of": as_of,
        "source_id": "SRC-303",
        "metric_note": (
            "Reliability is the share of trips that met the MBTA's headway or "
            "schedule-adherence standard, from the MBTA Open Data Portal (SRC-303). "
            "Trailing-year figures cover the twelve months ending at each mode's own "
            "latest month. Bus, commuter rail, and The RIDE are volume weighted; ferry "
            "is an unweighted mean of line-level monthly on-time performance."
        ),
        "excludes_note": (
            "Subway (Red, Orange, Blue) and the Green Line are not included here: the "
            "MBTA measures rapid transit reliability with Excess Trip Time, a different "
            "method adopted December 2024 that is not comparable to this headway series."
        ),
        "modes": modes,
        "commuter_rail_by_line_ttm": cr_by_line,
        "bus_routes_ttm": {
            "min_trips": BUS_ROUTE_MIN_TRIPS,
            "worst": bus_routes[:5],
            "best": list(reversed(bus_routes[-5:])),
        },
        "ferry_by_line_latest_year": ferry_by_line,
        "derived": {
            "note": "Precomputed rankings; all reliability figures cite (SRC-303).",
            "modes_ranked_by_reliability_ttm": ranked,
        },
    }

    LEDGER.write_text(json.dumps(ledger, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")
    print(f"refresh_dl03_reliability: as_of {as_of}; "
          f"bus {modes['MB']['ttm_pct']}%, cr {modes['CR']['ttm_pct']}%, "
          f"ferry {modes['FB']['ttm_pct']}%, ride {modes['DR']['ttm_pct']}% (trailing year)")

    subprocess.run([sys.executable, str(ROOT / "scripts/inject_data.py")], check=True)


if __name__ == "__main__":
    main()
