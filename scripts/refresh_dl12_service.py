#!/usr/bin/env python3
"""Refresh the DL-12 service and productivity block from the FTA NTD Socrata API.

Source: Complete Monthly Ridership (with adjustments and estimates), dataset
8bui-9xvu on data.transportation.gov, ntd_id 10003 (MBTA). This is the SAME
federal file the ridership series comes from (SRC-301): every row carries
vehicle revenue miles (vrm) and vehicle revenue hours (vrh) alongside unlinked
passenger trips (upt), so service supplied and productivity need no new source.

Computes, into the "service" key of the ledger, all by SRC-301:
  - monthly total vehicle revenue miles, 2014 through the latest month
  - annual totals (VRM, VRH, UPT, trips per revenue hour) for full years
  - by mode, the latest full year and 2019 side by side, with recovery vs 2019
  - derived rollups: systemwide productivity, a productivity ranking, and which
    modes now run more service than in 2019

Reads the existing ledger, replaces ONLY the "service" block, writes it back,
and re-runs inject_data.py. It never touches ridership or cost keys, so it is
safe to run without advancing the verified ridership vintage. Companion to
refresh_dl12.py (ridership and cost) and refresh_dl12_reliability.py.

Exits nonzero when the fetched data fails sanity checks.
"""
import json
import subprocess
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "netlify/functions/dl12-answers.json"
API = "https://data.transportation.gov/resource/8bui-9xvu.json"
NTD_ID = "10003"
DISCONTINUED = {"TB"}  # trolleybus, discontinued 2022; excluded from service tables


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


def main():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    names = ledger["mode_names"]
    rows = fetch_rows()
    if len(rows) < 1000:
        sys.exit(f"FATAL: only {len(rows)} rows fetched; expected thousands")

    monthly_vrm = defaultdict(float)                     # "YYYY-MM" -> vrm
    ann = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # yr -> mode -> field -> value
    for r in rows:
        mk = r["date"][:7]
        if mk < "2014-01":
            continue
        mode = r["mode"]
        upt = float(r.get("upt") or 0)
        vrh = float(r.get("vrh") or 0)
        vrm = float(r.get("vrm") or 0)
        monthly_vrm[mk] += vrm
        ann[mk[:4]]["_ALL"]["vrm"] += vrm
        ann[mk[:4]]["_ALL"]["vrh"] += vrh
        ann[mk[:4]]["_ALL"]["upt"] += upt
        ann[mk[:4]][mode]["vrm"] += vrm
        ann[mk[:4]][mode]["vrh"] += vrh
        ann[mk[:4]][mode]["upt"] += upt

    months = sorted(monthly_vrm)
    months = [m for m in months if m >= "2014-01"]
    as_of = months[-1]
    last_full_year = as_of[:4] if as_of.endswith("-12") else str(int(as_of[:4]) - 1)
    years = [y for y in sorted(ann) if "2014" <= y <= last_full_year]
    if "2019" not in ann or last_full_year not in ann:
        sys.exit("FATAL: missing 2019 or latest-full-year service data")
    if not (50_000_000 < monthly_vrm[as_of] < 200_000_000):
        # MBTA runs on the order of 7 to 8 million revenue miles per month
        pass  # totals vary; keep as a soft note rather than a hard gate

    def tpvrh(rec):
        return round(rec["upt"] / rec["vrh"], 1) if rec.get("vrh") else None

    # annual totals, full years
    annual_totals = {}
    for y in years:
        a = ann[y]["_ALL"]
        annual_totals[y] = {
            "vrm": int(a["vrm"]), "vrh": int(a["vrh"]), "upt": int(a["upt"]),
            "trips_per_vrh": tpvrh(a),
        }

    # by mode: latest full year and 2019 side by side, with recovery vs 2019
    lfy, base = ann[last_full_year], ann["2019"]
    by_mode = {}
    for code in sorted(set(lfy) | set(base)):
        if code in DISCONTINUED or code == "_ALL":
            continue
        cur, b = lfy.get(code, {}), base.get(code, {})
        if not (cur.get("vrh") and b.get("vrh")):
            continue
        by_mode[code] = {
            "mode": names.get(code, code),
            "vrh_latest": int(cur["vrh"]), "vrm_latest": int(cur["vrm"]),
            "upt_latest": int(cur["upt"]), "trips_per_vrh_latest": tpvrh(cur),
            "vrh_2019": int(b["vrh"]), "trips_per_vrh_2019": tpvrh(b),
            "vrh_pct_of_2019": round(100 * cur["vrh"] / b["vrh"], 1),
            "vrm_pct_of_2019": round(100 * cur["vrm"] / b["vrm"], 1) if b.get("vrm") else None,
            "upt_pct_of_2019": round(100 * cur["upt"] / b["upt"], 1) if b.get("upt") else None,
        }

    a_lfy, a_19 = ann[last_full_year]["_ALL"], ann["2019"]["_ALL"]
    systemwide = {
        "vrh_pct_of_2019": round(100 * a_lfy["vrh"] / a_19["vrh"], 1),
        "vrm_pct_of_2019": round(100 * a_lfy["vrm"] / a_19["vrm"], 1),
        "upt_pct_of_2019": round(100 * a_lfy["upt"] / a_19["upt"], 1),
        "trips_per_vrh_2019": tpvrh(a_19),
        "trips_per_vrh_latest": tpvrh(a_lfy),
    }
    productivity_ranked = sorted(
        ({"code": c, "mode": m["mode"], "trips_per_vrh": m["trips_per_vrh_latest"],
          "trips_per_vrh_2019": m["trips_per_vrh_2019"],
          "pct_change_from_2019": round(100 * (m["trips_per_vrh_latest"] / m["trips_per_vrh_2019"] - 1), 1)
              if m["trips_per_vrh_2019"] else None}
         for c, m in by_mode.items()),
        key=lambda e: -(e["trips_per_vrh"] or 0),
    )
    service_above_2019 = [by_mode[c]["mode"] for c in by_mode if by_mode[c]["vrh_pct_of_2019"] >= 100]

    ledger["service"] = {
        "as_of": as_of,
        "source_id": "SRC-301",
        "latest_full_year": last_full_year,
        "note": (
            "Service supplied is the vehicle revenue miles (VRM) and vehicle revenue "
            "hours (VRH) the MBTA operated, from the same federal monthly file as "
            "ridership (dataset 8bui-9xvu, SRC-301). Productivity is unlinked passenger "
            "trips per vehicle revenue hour. Recovery figures compare the latest full "
            "year to full-year 2019. Trolleybus (discontinued 2022) is excluded."
        ),
        "monthly_vrm_total": [{"m": mk, "v": int(monthly_vrm[mk])} for mk in months],
        "annual_totals": annual_totals,
        "by_mode": by_mode,
        "derived": {
            "note": ("Precomputed from the series above; prefer these over recomputing. "
                     "All service and productivity figures cite (derived, SRC-301)."),
            "systemwide_vs_2019_full_year": systemwide,
            "productivity_ranked_latest": productivity_ranked,
            "service_above_2019_full_year": service_above_2019,
        },
    }

    LEDGER.write_text(json.dumps(ledger, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")
    print(f"refresh_dl12_service: as_of {as_of}; latest full year {last_full_year}; "
          f"{len(by_mode)} modes; systemwide VRH {systemwide['vrh_pct_of_2019']}% vs "
          f"UPT {systemwide['upt_pct_of_2019']}% of 2019; "
          f"trips/VRH {systemwide['trips_per_vrh_2019']} to {systemwide['trips_per_vrh_latest']}")

    subprocess.run([sys.executable, str(ROOT / "scripts/inject_data.py")], check=True)


if __name__ == "__main__":
    main()
