#!/usr/bin/env python3
"""Fill ledger.trend with every state the published file already has.

Does not rewrite latest, rows, or KPIs. Does not invent cells. Sets
page.revised to Aug 16, 2026 when the trend object actually grows.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_suite import URL_BFS, URL_LAUS, URL_PEP, MONTHS, parse_laus
from suite_builders import (
    DIGEST_203,
    DIGEST_216,
    DIGEST_304,
    URL_SAGDP,
    URL_SARPP,
    URL_SEDS_COMPLETE,
    _bea_csv_from_zip,
    _digest_all_year_trend,
    _wb,
    geo_to_st,
    parse_num,
)
from suite_common import STATE_NAMES, fetch_text, ledger_path, write_ledger

REVISED = "Aug 16, 2026"


def _load(tid):
    return json.loads(ledger_path(tid).read_text(encoding="utf-8"))


def _save(led, trend, label):
    old = led.get("trend") or {}
    old_n = sum(len(v or []) for v in old.values())
    new_n = sum(len(v or []) for v in trend.values())
    if new_n <= old_n and set(trend) <= set(old):
        print(f"  {label}: keep {len(old)} series, {old_n} points")
        return False
    led["trend"] = trend
    led.setdefault("page", {})["revised"] = REVISED
    write_ledger(led)
    print(f"  {label}: {len(trend)} series, {new_n} points (was {old_n})")
    return True


def expand_bfs():
    text = fetch_text(URL_BFS, timeout=120)
    rows = list(csv.DictReader(io.StringIO(text)))
    by_geo = {}
    for r in rows:
        if r["sa"] != "A" or r["naics_sector"] != "TOTAL" or r["series"] != "BA_BA":
            continue
        geo = r["geo"]
        if geo not in STATE_NAMES:
            continue
        by_geo.setdefault(geo, {})[int(r["year"])] = r
    trend = {}
    for st, years in by_geo.items():
        series = []
        for y in sorted(years):
            row = years[y]
            for i, key in enumerate(MONTHS, 1):
                raw = (row.get(key) or "").strip()
                if raw:
                    series.append({"m": f"{y}-{i:02d}", "v": int(float(raw))})
        if len(series) >= 2:
            trend[st] = series
    return _save(_load("DL-13"), trend, "DL-13 BFS")


def expand_laus():
    text = fetch_text(URL_LAUS, timeout=120)
    series = parse_laus(text)
    trend = {}
    for (st, y, m), v in sorted(series.items()):
        trend.setdefault(st, []).append({"m": f"{y}-{m:02d}", "v": v})
    trend = {st: pts for st, pts in trend.items() if len(pts) >= 2}
    return _save(_load("DL-14"), trend, "DL-14 LAUS")


def expand_pep():
    text = fetch_text(URL_PEP, timeout=90)
    rows = list(csv.DictReader(io.StringIO(text)))
    trend = {}
    for r in rows:
        if r.get("SUMLEV") != "040":
            continue
        st = next((k for k, v in STATE_NAMES.items() if v == r["NAME"]), None)
        if not st:
            continue
        series = []
        for y in range(2020, 2026):
            raw = (r.get(f"DOMESTICMIG{y}") or "").strip()
            if raw != "":
                series.append({"y": y, "v": int(float(raw))})
        if len(series) >= 2:
            trend[st] = series
    return _save(_load("DL-17"), trend, "DL-17 PEP migration")


def expand_digest(tid, url, header_row, label, enroll_second=False):
    ws = _wb(url).active
    trend = _digest_all_year_trend(ws, header_row, enroll_second=enroll_second)
    return _save(_load(tid), trend, label)


def expand_gdp():
    rows = _bea_csv_from_zip(URL_SAGDP, "SAGDP1__ALL_AREAS_1997_2025.csv")
    trend = {}
    for r in rows:
        if str(r.get("LineCode", "")).strip() != "1":
            continue
        st = geo_to_st(r.get("GeoName"))
        if not st:
            continue
        series = []
        for y in range(1997, 2026):
            yv = parse_num(r.get(str(y)))
            if yv is not None:
                series.append({"y": y, "v": yv})
        if len(series) >= 2:
            trend[st] = series
    return _save(_load("DL-15"), trend, "DL-15 SAGDP")


def expand_rpp():
    rows = _bea_csv_from_zip(URL_SARPP, "SARPP_STATE_2008_2024.csv")
    trend = {}
    for r in rows:
        if str(r.get("LineCode", "")).strip() != "1":
            continue
        st = geo_to_st(r.get("GeoName"))
        if not st:
            continue
        series = []
        for y in range(2008, 2025):
            yv = parse_num(r.get(str(y)))
            if yv is not None:
                series.append({"y": y, "v": yv})
        if len(series) >= 2:
            trend[st] = series
    return _save(_load("DL-19"), trend, "DL-19 SARPP")


def expand_co2():
    text = fetch_text(URL_SEDS_COMPLETE, timeout=180)
    trend = {}
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("MSN") != "TETCE":
            continue
        st = row.get("StateCode")
        if st not in STATE_NAMES and st != "US":
            continue
        year = parse_num(row.get("Year"))
        v = parse_num(row.get("Data"))
        if year is None or v is None or year < 2000:
            continue
        trend.setdefault(st, []).append({"y": int(year), "v": round(v, 3)})
    for st in list(trend):
        trend[st].sort(key=lambda x: x["y"])
        if len(trend[st]) < 2:
            del trend[st]
    return _save(_load("DL-24"), trend, "DL-24 SEDS TETCE")


def main():
    jobs = [
        ("DL-09 charter", lambda: expand_digest("DL-09", DIGEST_216, 3, "DL-09 charter", True)),
        ("DL-08 college", lambda: expand_digest("DL-08", DIGEST_304, 2, "DL-08 college")),
        ("DL-07 k12", lambda: expand_digest("DL-07", DIGEST_203, 2, "DL-07 k12")),
        ("DL-13 BFS", expand_bfs),
        ("DL-14 LAUS", expand_laus),
        ("DL-17 PEP", expand_pep),
        ("DL-15 GDP", expand_gdp),
        ("DL-19 RPP", expand_rpp),
        ("DL-24 CO2", expand_co2),
    ]
    ok = fail = 0
    for name, fn in jobs:
        print(f"expand {name} ...")
        try:
            fn()
            ok += 1
        except Exception as exc:
            fail += 1
            print(f"  FAIL {name}: {exc}")
    print(f"done ok={ok} fail={fail}")
    if fail and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
