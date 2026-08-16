#!/usr/bin/env python3
"""Add Florida to live US-tool snaps, special charts, and main trends.

Re-runs later-view enrich for fifty-state tools (does not rebuild flagship
ledgers or rewrite primary ranks). Then fills trend.FL from the same public
files the builders already use.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from refresh_suite import URL_BFS, URL_LAUS, URL_PEP, MONTHS, parse_laus
from suite_builders import (
    DIGEST_203,
    URL_SAGDP,
    URL_SARPP,
    URL_SEDS_COMPLETE,
    VERIFY_US_ENROLL_FALL_2024,
    _bea_csv_from_zip,
    _digest_state_table,
)
from suite_common import (
    fetch_text,
    geo_to_st,
    ledger_path,
    load_apps,
    parse_num,
    write_ledger,
)
from suite_later import enrich

REVISED_PAGE = "Aug 16, 2026"
ENRICH_IDS = (
    "DL-07", "DL-08", "DL-09", "DL-12", "DL-13", "DL-14", "DL-15",
    "DL-16", "DL-17", "DL-19", "DL-20", "DL-21", "DL-23", "DL-24",
    "DL-29", "DL-31",
)
TREND_IDS = ("DL-07", "DL-13", "DL-14", "DL-15", "DL-17", "DL-19", "DL-24")


def _load(app):
    return json.loads(ledger_path(app["id"]).read_text(encoding="utf-8"))


def _touch_page(ledger):
    page = ledger.setdefault("page", {})
    page["revised"] = REVISED_PAGE
    geo = list(ledger.get("geo") or [])
    if "MA" in geo and "FL" not in geo and "Boston" not in geo:
        ledger["geo"] = geo + ["FL"]
    elif geo == ["US"]:
        ledger["geo"] = ["US", "FL"]


def _enroll_fl():
    values, us_val, col, label, raw, ws, header_row = _digest_state_table(
        DIGEST_203, 2, "Fall 2024", us_check=VERIFY_US_ENROLL_FALL_2024
    )
    headers = [c.value for c in ws[2]]
    by_st = {st: row for st, row in raw}
    out = []
    for i, h in enumerate(headers):
        if h is None:
            continue
        s = str(h).replace("\xa0", " ")
        if not s.startswith("Fall "):
            continue
        year = parse_num(s.replace("Fall ", "")[:4])
        row = by_st.get("FL")
        if year is None or not row:
            continue
        v = parse_num(row[i])
        if v is not None:
            out.append({"y": int(year), "v": int(round(v))})
    if len(out) < 8:
        sys.exit(f"FATAL: Digest enrollment Florida trend parsed {len(out)} years")
    return out


def _bfs_fl():
    text = fetch_text(URL_BFS, timeout=120)
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        if r.get("sa") != "A" or r.get("naics_sector") != "TOTAL" or r.get("series") != "BA_BA":
            continue
        if r.get("geo") != "FL":
            continue
        year = int(r["year"])
        if year < 2018:
            continue
        for i, key in enumerate(MONTHS, 1):
            raw = (r.get(key) or "").strip()
            if raw:
                out.append({"m": f"{year}-{i:02d}", "v": int(float(raw))})
    out.sort(key=lambda x: x["m"])
    if len(out) < 24:
        sys.exit(f"FATAL: BFS Florida trend parsed {len(out)} months")
    return out


def _laus_fl():
    series = parse_laus(fetch_text(URL_LAUS, timeout=120))
    out = []
    for (st, y, m), v in sorted(series.items()):
        if st == "FL" and y >= 2018:
            out.append({"m": f"{y}-{m:02d}", "v": v})
    if len(out) < 24:
        sys.exit(f"FATAL: LAUS Florida trend parsed {len(out)} months")
    return out


def _pep_fl():
    text = fetch_text(URL_PEP, timeout=90)
    fl_row = None
    for r in csv.DictReader(io.StringIO(text)):
        name = (r.get("NAME") or "").strip()
        if name == "Florida":
            fl_row = r
            break
    if not fl_row:
        sys.exit("FATAL: PEP file missing Florida")
    out = []
    for y in range(2020, 2026):
        v = parse_num(fl_row.get(f"POPESTIMATE{y}"))
        if v is not None:
            out.append({"y": y, "v": int(v)})
    if len(out) < 4:
        sys.exit(f"FATAL: PEP Florida trend parsed {len(out)} years")
    return out


def _sagdp_fl():
    rows = _bea_csv_from_zip(URL_SAGDP, "SAGDP1__ALL_AREAS_1997_2025.csv")
    out = []
    for r in rows:
        if str(r.get("LineCode", "")).strip() != "1":
            continue
        if geo_to_st(r.get("GeoName")) != "FL":
            continue
        for y in range(1997, 2026):
            v = parse_num(r.get(str(y)))
            if v is not None:
                out.append({"y": y, "v": v})
        break
    if len(out) < 10:
        sys.exit(f"FATAL: SAGDP1 Florida trend parsed {len(out)} years")
    return out


def _sarpp_fl():
    rows = _bea_csv_from_zip(URL_SARPP, "SARPP_STATE_2008_2024.csv")
    out = []
    for r in rows:
        if str(r.get("LineCode", "")).strip() != "1":
            continue
        if geo_to_st(r.get("GeoName")) != "FL":
            continue
        for y in range(2008, 2025):
            v = parse_num(r.get(str(y)))
            if v is not None:
                out.append({"y": y, "v": v})
        break
    if len(out) < 8:
        sys.exit(f"FATAL: SARPP Florida trend parsed {len(out)} years")
    return out


def _seds_fl():
    text = fetch_text(URL_SEDS_COMPLETE, timeout=180)
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("MSN") != "TETCE" or row.get("StateCode") != "FL":
            continue
        year = parse_num(row.get("Year"))
        v = parse_num(row.get("Data"))
        if year is None or v is None or year < 2000:
            continue
        out.append({"y": int(year), "v": round(v, 3)})
    out.sort(key=lambda x: x["y"])
    if not out or out[-1]["y"] != 2024:
        sys.exit("FATAL: SEDS complete TETCE Florida trend missing 2024")
    return out


TREND_FETCH = {
    "DL-07": _enroll_fl,
    "DL-13": _bfs_fl,
    "DL-14": _laus_fl,
    "DL-15": _sagdp_fl,
    "DL-17": _pep_fl,
    "DL-19": _sarpp_fl,
    "DL-24": _seds_fl,
}


def _sync_apps_geo():
    """Keep compact apps.json formatting; only append FL to existing g arrays."""
    path = Path("/workspace/suite/apps.json")
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    for app in data["apps"]:
        if app["id"] not in ENRICH_IDS:
            continue
        g = list(app.get("g") or [])
        if "FL" in g:
            continue
        if "MA" not in g and g != ["US"]:
            continue
        old_lit = "[" + ", ".join(f'"{x}"' for x in g) + "]"
        new_lit = "[" + ", ".join(f'"{x}"' for x in g + ["FL"]) + "]"
        i = text.find(f'"id": "{app["id"]}"')
        gpos = text.find('"g":', i)
        next_id = text.find('"id":', i + 5)
        if i < 0 or gpos < 0 or (next_id > 0 and gpos > next_id):
            continue
        text = text[:gpos] + text[gpos:].replace(f'"g": {old_lit}', f'"g": {new_lit}', 1)
    path.write_text(text, encoding="utf-8")


def main():
    apps = {a["id"]: a for a in load_apps()}
    _sync_apps_geo()
    for tid in ENRICH_IDS:
        app = apps[tid]
        print(f"enrich {tid} {app['title']} ...", flush=True)
        ledger = _load(app)
        before = deepcopy(ledger.get("derived", {}).get("secondary"))
        try:
            ledger = enrich(app, ledger)
        except Exception as exc:
            print(f"  WARN enrich failed, keeping prior secondary: {exc}", flush=True)
            ledger.setdefault("derived", {})["secondary"] = before
        if tid in TREND_FETCH:
            print(f"  trend.FL {tid} ...", flush=True)
            try:
                fl_trend = TREND_FETCH[tid]()
                ledger.setdefault("trend", {})["FL"] = fl_trend
            except Exception as exc:
                print(f"  WARN trend.FL failed: {exc}", flush=True)
        if tid == "DL-20":
            ledger["scope"] = app["scope"]
            ledger["geo"] = ["US", "MA", "FL"]
            src = (ledger.get("source_id_map") or {}).get("SRC-620-02") or {}
            src["name"] = "IRS SOI county-to-county migration, tax years 2022-23"
            src["supports"] = app["scope"]
        if tid == "DL-13":
            ledger["scope"] = app["scope"]
        if tid == "DL-16":
            ledger["scope"] = app["scope"]
            src = (ledger.get("source_id_map") or {}).get("SRC-616-03") or {}
            src["name"] = app["sources"][2]["name"]
        if tid == "DL-21":
            ledger["scope"] = app["scope"]
        _touch_page(ledger)
        path = write_ledger(ledger)
        print(f"  wrote {path.name}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
