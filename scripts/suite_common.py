"""Shared helpers for the 26-app suite: states, fetch, money, ledger I/O."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "suite" / "apps.json"
LEDGER_DIR = ROOT / "netlify" / "functions"
UA = "PioneerDataLabs/1.0 (datalabs@pioneerinstitute.org)"

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "US": "United States",
}

# FIPS used by BLS LAUS and Census BPS / PEP.
FIPS_TO_ST = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "00": "US",
}
ST_TO_FIPS = {v: k for k, v in FIPS_TO_ST.items()}

RANKED = [s for s in STATE_NAMES if s != "US"]
NAME_TO_ST = {v: k for k, v in STATE_NAMES.items()}
NAME_TO_ST.update({
    "District of Columbia": "DC",
    "D.C.": "DC",
    "Dist. Of Col.": "DC",
    "Dist. of Col.": "DC",
    "U.S. total": "US",
    "U.S. Total": "US",
    "United States": "US",
})
MONTHS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]
MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def load_apps():
    return json.loads((SUITE).read_text(encoding="utf-8"))["apps"]


def ledger_path(tool_id: str) -> Path:
    # DL-13 -> dl13-answers.json, matching dl01 through dl05.
    return LEDGER_DIR / f"{tool_id.lower().replace('-', '')}-answers.json"


def write_ledger(obj: dict) -> Path:
    path = ledger_path(obj["tool_id"])
    path.write_text(
        json.dumps(obj, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_text(url: str, timeout: int = 90) -> str:
    return fetch(url, timeout=timeout).decode("utf-8", "replace")


def commify(n) -> str:
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.1f}"
    return f"{int(round(n)):,}"


def usd_prose(n: float) -> str:
    sign = "\u2212" if n < 0 else ""
    a = abs(n)
    if a >= 1_000_000_000_000:
        return f"{sign}${a / 1_000_000_000_000:.2f} trillion"
    if a >= 1_000_000_000:
        return f"{sign}${a / 1_000_000_000:.2f} billion"
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.2f} million"
    return f"{sign}${a:,.0f}"


def clean_geo_name(s) -> str:
    if s is None:
        return ""
    t = str(s).replace("\xa0", " ").replace("\n", " ").replace("*", "")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"/[a-z]+$", "", t, flags=re.I).strip()
    return t


def geo_to_st(name):
    t = clean_geo_name(name)
    if t in NAME_TO_ST:
        return NAME_TO_ST[t]
    low = t.lower()
    for k, v in STATE_NAMES.items():
        if v.lower() == low:
            return k
    return None


def parse_num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v).replace(",", "").replace("$", "").replace("\xa0", " ").strip()
    if s in ("", "-", "--", "\u2013", "\u2014", "\u2020", "#", "NA", "N/A", "X", "*", "na"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def rank_named(values: dict, higher_is_better=True, st_key=None):
    """values: label -> number. For towns, departments, or tax types."""
    items = [(k, v) for k, v in values.items() if v is not None]
    items.sort(key=lambda x: x[1], reverse=higher_is_better)
    out = []
    for i, (key, v) in enumerate(items, 1):
        st = st_key(key) if st_key else str(key)[:8]
        out.append({"st": st, "name": key, "v": v, "rank": i, "n": len(items)})
    return out


def pct(n) -> str:
    if n is None:
        return ""
    sign = "+" if n > 0 else ""
    return f"{sign}{n:.1f}%"


def yoy_pct(new, old):
    if old in (None, 0):
        return None
    return round((new - old) / old * 100, 1)


def rank_rows(values: dict, higher_is_better=True):
    """values: st -> number. Returns ranked list excluding US."""
    items = [(st, values[st]) for st in RANKED if st in values and values[st] is not None]
    items.sort(key=lambda x: x[1], reverse=higher_is_better)
    out = []
    for i, (st, v) in enumerate(items, 1):
        out.append({"st": st, "name": STATE_NAMES[st], "v": v, "rank": i, "n": len(items)})
    return out


REVISED = "Aug 15, 2026"


def base_ledger(app, status, as_of, vintage_note, extra):
    out = {
        "tool_id": app["id"],
        "title": app["title"],
        "slug": app["slug"],
        "vertical": app["vertical"],
        "group": app["group"],
        "status": status,
        "as_of": as_of,
        "scope": app["scope"],
        "exclusions": app["exclusions"],
        "heritage": app["heritage"],
        "replaces": app["replaces"],
        "vintage_note": vintage_note,
        "source_id_map": {
            s["id"]: {
                "name": s["name"],
                "cadence": s["cadence"],
                "url": s["url"],
                "supports": app["scope"],
            }
            for s in app["sources"]
        },
        "page": {"revised": REVISED, "version": "0.1" if status == "live" else "0.0"},
        "geo": app["g"],
        "q": app["q"],
    }
    out.update(extra)
    return out


def stub_ledger(app):
    return base_ledger(
        app,
        "build",
        None,
        "Ledger pending. Sources are inventoried; figures will be compiled from "
        "those files on a later refresh. This page does not invent numbers.",
        {
            "pending": True,
            "pending_plan": (
                "A later refresh_suite.py pass will fetch the sources in "
                "source_id_map, recompute a ranked state (or municipal) table, "
                "and clear this flag. Until then the page publishes scope and "
                "sources only."
            ),
            "rows": [],
            "trend": {},
            "derived": {},
            "kpis": [],
        },
    )


def finish_live(app, *, as_of, as_of_label, vintage_note, metric, metric_label,
                unit, lead, kpis, ranked, trend, latest, src_note, extra=None):
    derived = {
        "note": f"Prefer these over recomputing. Ranks cite (derived, {src_note}).",
        "highest_five": ranked[:5],
        "lowest_five": list(reversed(ranked[-5:])) if ranked else [],
        "n_ranked": ranked[0]["n"] if ranked else 0,
    }
    ma = next((r for r in ranked if r.get("st") == "MA"), None)
    if ma:
        derived["massachusetts_rank"] = ma["rank"]
    payload = {
        "pending": False,
        "metric": metric,
        "metric_label": metric_label,
        "unit": unit,
        "data_month": as_of,
        "data_month_label": as_of_label,
        "lead": lead,
        "kpis": kpis,
        "latest": latest,
        "rows": ranked,
        "trend": trend or {},
        "derived": derived,
    }
    if extra:
        payload.update(extra)
        if "derived" in extra:
            derived.update(extra["derived"])
            payload["derived"] = derived
    return base_ledger(app, "live", as_of, vintage_note, payload)
