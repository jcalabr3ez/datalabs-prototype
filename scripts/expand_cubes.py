#!/usr/bin/env python3
"""Wave 1 full cubes and Wave 2 named companions.

Does not touch DL-01 (wealth taxes) or DL-02 (Florida HOI).
Writes page.revised to Aug 16, 2026 on ledgers this pass actually changes.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from refresh_suite import (
    app_by_id,
    build_bfs,
    parse_bps,
    parse_laus,
    URL_BPS,
)
from suite_builders import _wb
from suite_common import (
    MONTH_ABBR,
    RANKED,
    STATE_NAMES,
    fetch_text,
    ledger_path,
    load_apps,
    parse_num,
    write_ledger,
)
from suite_later import enrich
from suite_windows import attach_windows, windows_from_trend

REVISED = "Aug 16, 2026"
SKIP = {"DL-01", "DL-02", "DL-18"}


def _load(tid):
    led = json.loads(ledger_path(tid).read_text(encoding="utf-8"))
    if "tool_id" not in led:
        led["tool_id"] = tid
    return led


def _touch(led):
    led.setdefault("page", {})["revised"] = REVISED
    return led


def _bed_rate_trend(bed):
    states = (bed or {}).get("states") or {}
    birth, death = {}, {}
    for st, series in states.items():
        b, d = [], []
        for p in series or []:
            q = p.get("q")
            if p.get("birth_rate_pct") is not None and q:
                b.append({"q": q, "v": p["birth_rate_pct"]})
            if p.get("death_rate_pct") is not None and q:
                d.append({"q": q, "v": p["death_rate_pct"]})
        if len(b) >= 2:
            birth[st] = b
        if len(d) >= 2:
            death[st] = d
    return birth, death


def attach_bed_windows(ledger):
    bed = ((ledger.get("derived") or {}).get("secondary") or {}).get("bed_births_deaths") or {}
    birth, death = _bed_rate_trend(bed)
    wins = {}
    if birth:
        wins.update(windows_from_trend(
            birth, src="SRC-613-02", unit="percent",
            ns=(4, 9), label_stem="Establishment birth rate",
            named_ends=["2024 Q3"], prefix="bed_birth_rate",
        ))
    if death:
        wins.update(windows_from_trend(
            death, src="SRC-613-02", unit="percent",
            ns=(4, 9), label_stem="Establishment death rate",
            named_ends=["2024 Q3"], prefix="bed_death_rate",
        ))
    attach_windows(
        ledger, wins,
        note="Prefer these over recomputing. BED window means and ranks cite (derived, SRC-613-02).",
    )
    w9 = wins.get("bed_birth_rate_t9_2024q3")
    if w9 and bed:
        bed["window_9q_2024q3"] = {
            "ma": w9.get("ma"), "us": w9.get("us"), "fl": w9.get("fl"),
            "highest": w9.get("highest"), "lowest": w9.get("lowest"),
            "end": w9.get("end"), "n_periods": 9,
        }
    return ledger


def expand_dl13():
    apps = load_apps()
    app = app_by_id(apps, "DL-13")
    print("expand DL-13 BFS + all-state BED ...")
    ledger = build_bfs(app)
    ledger = enrich(app, ledger)
    ledger = attach_bed_windows(ledger)
    _touch(ledger)
    write_ledger(ledger)
    bed = ((ledger.get("derived") or {}).get("secondary") or {}).get("bed_births_deaths") or {}
    n_states = len((bed.get("states") or {}))
    n_win = len((ledger.get("derived") or {}).get("windows") or {})
    print(f"  BED states={n_states} windows={n_win} trend_pts={len((ledger.get('trend') or {}).get('MA') or [])}")


def expand_dl14_history():
    print("expand DL-14 LAUS full history ...")
    led = _load("DL-14")
    text = fetch_text("https://download.bls.gov/pub/time.series/la/la.data.3.AllStatesS", timeout=120)
    series = parse_laus(text)
    trend = {}
    for (st, y, m), v in sorted(series.items()):
        trend.setdefault(st, []).append({"m": f"{y}-{m:02d}", "v": v})
    trend = {st: pts for st, pts in trend.items() if len(pts) >= 2}
    old_n = sum(len(v or []) for v in (led.get("trend") or {}).values())
    new_n = sum(len(v) for v in trend.values())
    led["trend"] = trend
    attach_windows(
        led,
        windows_from_trend(
            trend, src="SRC-614-01", unit="percent",
            ns=(12, 36), label_stem="Seasonally adjusted unemployment rate",
            prefix="laus_rate",
        ),
        note="Prefer these over recomputing. Window means and ranks cite (derived, SRC-614-01).",
    )
    _touch(led)
    write_ledger(led)
    print(f"  LAUS points {old_n} -> {new_n}")


def expand_qcew_stack():
    print("expand DL-14 QCEW quarter stack ...")
    from suite_common import FIPS_TO_ST
    led = _load("DL-14")
    cube = {}
    for year in (2023, 2024, 2025):
        for q in (1, 2, 3, 4):
            if year == 2025 and q > 4:
                continue
            url = f"https://data.bls.gov/cew/data/api/{year}/{q}/industry/10.csv"
            try:
                text = fetch_text(url, timeout=90)
            except Exception as exc:
                print(f"  skip QCEW {year} Q{q}: {exc}")
                continue
            emp, wage = {}, {}
            for r in csv.DictReader(io.StringIO(text)):
                if not (
                    r.get("own_code") == "0"
                    and r.get("agglvl_code") == "50"
                    and r.get("industry_code") == "10"
                ):
                    continue
                fips = (r.get("area_fips") or "").zfill(5)
                st = FIPS_TO_ST.get(fips[:2])
                if not st or st == "US":
                    continue
                e1 = parse_num(r.get("month1_emplvl"))
                e2 = parse_num(r.get("month2_emplvl"))
                e3 = parse_num(r.get("month3_emplvl"))
                w = parse_num(r.get("avg_wkly_wage"))
                if None not in (e1, e2, e3):
                    emp[st] = (e1 + e2 + e3) / 3
                if w is not None:
                    wage[st] = w
            if "MA" not in emp:
                continue
            label = f"{year} Q{q}"
            for st, v in emp.items():
                cube.setdefault(st, []).append({
                    "q": label, "employment": round(v),
                    "avg_weekly_wage": round(wage[st]) if st in wage else None,
                })
    if "MA" not in cube:
        print("  QCEW stack empty")
        return
    sec = (led.setdefault("derived", {})).setdefault("secondary", {})
    emp_trend = {
        st: [{"q": p["q"], "v": p["employment"]} for p in pts if p.get("employment")]
        for st, pts in cube.items()
    }
    wage_trend = {
        st: [{"q": p["q"], "v": p["avg_weekly_wage"]} for p in pts if p.get("avg_weekly_wage")]
        for st, pts in cube.items()
    }
    sec["qcew_quarter_stack"] = {
        "label": "QCEW employment and average weekly wage by quarter",
        "src": "SRC-614-02",
        "unit": "jobs",
        "note": "BLS QCEW statewide all-ownership, all industries. Cube is modelSlice-only.",
        "cube": cube,
    }
    attach_windows(
        led,
        {
            **windows_from_trend(
                emp_trend, src="SRC-614-02", unit="jobs",
                ns=(4,), label_stem="QCEW average monthly employment",
                prefix="qcew_emp",
            ),
            **windows_from_trend(
                wage_trend, src="SRC-614-02", unit="dollars per week",
                ns=(4,), label_stem="QCEW average weekly wage",
                prefix="qcew_wage",
            ),
        },
    )
    _touch(led)
    write_ledger(led)
    print(f"  QCEW geos={len(cube)} quarters={len(cube.get('MA') or [])}")


def attach_existing_windows():
    specs = {
        "DL-06": ("SRC-606-01", "dollars", (2,), "Current expenditures per pupil"),
        "DL-07": ("SRC-607-01", "students", (4, 8), "Public K-12 fall enrollment"),
        "DL-08": ("SRC-608-01", "students", (4, 8), "Fall postsecondary enrollment"),
        "DL-09": ("SRC-609-01", "students", (4,), "Public charter fall enrollment"),
        "DL-15": ("SRC-615-01", "millions of chained 2017 dollars", (4, 8), "Real GDP"),
        "DL-17": ("SRC-617-01", "people", (4,), "Domestic migration"),
        "DL-19": ("SRC-619-01", "index, US=100", (4, 8), "Regional price parities"),
        "DL-24": ("SRC-624-01", "million metric tons", (4, 8), "Energy-related CO2"),
    }
    for tid, (src, unit, ns, stem) in specs.items():
        print(f"windows {tid} ...")
        led = _load(tid)
        if led.get("status") != "live":
            continue
        trend = led.get("trend") or {}
        if not isinstance(trend, dict) or "MA" not in trend:
            print("  skip: no MA trend")
            continue
        wins = windows_from_trend(
            trend, src=src, unit=unit, ns=ns, label_stem=stem,
            prefix=tid.lower().replace("-", ""),
        )
        attach_windows(led, wins)
        _touch(led)
        write_ledger(led)
        print(f"  {len(wins)} windows")


def expand_dl04_windows():
    print("windows DL-04 ...")
    led = _load("DL-04")
    trend = led.get("price_trend") or {}
    if "MA" not in trend:
        print("  skip")
        return
    wins = windows_from_trend(
        trend, src="SRC-401", unit="cents per kWh",
        ns=(4, 8), label_stem="All-sector retail electricity price",
        prefix="eia_price",
    )
    attach_windows(led, wins)
    _touch(led)
    write_ledger(led)
    print(f"  {len(wins)} windows")


def expand_bps_history():
    print("expand DL-16 BPS year stack ...")
    led = _load("DL-16")
    trend = {}
    for year in range(2018, 2027):
        month = 12 if year < 2026 else 6
        url = URL_BPS.format(yy=f"{year % 100:02d}", mm=f"{month:02d}")
        try:
            text = fetch_text(url, timeout=60)
        except Exception as exc:
            print(f"  skip BPS {year}-{month:02d}: {exc}")
            continue
        values = parse_bps(text)
        if "MA" not in values:
            continue
        label = f"{year}-{month:02d}"
        for st, v in values.items():
            trend.setdefault(st, []).append({"m": label, "v": v})
    if "MA" not in trend or len(trend["MA"]) < 2:
        print("  BPS stack too thin")
        return
    led["trend"] = trend
    attach_windows(
        led,
        windows_from_trend(
            trend, src="SRC-616-01", unit="units",
            ns=(4,), label_stem="Housing units authorized, year-to-date",
            prefix="bps_units",
        ),
    )
    _touch(led)
    write_ledger(led)
    print(f"  BPS years={len(trend['MA'])} geos={len(trend)}")


def _qtax_totals(ws):
    """Read Total Taxes by state from a QTAX table-3 sheet.

    2026 Q1 uses five columns per geo. Earlier quarters use two (footnote, value).
    """
    from suite_builders import geo_to_st
    header = None
    totals = None
    for row in ws.iter_rows(min_row=5, max_row=12, values_only=True):
        cells = list(row)
        label = str(cells[0] or "").strip()
        if header is None and any(geo_to_st(c) for c in cells if c):
            header = cells
        if label == "Total Taxes":
            totals = cells
            break
    if not header or not totals:
        return {}
    geos = []
    for i, name in enumerate(header):
        st = geo_to_st(name) if name else None
        if st:
            geos.append((i, st))
    out = {}
    for idx, (i, st) in enumerate(geos):
        nxt = geos[idx + 1][0] if idx + 1 < len(geos) else len(totals)
        v = None
        for j in range(i, nxt):
            v = parse_num(totals[j]) if j < len(totals) else None
            if v is not None and abs(v) > 10:
                break
        if v is not None:
            out[st] = v * 1000
    return out


def expand_qtax_stack():
    print("expand DL-28/29 QTAX quarter stack ...")
    cube = {}
    for year, q in (
        (2024, 1), (2024, 2), (2024, 3), (2024, 4),
        (2025, 1), (2025, 2), (2025, 3), (2025, 4),
        (2026, 1),
    ):
        url = f"https://www2.census.gov/programs-surveys/qtax/tables/{year}/q{q}t3.xlsx"
        try:
            ws = _wb(url).active
        except Exception as exc:
            print(f"  skip QTAX {year} Q{q}: {exc}")
            continue
        values = _qtax_totals(ws)
        if "MA" not in values:
            print(f"  skip QTAX {year} Q{q}: no Massachusetts cell")
            continue
        label = f"{year} Q{q}"
        for st, v in values.items():
            cube.setdefault(st, []).append({"q": label, "v": round(v)})
    if "MA" not in cube or len(cube["MA"]) < 2:
        print("  QTAX stack too thin")
        return
    trend = {st: pts for st, pts in cube.items() if len(pts) >= 2}
    for tid, src in (("DL-28", "SRC-628-01"), ("DL-29", "SRC-629-01")):
        led = _load(tid)
        if tid == "DL-28":
            led["trend"] = {"MA": trend.get("MA", [])}
            if trend.get("US"):
                led["trend"]["US"] = trend["US"]
            wins = windows_from_trend(
                led["trend"], src=src, unit="dollars", ns=(4,),
                label_stem="Total tax collections", prefix="qtax_ma",
            )
        else:
            led["trend"] = {st: pts for st, pts in trend.items() if st in RANKED}
            wins = windows_from_trend(
                led["trend"], src=src, unit="dollars", ns=(4,),
                label_stem="State tax collections, total taxes",
                prefix="qtax_total",
            )
        attach_windows(led, wins)
        sec = (led.setdefault("derived", {})).setdefault("secondary", {})
        sec["qtax_quarter_stack"] = {
            "label": "Census QTAX total taxes by quarter",
            "src": src,
            "unit": "dollars",
            "note": "Table 3 Total Taxes. Amounts converted from thousands of dollars.",
            "cube": {st: pts for st, pts in cube.items() if tid == "DL-29" or st in ("MA", "US")},
        }
        _touch(led)
        write_ledger(led)
        print(f"  {tid} quarters={len((trend.get('MA') or []))}")


def expand_dl03_windows():
    print("windows DL-03 ...")
    led = _load("DL-03")
    monthly = led.get("monthly_total_upt") or []
    if len(monthly) < 12:
        print("  skip")
        return
    pts = [p for p in monthly if p.get("v") is not None]
    if len(pts) < 12:
        return
    last12 = pts[-12:]
    mean = sum(p["v"] for p in last12) / 12
    derived = led.setdefault("derived", {})
    wins = derived.setdefault("windows", {})
    wins["note"] = "Prefer these over recomputing. Window means cite (derived, SRC-301)."
    wins["mbta_upt_trailing_12m"] = {
        "id": "mbta_upt_trailing_12m",
        "label": f"MBTA unlinked trips, trailing 12 months ending {last12[-1].get('m')}",
        "src": "SRC-301",
        "unit": "unlinked passenger trips",
        "end": last12[-1].get("m"),
        "n_periods": 12,
        "v": round(mean),
        "first": last12[0].get("m"),
    }
    _touch(led)
    write_ledger(led)
    print(f"  trailing-12 mean {round(mean):,}")


def try_ojjdp():
    print("try OJJDP juvenile custody ...")
    # Easy Access to the Census of Juveniles in Residential Placement is
    # an interactive tool, not a stable state CSV. Leave declined.
    print("  no stable state CSV; keep declining")


def main():
    jobs = [
        ("DL-13", expand_dl13),
        ("DL-14 history", expand_dl14_history),
        ("DL-14 QCEW", expand_qcew_stack),
        ("existing windows", attach_existing_windows),
        ("DL-04 windows", expand_dl04_windows),
        ("DL-16 BPS", expand_bps_history),
        ("QTAX stack", expand_qtax_stack),
        ("DL-03 windows", expand_dl03_windows),
        ("OJJDP", try_ojjdp),
    ]
    ok = fail = 0
    for name, fn in jobs:
        try:
            fn()
            ok += 1
        except Exception as exc:
            fail += 1
            print(f"FAIL {name}: {exc}")
            import traceback
            traceback.print_exc()
    print(f"done ok={ok} fail={fail}")
    if fail and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
