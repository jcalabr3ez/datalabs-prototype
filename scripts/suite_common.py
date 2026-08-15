"""Shared helpers for the 26-app suite: states, fetch, money, ledger I/O."""
from __future__ import annotations

import json
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
    if a >= 1_000_000_000:
        return f"{sign}${a / 1_000_000_000:.2f} billion"
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.2f} million"
    return f"{sign}${a:,.0f}"


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
