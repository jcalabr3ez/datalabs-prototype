#!/usr/bin/env python3
"""Rebuild the DL-11 340B ledger from local primary extracts.

OPAIS has no public download URL (the Reports page is a Blazor click-through).
Put the Covered Entity Daily Export JSON at OPAIS_CE_JSON or
/tmp/opais-ce-daily.json, the CMS Hospital Provider Cost Report PUF CSVs in
HCRIS_DIR or /tmp/hcris, and the Census 2024 SLDL-to-ZCTA file at
CENSUS_SLDL_ZCTA or /tmp/census/tab20_sldl202420_zcta520_natl.txt.

If those files are missing and a live ledger already exists, that ledger is
kept so the monthly suite refresh does not restub the page.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_common import (
    FIPS_TO_ST,
    STATE_NAMES,
    commify,
    finish_live,
    ledger_path,
    parse_num,
    rank_rows,
    usd_prose,
)

FILE_DATE = date(2026, 8, 15)
PAGE_REVISED = "Aug 16, 2026"
HCRIS_YEARS = list(range(2011, 2024))
HOSPITAL_TYPES = {"DSH", "CAH", "RRC", "SCH", "PED", "CAN"}
CCN_RE = re.compile(r"^([A-Z]+)(\d{6})(?:-\d+)?$")
ZIP_RE = re.compile(r"^(\d{5})")

TYPE_LABELS = {
    "DSH": "Disproportionate share hospitals",
    "CAH": "Critical access hospitals",
    "RRC": "Rural referral centers",
    "SCH": "Sole community hospitals",
    "PED": "Children's hospitals",
    "CAN": "Free-standing cancer hospitals",
    "CH": "Consolidated health centers",
    "FQHC": "Federally qualified health centers",
    "FQHCLA": "FQHC look-alikes",
    "STD": "Sexually transmitted disease clinics",
    "FP": "Family planning clinics",
    "TB": "Tuberculosis clinics",
    "HIV": "HIV clinics",
    "RW": "Ryan White clinics",
    "RWH": "Ryan White clinics",
    "RWGA": "Ryan White clinics",
    "HM": "Hemophilia treatment centers",
    "BL": "Black lung clinics",
    "URB": "Urban Indian health",
    "UI": "Urban Indian health",
    "IHS": "Indian Health Service",
    "TH": "Tribal hospitals",
    "NH": "Native Hawaiian health",
}

DEFAULT_OPAIS = Path("/tmp/opais-ce-daily.json")
DEFAULT_HCRIS = Path("/tmp/hcris")
DEFAULT_CENSUS = Path("/tmp/census/tab20_sldl202420_zcta520_natl.txt")


def _path(env_key, default):
    raw = os.environ.get(env_key)
    return Path(raw) if raw else default


def parse_day(raw):
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def is_true(v):
    if v is True:
        return True
    return str(v or "").strip().upper() in {"TRUE", "YES", "Y", "1"}


def zip5(raw):
    if raw is None:
        return ""
    m = ZIP_RE.match(str(raw).strip())
    return m.group(1) if m else ""


def ccn_from_id(id340b, entity_type):
    if entity_type not in HOSPITAL_TYPES:
        return None
    m = CCN_RE.match(str(id340b or "").strip())
    return m.group(2) if m else None


def participating(ent):
    return is_true(ent.get("participating"))


def keep_existing(reason):
    path = ledger_path("DL-11")
    if path.exists():
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("status") == "live":
            print(f"WARN: {reason}; keeping published DL-11 ledger")
            return obj
    sys.exit(f"FATAL: {reason}")


def load_opais(path):
    print(f"  OPAIS {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    ents = data.get("coveredEntities") if isinstance(data, dict) else data
    if not isinstance(ents, list) or not ents:
        sys.exit("FATAL: OPAIS file has no coveredEntities")
    return ents


def load_zcta_sldl(path):
    print(f"  Census SLDL-ZCTA {path}")
    best = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="|")
        for rec in reader:
            geoid = (rec.get("GEOID_SLDL2024_20") or "").strip()
            zcta = (rec.get("GEOID_ZCTA5_20") or "").strip()
            if not geoid or not zcta:
                continue
            st = FIPS_TO_ST.get(geoid[:2])
            if not st:
                continue
            land = parse_num(rec.get("AREALAND_PART")) or 0
            water = parse_num(rec.get("AREAWATER_PART")) or 0
            score = land if land > 0 else water
            name = (rec.get("NAMELSAD_SLDL2024_20") or "").strip() or geoid
            prev = best.get(zcta)
            if prev is None or score > prev[0]:
                best[zcta] = (score, geoid, name, st)
    if len(best) < 10000:
        sys.exit(f"FATAL: Census SLDL-ZCTA file looked empty ({len(best)} ZCTAs)")
    return {z: {"id": g, "name": n, "st": st} for z, (_s, g, n, st) in best.items()}


def load_hcris_year(path):
    by_ccn = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "Cost of Charity Care" not in (reader.fieldnames or []):
            return {}
        for rec in reader:
            ccn = str(rec.get("Provider CCN") or "").strip()
            if not ccn:
                continue
            ccn = ccn.zfill(6)
            costs = parse_num(rec.get("Total Costs"))
            if costs is None or costs <= 0:
                continue
            charity = parse_num(rec.get("Cost of Charity Care"))
            if charity is None:
                charity = 0.0
            fy = parse_day(rec.get("Fiscal Year End Date"))
            prev = by_ccn.get(ccn)
            if prev and prev["fy"] and fy and fy < prev["fy"]:
                continue
            st = (rec.get("State Code") or "").strip().upper()
            if st not in STATE_NAMES or st == "US":
                continue
            by_ccn[ccn] = {
                "st": st,
                "charity": charity,
                "costs": costs,
                "fy": fy,
            }
    return by_ccn


def share_pct(charity, costs):
    if not costs:
        return None
    return round(charity / costs * 100, 2)


def pack_rank(ranked, extra=None):
    extra = extra or {}
    out = []
    for rec in ranked:
        row = dict(rec)
        more = extra.get(rec["st"]) or {}
        row.update(more)
        out.append(row)
    return out


def cell(ranked, st):
    for rec in ranked:
        if rec.get("st") == st:
            return rec
    return None


def pharmacy_active(pharm, as_of):
    begin = parse_day(pharm.get("beginDate"))
    if begin and begin > as_of:
        return False
    end = parse_day(pharm.get("terminationDate"))
    if end and end <= as_of:
        return False
    return True


def build(app):
    opais_path = _path("OPAIS_CE_JSON", DEFAULT_OPAIS)
    hcris_dir = _path("HCRIS_DIR", DEFAULT_HCRIS)
    census_path = _path("CENSUS_SLDL_ZCTA", DEFAULT_CENSUS)
    if not opais_path.exists():
        return keep_existing(f"OPAIS CE daily JSON not at {opais_path}")
    if not hcris_dir.exists():
        return keep_existing(f"HCRIS directory not at {hcris_dir}")
    if not census_path.exists():
        return keep_existing(f"Census SLDL-ZCTA file not at {census_path}")

    as_of = FILE_DATE
    ents = load_opais(opais_path)
    zcta_map = load_zcta_sldl(census_path)

    sites_by_st = defaultdict(int)
    types = defaultdict(int)
    start_years = []
    start_by_st = defaultdict(list)
    hospital_ccns = set()
    unique_pharm = {}
    pharm_by_st = defaultdict(set)
    district_pharm = defaultdict(set)
    unmapped = 0
    mapped = 0
    n_part = 0

    for ent in ents:
        if not participating(ent):
            continue
        n_part += 1
        addr = ent.get("streetAddress") or {}
        st = (addr.get("state") or "").strip().upper()
        if st in STATE_NAMES and st != "US":
            sites_by_st[st] += 1
        etype = (ent.get("entityType") or "").strip().upper()
        types[etype] += 1
        started = parse_day(ent.get("participatingStartDate"))
        if started:
            start_years.append(started.year)
            if st in STATE_NAMES and st != "US":
                start_by_st[st].append(started.year)
        ccn = ccn_from_id(ent.get("id340B"), etype)
        if ccn:
            hospital_ccns.add(ccn)
        for pharm in ent.get("contractPharmacies") or []:
            if not pharmacy_active(pharm, as_of):
                continue
            pid = pharm.get("pharmacyId")
            paddr = pharm.get("address") or {}
            pst = (paddr.get("state") or "").strip().upper()
            pzip = zip5(paddr.get("zip"))
            key = str(pid) if pid not in (None, "") else "|".join([
                str(pharm.get("name") or "").strip().upper(),
                pzip,
                pst,
            ])
            unique_pharm[key] = (pst, pzip)
            if pst in STATE_NAMES and pst != "US":
                pharm_by_st[pst].add(key)
            if pzip and pzip in zcta_map:
                dist = zcta_map[pzip]
                district_pharm[(dist["st"], dist["id"], dist["name"])].add(key)
                mapped += 1
            else:
                unmapped += 1

    if n_part < 1000:
        sys.exit(f"FATAL: only {n_part} participating 340B entities")

    site_values = {st: sites_by_st.get(st, 0) for st in STATE_NAMES if st != "US"}
    ranked = pack_rank(
        rank_rows(site_values, higher_is_better=True),
        {st: {"pharmacies": len(pharm_by_st.get(st, ()))} for st in site_values},
    )
    pharm_values = {st: len(pharm_by_st.get(st, ())) for st in site_values}
    pharm_ranked = rank_rows(pharm_values, higher_is_better=True)

    def cum_from(years):
        counts = defaultdict(int)
        for y in years:
            counts[y] += 1
        running = 0
        out = []
        for y in range(min(counts), as_of.year + 1):
            running += counts.get(y, 0)
            out.append({"y": y, "v": running})
        return out

    trend = {
        "US": cum_from(start_years),
        "MA": cum_from(start_by_st.get("MA") or [as_of.year]),
        "FL": cum_from(start_by_st.get("FL") or [as_of.year]),
    }

    type_rows = []
    for code, n in sorted(types.items(), key=lambda kv: (-kv[1], kv[0])):
        if not code:
            continue
        type_rows.append({
            "st": code,
            "name": TYPE_LABELS.get(code, code),
            "code": code,
            "v": n,
        })
    for i, rec in enumerate(type_rows, 1):
        rec["rank"] = i
        rec["n"] = len(type_rows)

    charity_by_year = {}
    split_2023 = None
    for year in HCRIS_YEARS:
        csv_path = hcris_dir / f"CostReport_{year}_Final.csv"
        if not csv_path.exists():
            print(f"  skip HCRIS {year}: missing {csv_path.name}")
            continue
        print(f"  HCRIS {year} {csv_path}")
        by_ccn = load_hcris_year(csv_path)
        if not by_ccn:
            continue
        st_charity = defaultdict(float)
        st_costs = defaultdict(float)
        us_charity = 0.0
        us_costs = 0.0
        b_charity = o_charity = 0.0
        b_costs = o_costs = 0.0
        n_340b = n_other = 0
        for ccn, rec in by_ccn.items():
            st_charity[rec["st"]] += rec["charity"]
            st_costs[rec["st"]] += rec["costs"]
            us_charity += rec["charity"]
            us_costs += rec["costs"]
            if year == 2023:
                if ccn in hospital_ccns:
                    b_charity += rec["charity"]
                    b_costs += rec["costs"]
                    n_340b += 1
                else:
                    o_charity += rec["charity"]
                    o_costs += rec["costs"]
                    n_other += 1
        shares = {
            st: share_pct(st_charity[st], st_costs[st])
            for st in st_costs
            if st_costs[st] > 0
        }
        ranked_year = pack_rank(
            rank_rows(shares, higher_is_better=True),
            {
                st: {
                    "charity": round(st_charity[st], 0),
                    "costs": round(st_costs[st], 0),
                }
                for st in shares
            },
        )
        charity_by_year[year] = {
            "rows": ranked_year,
            "us": {
                "v": share_pct(us_charity, us_costs),
                "charity": round(us_charity, 0),
                "costs": round(us_costs, 0),
            },
        }
        if year == 2023:
            split_2023 = {
                "340b": {
                    "n": n_340b,
                    "share_pct": share_pct(b_charity, b_costs),
                    "charity": round(b_charity, 0),
                    "costs": round(b_costs, 0),
                },
                "other": {
                    "n": n_other,
                    "share_pct": share_pct(o_charity, o_costs),
                    "charity": round(o_charity, 0),
                    "costs": round(o_costs, 0),
                },
            }

    if 2023 not in charity_by_year:
        sys.exit("FATAL: CMS 2023 Hospital Provider Cost Report PUF missing or empty")

    charity_2023 = charity_by_year[2023]
    charity_rows = charity_2023["rows"]
    charity_trend = {"US": [], "MA": [], "FL": []}
    for year in sorted(charity_by_year):
        block = charity_by_year[year]
        charity_trend["US"].append({"y": year, "v": block["us"]["v"]})
        ma_c = cell(block["rows"], "MA")
        fl_c = cell(block["rows"], "FL")
        if ma_c:
            charity_trend["MA"].append({"y": year, "v": ma_c["v"]})
        if fl_c:
            charity_trend["FL"].append({"y": year, "v": fl_c["v"]})

    district_rows = []
    for (st, geoid, name), pids in district_pharm.items():
        district_rows.append({
            "st": st,
            "id": geoid,
            "name": name,
            "v": len(pids),
        })
    district_rows.sort(key=lambda r: (-r["v"], r["st"], r["name"]))
    for i, rec in enumerate(district_rows, 1):
        rec["rank"] = i
        rec["n"] = len(district_rows)
    ma_districts = [r for r in district_rows if r["st"] == "MA"]
    fl_districts = [r for r in district_rows if r["st"] == "FL"]

    ma = cell(ranked, "MA")
    fl = cell(ranked, "FL")
    hi = ranked[0]
    lo = ranked[-1]
    us_sites = n_part
    us_pharm = len(unique_pharm)
    ma_pharm = cell(pharm_ranked, "MA")
    fl_pharm = cell(pharm_ranked, "FL")
    ma_char = cell(charity_rows, "MA")
    fl_char = cell(charity_rows, "FL")
    hi_char = charity_rows[0]
    lo_char = charity_rows[-1]
    us_char = charity_2023["us"]

    type_top = ", ".join(
        f"{r['name']} {commify(r['v'])}" for r in type_rows[:3]
    )
    lead = (
        f"{commify(us_sites)} 340B covered-entity sites are participating on the "
        f"HRSA OPAIS daily export dated {as_of.isoformat()} (SRC-611-01). "
        f"{hi['name']} has the most sites at {commify(hi['v'])}; "
        f"{lo['name']} has the fewest at {commify(lo['v'])}. "
        f"Massachusetts ranks {ma['rank']} of {ma['n']} at {commify(ma['v'])} "
        f"sites; Florida ranks {fl['rank']} of {fl['n']} at {commify(fl['v'])} "
        f"(derived, SRC-611-01)."
    )
    vintage_note = (
        f"Rebuilt {PAGE_REVISED} from the HRSA OPAIS Covered Entity Daily "
        f"Export JSON dated {as_of.isoformat()}, the CMS Hospital Provider "
        f"Cost Report PUF for fiscal years 2011 through 2023 (Worksheet S-10 "
        f"cost of charity care over total costs, the public file behind RAND "
        f"TL-303), and the Census 2024 state house (SLDL) to 2020 ZCTA "
        f"relationship file. Participating counts are current sites, not a "
        f"reconstructed historical stock: the start-year series is the number "
        f"of currently participating sites that had a participating start date "
        f"on or before that year. Unique pharmacies are distinct pharmacyId "
        f"values on an active contract (begin date on or before the file date, "
        f"and no termination date on or before the file date). District "
        f"assignment uses the ZCTA's majority land-area 2024 state house "
        f"district. A ZIP can cross district lines. Refresh: download the "
        f"Covered Entity Daily Export (JSON) from https://340bopais.hrsa.gov/reports, "
        f"the CMS Hospital Provider Cost Report PUF CSVs, and the Census "
        f"tab20_sldl202420_zcta520_natl.txt file, then run scripts/build_dl11.py."
    )
    kpis = []
    latest = {
        "us": {"v": us_sites, "pharmacies": us_pharm},
        "ma": {
            "v": ma["v"],
            "rank": ma["rank"],
            "n": ma["n"],
            "pharmacies": ma.get("pharmacies"),
        },
        "fl": {
            "v": fl["v"],
            "rank": fl["rank"],
            "n": fl["n"],
            "pharmacies": fl.get("pharmacies"),
        },
        "highest": {"st": hi["st"], "name": hi["name"], "v": hi["v"]},
        "lowest": {"st": lo["st"], "name": lo["name"], "v": lo["v"]},
    }
    ledger = finish_live(
        app,
        as_of=as_of.isoformat(),
        as_of_label="August 15, 2026",
        vintage_note=vintage_note,
        metric="participating_covered_entities",
        metric_label="Participating 340B covered-entity sites",
        unit="sites",
        lead=lead,
        kpis=kpis,
        ranked=ranked,
        trend=trend,
        latest=latest,
        src_note="SRC-611-01",
        extra={
            "derived": {
                "type_mix_note": type_top,
                "secondary": {
                    "type_mix": {
                        "label": "Participating 340B sites by entity type",
                        "unit": "sites",
                        "src": "SRC-611-01",
                        "as_of_label": "August 15, 2026",
                        "rows": type_rows,
                    },
                    "pharmacies_by_state": {
                        "label": "Unique active 340B contract pharmacies",
                        "unit": "pharmacies",
                        "src": "SRC-611-01",
                        "as_of_label": "August 15, 2026",
                        "rows": pharm_ranked,
                        "us": {"v": us_pharm},
                        "ma": ma_pharm,
                        "fl": fl_pharm,
                        "highest": {
                            "st": pharm_ranked[0]["st"],
                            "name": pharm_ranked[0]["name"],
                            "v": pharm_ranked[0]["v"],
                        },
                        "lowest": {
                            "st": pharm_ranked[-1]["st"],
                            "name": pharm_ranked[-1]["name"],
                            "v": pharm_ranked[-1]["v"],
                        },
                        "note": (
                            "Unique pharmacyId values on an active contract "
                            "with a participating covered entity. One pharmacy "
                            "can contract with many entities."
                        ),
                    },
                    "charity_care": {
                        "label": "Hospital charity-care share of total costs, 2023",
                        "unit": "percent of total costs",
                        "src": "SRC-611-02",
                        "method": "SRC-611-04",
                        "as_of_label": "Fiscal year 2023",
                        "year": 2023,
                        "rows": charity_rows,
                        "us": us_char,
                        "ma": ma_char,
                        "fl": fl_char,
                        "highest": {
                            "st": hi_char["st"],
                            "name": hi_char["name"],
                            "v": hi_char["v"],
                        },
                        "lowest": {
                            "st": lo_char["st"],
                            "name": lo_char["name"],
                            "v": lo_char["v"],
                        },
                        "trend": charity_trend,
                        "hospital_split_2023": split_2023,
                        "note": (
                            "CMS Hospital Provider Cost Report PUF, Worksheet "
                            "S-10 cost of charity care divided by total costs. "
                            "That is the public file behind RAND TL-303. One "
                            "row per provider CCN, latest fiscal-year end in "
                            "that PUF year. 340B hospitals are participating "
                            "DSH, CAH, RRC, SCH, PED, and CAN sites matched "
                            "on the six-digit CCN inside the 340B ID."
                        ),
                    },
                    "legislative": {
                        "label": "Unique 340B pharmacies by 2024 state house district",
                        "unit": "pharmacies",
                        "src": "SRC-611-03",
                        "as_of_label": "2024 state house districts",
                        "chamber": "2024 state house (SLDL)",
                        "rows": district_rows,
                        "district_rows": ma_districts + fl_districts,
                        "ma_districts": ma_districts,
                        "fl_districts": fl_districts,
                        "by_state": pharm_ranked,
                        "mapped_contracts": mapped,
                        "unmapped_contracts": unmapped,
                        "unique_pharmacies": us_pharm,
                        "districts_with_pharmacies": len(district_rows),
                        "ma": {
                            "v": len(ma_districts),
                            "pharmacies": (ma_pharm or {}).get("v"),
                        },
                        "fl": {
                            "v": len(fl_districts),
                            "pharmacies": (fl_pharm or {}).get("v"),
                        },
                        "note": (
                            "The 2023 Pioneer mapping geocoded pharmacy "
                            "addresses onto state legislative districts. This "
                            "rebuild assigns each pharmacy ZIP to the 2024 "
                            "state house district that holds the majority of "
                            "that ZCTA's land area. A ZIP can cross district "
                            "lines. Unmapped ZIPs have no 2020 ZCTA in the "
                            "Census file (post-office boxes and some unique "
                            "ZIPs)."
                        ),
                    },
                },
            }
        },
    )
    ledger["page"] = {"revised": PAGE_REVISED, "version": "1.0"}
    print(
        f"  participating {us_sites:,} pharmacies {us_pharm:,} "
        f"districts {len(district_rows):,} "
        f"charity US {us_char['v']}% "
        f"MA sites {ma['v']:,} FL sites {fl['v']:,}"
    )
    return ledger


def main():
    from suite_common import load_apps, write_ledger

    apps = load_apps()
    app = next(a for a in apps if a["id"] == "DL-11")
    ledger = build(app)
    path = write_ledger(ledger)
    print(f"wrote {path} status={ledger.get('status')} as_of={ledger.get('as_of')}")


if __name__ == "__main__":
    main()
