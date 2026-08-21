#!/usr/bin/env python3
"""Compare high-cadence publisher files to the vintages in the ledgers.

Prints one row per source. Exit 1 when a reachable file is newer than the
ledger. Does not write ledgers. Does not invent figures.

This is the latest-release check, not the age gate in check_freshness.py.
A ledger can be inside its day limit and still be a month behind the file.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from calendar import monthrange
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_common import (  # noqa: E402
    FIPS_TO_ST,
    ROOT,
    UA,
    fetch,
    fetch_text,
    ledger_path,
    load_apps,
)

TODAY = date.today().isoformat()

URL_BFS = "https://www.census.gov/econ/bfs/csv/bfs_monthly.csv"
URL_LAUS = "https://download.bls.gov/pub/time.series/la/la.data.3.AllStatesS"
URL_BPS = "https://www2.census.gov/econ/bps/State/st{yy}{mm}y.txt"
URL_NTD = "https://data.transportation.gov/resource/8bui-9xvu.json"
URL_UI = "https://oui.doleta.gov/unemploy/csv/ar539.csv"
URL_QTAX = "https://www2.census.gov/programs-surveys/qtax/tables/2026/q{q}t3.xlsx"
URL_CITIZENS = "https://www.citizensfla.com/policies-in-force"
URL_CTHRU = "https://cthru.data.socrata.com/resource/pni4-392n.json"

MONTHS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]


def load_ledger(tid):
    path = ledger_path(tid)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ym(value):
    """Normalize a ledger vintage to YYYY-MM when it is a month."""
    if not value:
        return ""
    s = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return s
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s[:7]
    months = {
        "jan": "01", "january": "01", "feb": "02", "february": "02",
        "mar": "03", "march": "03", "apr": "04", "april": "04",
        "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
        "aug": "08", "august": "08", "sep": "09", "september": "09",
        "oct": "10", "october": "10", "nov": "11", "november": "11",
        "dec": "12", "december": "12",
    }
    parts = s.replace(",", " ").split()
    if len(parts) >= 2:
        mon = months.get(parts[0].lower())
        year = re.sub(r"\D", "", parts[1])
        if mon and len(year) == 4:
            return f"{year}-{mon}"
    if re.fullmatch(r"\d{4} Q[1-4]", s):
        q = int(s[-1])
        return f"{s[:4]}-Q{q}"
    return s


def cmp_period(file_p, ledger_p):
    if not file_p or file_p.startswith("err:") or file_p.startswith("unreadable"):
        return "probe-failed"
    if not ledger_p:
        return "no-ledger"
    if file_p == ledger_p:
        return "current"
    if file_p > ledger_p:
        return "behind"
    return "ahead-of-file"


def row(tool, source, ledger, file_latest, note=""):
    status = cmp_period(file_latest, ledger)
    return {
        "tool": tool,
        "source": source,
        "ledger": ledger,
        "file": file_latest,
        "status": status,
        "note": note,
    }


def probe_bfs():
    text = fetch_text(URL_BFS, timeout=60)
    rows = list(csv.DictReader(io.StringIO(text)))
    last = None
    for r in rows:
        if r.get("sa") != "A" or r.get("naics_sector") != "TOTAL":
            continue
        if r.get("series") != "BA_BA" or r.get("geo") != "US":
            continue
        try:
            year = int(r.get("year"))
        except (TypeError, ValueError):
            continue
        for i, key in enumerate(MONTHS, 1):
            raw = (r.get(key) or "").strip()
            if not raw:
                continue
            cand = f"{year}-{i:02d}"
            if last is None or cand > last:
                last = cand
    led = load_ledger("DL-13")
    return row(
        "DL-13", "Census BFS BA_BA SA (SRC-613-01)",
        ym(led.get("data_month") or led.get("as_of")),
        last or "unreadable",
        "seasonally adjusted TOTAL applications",
    )


def probe_laus():
    text = fetch_text(URL_LAUS, timeout=180)
    latest = None
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        sid = parts[0].strip()
        if not (sid.startswith("LASST") and sid.endswith("0000000000003") and len(sid) == 20):
            continue
        if FIPS_TO_ST.get(sid[5:7]) in (None, "US"):
            continue
        period = parts[2].strip()
        if not period.startswith("M"):
            continue
        raw = parts[3].strip()
        if raw in ("", "-"):
            continue
        cand = f"{int(parts[1].strip())}-{int(period[1:]):02d}"
        if latest is None or cand > latest:
            latest = cand
    led = load_ledger("DL-14")
    return row(
        "DL-14", "BLS LAUS statewide SA rate (SRC-614-01)",
        ym(led.get("data_month") or led.get("as_of")),
        latest or "unreadable",
        "measure 03, all states and D.C.",
    )


def probe_ui():
    text = fetch_text(URL_UI, timeout=90)
    latest = None
    for r in csv.DictReader(io.StringIO(text)):
        week = (r.get("rptdate") or "")[:10]
        if week and (latest is None or week > latest):
            latest = week
    led = load_ledger("DL-14")
    sec = ((led.get("derived") or {}).get("secondary") or {})
    ui = sec.get("ui_initial_claims") or sec.get("ui_claims") or {}
    ledger_week = ui.get("as_of_label") or ""
    return row(
        "DL-14", "DOL ETA 539 UI claims (SRC-614-03)",
        ledger_week,
        latest or "unreadable",
        "companion series on State Unemployment; not the hero vintage",
    )


def _bps_has_states(text):
    n = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 17:
            n += 1
    return n >= 50


def probe_bps():
    found = None
    # Walk backward from the current calendar month. State YTD files
    # usually trail the national release by a few days.
    today = date.today()
    year, month = today.year, today.month
    checked = []
    for _ in range(6):
        url = URL_BPS.format(yy=f"{year % 100:02d}", mm=f"{month:02d}")
        label = f"{year}-{month:02d}"
        try:
            text = fetch_text(url, timeout=30)
        except urllib.error.HTTPError as e:
            checked.append(f"{label} HTTP {e.code}")
        except Exception as e:
            checked.append(f"{label} {type(e).__name__}")
        else:
            if _bps_has_states(text):
                found = label
                break
            checked.append(f"{label} empty")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    led = load_ledger("DL-16")
    return row(
        "DL-16", "Census BPS state YTD (SRC-616-01)",
        ym(led.get("data_month") or led.get("as_of")),
        found or "unreadable",
        "; ".join(checked[:3]) if not found or found != ym(led.get("data_month")) else "state year-to-date file",
    )


def probe_ntd(tool, ntd_id=None):
    params = {"$select": "max(date) as d"}
    if ntd_id:
        params["ntd_id"] = ntd_id
    url = URL_NTD + "?" + urllib.parse.urlencode(params)
    payload = json.loads(fetch(url, timeout=60).decode("utf-8", "replace"))
    date_s = (payload[0].get("d") or "")[:10]
    file_ym = date_s[:7] if date_s else "unreadable"
    led = load_ledger(tool)
    src = "FTA NTD monthly ridership (SRC-622-01)" if tool == "DL-22" else "FTA NTD MBTA (SRC-301)"
    note = f"max(date)={date_s}" + (f", ntd_id={ntd_id}" if ntd_id else ", all agencies")
    return row(tool, src, ym(led.get("data_month") or led.get("as_of")), file_ym, note)


def probe_qtax():
    found = None
    checked = []
    for q in (4, 3, 2, 1):
        url = URL_QTAX.format(q=q)
        try:
            data = fetch(url, timeout=30)
        except urllib.error.HTTPError as e:
            checked.append(f"Q{q} HTTP {e.code}")
            continue
        except Exception as e:
            checked.append(f"Q{q} {type(e).__name__}")
            continue
        if len(data) > 1000 and data[:2] == b"PK":
            found = f"2026-Q{q}"
            break
        checked.append(f"Q{q} not xlsx")
    led = load_ledger("DL-29")
    ledger = ym(led.get("as_of"))
    if ledger == "2026-03":
        ledger = "2026-Q1"
    elif ledger == "2026-06":
        ledger = "2026-Q2"
    elif ledger == "2026-09":
        ledger = "2026-Q3"
    elif ledger == "2026-12":
        ledger = "2026-Q4"
    note = "q1t3 / q2t3 workbook; DL-28 shares this file"
    if checked:
        note = note + "; " + ", ".join(checked[:3])
    return row("DL-28/29", "Census QTAX table 3 (SRC-629-01)", ledger, found or "unreadable", note)


def _pif_month_end_slug(year, month):
    last = monthrange(year, month)[1]
    return f"{year}{month:02d}{last:02d}-policies-in-force"


def _http_status(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200) or 200)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def probe_citizens():
    led = load_ledger("DL-02")
    series = led.get("citizens_policies_monthly") or []
    ledger = series[-1]["m"] if series else ym(led.get("as_of"))
    # Fail when the next month-end PIF page is already live.
    # Skip the probe while that month-end is still in the future.
    try:
        y, m = [int(x) for x in str(ledger).split("-")]
    except ValueError:
        y = m = None
    if y and m:
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        next_end = date(ny, nm, monthrange(ny, nm)[1])
        if next_end <= date.today():
            next_url = (
                "https://www.citizensfla.com/-/"
                + _pif_month_end_slug(ny, nm)
            )
            try:
                code = _http_status(next_url)
            except Exception as e:
                code = None
                next_err = type(e).__name__
            else:
                next_err = None
            if code == 200:
                return row(
                    "DL-02", "Citizens Policies in Force (SRC-FL-02)",
                    ledger, f"{ny}-{nm:02d}",
                    f"newer month-end page is live: {next_url}",
                )
            if next_err:
                return row(
                    "DL-02", "Citizens Policies in Force (SRC-FL-02)",
                    ledger, f"err:{next_err}",
                    f"could not probe {next_url}",
                )
    try:
        html = fetch_text(URL_CITIZENS, timeout=45)
    except Exception as e:
        return row(
            "DL-02", "Citizens Policies in Force (SRC-FL-02)",
            ledger, f"err:{type(e).__name__}",
            "flagship research pass; HTML is not a monthly file",
        )
    hit = re.search(
        r"Policies in Force as of ([A-Za-z]+ \d{1,2}, \d{4}):\s*([\d,]+)",
        html,
    )
    if not hit:
        return row(
            "DL-02", "Citizens Policies in Force (SRC-FL-02)",
            ledger, "unreadable:html",
            "research pass; page loaded without a Policies in Force as-of line",
        )
    when, count = hit.group(1), hit.group(2)
    day = int(re.search(r"\d+", when).group())
    page_ym = ym(when)
    # The ledger is month-end. Mid-month website prints are not a new vintage.
    if day >= 28 and page_ym > ledger:
        return row(
            "DL-02", "Citizens Policies in Force (SRC-FL-02)",
            ledger, page_ym,
            f"month-end print on the page: {when} = {count}",
        )
    return row(
        "DL-02", "Citizens Policies in Force (SRC-FL-02)",
        ledger, ledger,
        f"ledger is month-end; page also shows a mid-month snapshot {when} = {count}",
    )


def probe_cthru():
    url = URL_CTHRU + "?" + urllib.parse.urlencode({
        "$select": "year,count(*) as n",
        "$group": "year",
        "$order": "year",
    })
    try:
        years = json.loads(fetch(url, timeout=60).decode("utf-8", "replace"))
    except Exception as e:
        led = load_ledger("DL-05")
        return row(
            "DL-05", "CTHRU retiree payroll (SRC-503)",
            str(led.get("search_year") or ym(led.get("as_of"))),
            f"err:{type(e).__name__}",
            "as_of is the pull month, not the retiree year",
        )
    latest_year = None
    for r in years:
        y = str(r.get("year") or "").strip()
        if y.isdigit():
            latest_year = y
    led = load_ledger("DL-05")
    search = str(led.get("search_year") or "")
    return row(
        "DL-05", "CTHRU retiree payroll (SRC-503)",
        search,
        latest_year or "unreadable",
        f"search year vs max year on pni4-392n; pull month is {ym(led.get('as_of'))}",
    )


def probe_ntd_all():
    return probe_ntd("DL-22")


def probe_ntd_mbta():
    return probe_ntd("DL-03", ntd_id="10003")


FILE_SUFFIXES = (".csv", ".txt", ".json", ".xlsx", ".xls", ".zip", ".pdf", ".xml")


def looks_like_file(url):
    path = urllib.parse.urlparse(url).path.lower()
    return path.endswith(FILE_SUFFIXES) or "/resource/" in path or "/download" in path


def http_probe(url, timeout=20):
    """HEAD, then GET if the host rejects HEAD. Does not parse vintage."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200) or 200), None
    except urllib.error.HTTPError as exc:
        if int(exc.code) in (403, 405, 501):
            try:
                return _http_status(url, timeout=timeout), None
            except Exception as e:
                return None, type(e).__name__
        return int(exc.code), None
    except Exception as e:
        return None, type(e).__name__


def iter_register():
    """Every live source URL on the platform. Deduped by tool + source id."""
    seen = set()
    for app in load_apps():
        if app.get("wave") == "build":
            continue
        tid = app.get("id") or ""
        for src in app.get("sources") or []:
            url = (src.get("url") or "").strip()
            if not url.startswith("http"):
                continue
            key = (tid, src.get("id") or url)
            if key in seen:
                continue
            seen.add(key)
            yield tid, src.get("id") or "", src.get("name") or url, url
    for tid in ("DL-01", "DL-02", "DL-03", "DL-04", "DL-05"):
        led = load_ledger(tid)
        smap = led.get("source_id_map") or {}
        if not isinstance(smap, dict):
            continue
        for sid, rec in smap.items():
            if not isinstance(rec, dict):
                continue
            url = (rec.get("url") or "").strip()
            if not url.startswith("http"):
                continue
            key = (tid, sid)
            if key in seen:
                continue
            seen.add(key)
            yield tid, sid, rec.get("label") or rec.get("name") or sid, url


def probe_register():
    """Reachability for every register URL. Does not invent a vintage."""
    rows = []
    for tid, sid, name, url in iter_register():
        code, err = http_probe(url)
        if err:
            status = "probe-failed"
            file_s = f"err:{err}"
            note = "register URL; no vintage parsed"
        elif code in (200, 204, 301, 302, 303, 307, 308):
            status = "reachable"
            file_s = f"HTTP {code}"
            note = "register URL; no vintage parsed"
        elif code in (404, 410):
            status = "missing"
            file_s = f"HTTP {code}"
            note = "register URL is gone"
        else:
            status = "probe-failed"
            file_s = f"HTTP {code}"
            note = "register URL; host did not return the file"
        rows.append({
            "tool": tid,
            "source": f"{sid} {name}".strip() if sid else name,
            "ledger": "",
            "file": file_s,
            "status": status,
            "note": note,
            "url": url,
            "file_like": looks_like_file(url),
        })
        time.sleep(0.12)
    return rows


def main():
    results = []
    for fn in (
        probe_bfs, probe_laus, probe_ui, probe_bps,
        probe_ntd_all, probe_ntd_mbta, probe_qtax,
        probe_citizens, probe_cthru,
    ):
        try:
            rec = fn()
        except Exception as e:
            rec = {
                "tool": fn.__name__,
                "source": fn.__name__,
                "ledger": "",
                "file": f"err:{type(e).__name__}",
                "status": "probe-failed",
                "note": str(e)[:160],
            }
        results.append(rec)
        print(f"{rec['status']:14}  {rec['tool']:8}  ledger={rec['ledger'] or '-':20}  file={rec['file'] or '-':20}  {rec['source']}")
        if rec.get("note"):
            print(f"{'':14}  {'':8}  {rec['note']}")

    register = []
    if os.environ.get("DATALABS_CHECK_REGISTER") == "1":
        print("\nREGISTER (every live source URL; reachability only):")
        register = probe_register()
        for rec in register:
            print(f"{rec['status']:14}  {rec['tool']:8}  {rec['file']:12}  {rec['source']}")
        results.extend(register)

    behind = [r for r in results if r["status"] == "behind"]
    failed = [r for r in results if r["status"] == "probe-failed"]
    missing = [r for r in register if r["status"] == "missing" and r.get("file_like")]
    print()
    print(f"probed {len(results)} rows on {TODAY}  UA={UA}")
    print(f"vintage current {sum(1 for r in results if r['status']=='current')}  "
          f"behind {len(behind)}  reachable {sum(1 for r in register if r['status']=='reachable')}  "
          f"missing {sum(1 for r in register if r['status']=='missing')}  "
          f"probe-failed {len(failed)}")
    if behind:
        print("\nBEHIND (file newer than ledger):")
        for r in behind:
            print(f" - {r['tool']} {r['source']}: ledger {r['ledger']}  file {r['file']}")
    if missing:
        print("\nMISSING (register file URL is gone):")
        for r in missing:
            print(f" - {r['tool']} {r['source']}: {r.get('url')}")
    if behind or missing:
        sys.exit(1)
    print("\nno reachable high-cadence file is newer than its ledger")
    if register:
        print("every live register file URL still responds")


if __name__ == "__main__":
    main()
