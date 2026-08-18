#!/usr/bin/env python3
"""Fail when the public question and hero number are different metrics,
or when jump nav points at missing insight figures.

Does not invent figures. Skips the tax atlas (DL-01) and Florida insurance (DL-02).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from audience_starters import starters_for  # noqa: E402
from page_voice import SKIP_VOICE, flagship_voice, split_ma_line, uses_national_lens, voice_for  # noqa: E402
from suite_common import ledger_path, load_apps  # noqa: E402

failures = []


def fail(msg):
    failures.append(msg)
    print(f"answer contract: MISS {msg}")


def ok(msg):
    print(f"answer contract: ok   {msg}")


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


# ---- 1. Public starter matches the hero number for live suite tools ----
apps = load_apps()
for app in apps:
    tid = app["id"]
    if tid in SKIP_VOICE or app.get("wave") != "live":
        continue
    path = ledger_path(tid)
    if not path.exists():
        continue
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("status") != "live":
        continue
    voice = voice_for(app, ledger)
    answer = (voice or {}).get("answer") or {}
    q = (answer.get("q") or "").strip()
    value = str(answer.get("value") or "").strip()
    context = (answer.get("context") or "").strip()
    public = (starters_for(tid) or {}).get("public") or ""
    if public and q != public:
        fail(f"{tid} public H2 {q!r} does not match starter {public!r}")
    else:
        ok(f"{tid} public H2")
    if not value:
        fail(f"{tid} has an empty hero number")
        continue
    ma_line = (voice or {}).get("ma") or ""
    split_val, _ = split_ma_line(ma_line)
    if ma_line and re.match(r"^\d{1,3}$", value) and re.search(r"\d,\d{3}", ma_line):
        fail(f"{tid} hero value {value!r} looks like a comma-split of {ma_line!r}")
    if tid == "DL-06":
        if "enroll" not in q.lower() or "915,932" not in value:
            fail(f"{tid} public question should be Massachusetts enrollment, value={value!r}")
        else:
            ok(f"{tid} enrollment")
    if tid == "DL-08":
        if "enroll" not in q.lower():
            fail(f"{tid} public question should be enrollment, got {q!r}")
        else:
            ok(f"{tid} enrollment")
    if tid == "DL-22":
        compact = value.replace(",", "")
        if "26288869" not in compact and "26,288,869" not in value:
            fail(f"{tid} hero should keep MBTA trips with thousands separators, value={value!r}")
        else:
            ok(f"{tid} MBTA trips")
    if tid == "DL-26":
        if "13,117" not in value and "13117" not in value.replace(",", "").replace("+", ""):
            fail(f"{tid} hero should keep Amherst +13,117, value={value!r}")
        else:
            ok(f"{tid} town change")
    if tid == "DL-29":
        if uses_national_lens(tid, ledger):
            if "united states" not in q.lower():
                fail(f"{tid} public question should be United States collections, got {q!r}")
            else:
                ok(f"{tid} national tax")
        elif "which state collected the most" in q.lower():
            fail(f"{tid} public question is the journalist ranking, not Massachusetts")
        elif "massachusetts" not in q.lower():
            fail(f"{tid} public question should be Massachusetts collections, got {q!r}")
        else:
            ok(f"{tid} MA-first tax")
    if uses_national_lens(tid, ledger):
        geo = (answer.get("geo") or "").lower()
        kind = answer.get("kind") or ""
        if kind == "rank":
            if not value:
                fail(f"{tid} ranking hero is empty")
            else:
                ok(f"{tid} ranking hero")
        elif geo != "united states":
            fail(f"{tid} national-lens default geo is {answer.get('geo')!r}, not United States")
        else:
            ok(f"{tid} national default")
    if tid == "DL-30":
        if "10.89" not in value:
            fail(f"{tid} hero should be Commonwealth payroll total, value={value!r}")
        else:
            ok(f"{tid} payroll total")
    if tid == "DL-32":
        ctx_l = context.lower()
        if "speaker" in q.lower() and "spilka" in ctx_l and "senate president" not in ctx_l and "mariano" not in ctx_l:
            fail(f"{tid} Speaker question names Spilka without the office")
        elif "speaker" in q.lower() and "senate president" not in q.lower() and "mariano" not in ctx_l:
            fail(f"{tid} House Speaker question should name Mariano or both offices")
        else:
            ok(f"{tid} leadership offices")
    if tid == "DL-15":
        if "billion" in value.lower() and "million" in context.lower() and "chained 2017" not in context.lower():
            fail(f"{tid} leftover millions unit after billion conversion, context={context!r}")
        else:
            ok(f"{tid} GDP units")
    if tid == "DL-28":
        if "massachusetts state tax collections by type" in context.lower():
            fail(f"{tid} context is a field name, not a sentence")
        else:
            ok(f"{tid} tax context")

# ---- 2. Electricity household context uses the residential U.S. average ----
dl04 = load_json("netlify/functions/dl04-answers.json")
voice04 = flagship_voice("DL-04", dl04)
ctx04 = ((voice04 or {}).get("answer") or {}).get("context") or ""
if "12.94" in ctx04 and "16.48" not in ctx04:
    fail("DL-04 household context cites the all-sector U.S. average 12.94")
else:
    ok("DL-04 residential U.S. average")
elec = (ROOT / "electricity/index.html").read_text(encoding="utf-8")
if "State All-Sector Averages" in elec.split("</title>", 1)[0]:
    fail("electricity <title> still says State All-Sector Averages")
else:
    ok("electricity title")
m = re.search(r'id="mapNote">(.*?)</div>', elec, re.S)
if m and "all sectors combined" in m.group(1).lower() and "household" not in m.group(1).lower():
    fail("electricity default #mapNote is still the all-sector note")
else:
    ok("electricity default map note")

# ---- 3. Jump hrefs on generated suite pages must exist ----
SKIP_PAGES = {"tax-atlas", "florida-insurance"}
for app in apps:
    if app.get("wave") != "live":
        continue
    slug = app.get("slug")
    if not slug or slug in SKIP_PAGES:
        continue
    page = ROOT / slug / "index.html"
    if not page.exists():
        continue
    html = page.read_text(encoding="utf-8")
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    hrefs = re.findall(r'href="#(insight-[^"]+|view-[^"]+|answer)"', html)
    dead = []
    for href in hrefs:
        if href not in ids:
            dead.append(href)
    if dead:
        fail(f"{app['id']} ({slug}) jump hrefs missing ids: {sorted(set(dead))}")
    else:
        ok(f"{app['id']} jump hrefs")

# ---- 4. Florida place-strip is visible HTML under the hero ----
for app in apps:
    tid = app["id"]
    if tid in SKIP_VOICE or app.get("wave") != "live":
        continue
    path = ledger_path(tid)
    if not path.exists():
        continue
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("status") != "live" or not uses_national_lens(tid, ledger):
        continue
    slug = app.get("slug")
    page = ROOT / slug / "index.html"
    if not page.exists():
        fail(f"{tid} missing page for hero place-strip check")
        continue
    html = page.read_text(encoding="utf-8")
    if not re.search(
        r'id="answerNum">[^<]*</div>\s*<div class="place-strip" id="placeStrip">',
        html,
    ):
        fail(f"{tid} ({slug}) place-strip is not immediately under the hero number")
        continue
    m = re.search(
        r'<div class="place-strip" id="placeStrip">(.*?)<p class="answer-',
        html,
        re.S,
    )
    if not m or "ps-fl" not in m.group(1) or "Florida" not in m.group(1):
        fail(f"{tid} ({slug}) hero place-strip is missing the published Florida cell")
    else:
        ok(f"{tid} hero Florida strip")
    strip = re.search(r'<div class="strip metrics">(.*?)</div>\s*</section>', html, re.S)
    labels = re.findall(r'<div class="cl">([^<]+)</div>', strip.group(1)) if strip else []
    dups = [lab for lab in labels if lab.lower().startswith(("massachusetts", "florida"))]
    if dups:
        fail(f"{tid} ({slug}) KPI row repeats the place-strip: {dups}")
    else:
        ok(f"{tid} KPI row does not repeat MA/FL")

elec_html = (ROOT / "electricity/index.html").read_text(encoding="utf-8")
if not re.search(
    r'id="answerNum">[^<]*</div>\s*<div class="place-strip" id="placeStrip">',
    elec_html,
):
    fail("DL-04 place-strip is not immediately under the hero number")
elif "ps-fl" not in elec_html.split('id="placeStrip">', 1)[1][:800]:
    fail("DL-04 hero place-strip is missing the published Florida cell")
else:
    ok("DL-04 hero Florida strip")
elec_strip = re.search(r'<div class="strip metrics">(.*?)</div>\s*</section>', elec_html, re.S)
elec_labels = re.findall(r'<div class="cl">([^<]+)</div>', elec_strip.group(1)) if elec_strip else []
elec_dups = [lab for lab in elec_labels if lab.lower().startswith(("massachusetts", "florida"))]
if elec_dups:
    fail(f"DL-04 KPI row repeats the place-strip: {elec_dups}")
else:
    ok("DL-04 KPI row does not repeat MA/FL")

# ---- 5. Fifty-state Figure 1 is the hex cartogram ----
usmap = (ROOT / "assets" / "us-map.js").read_text(encoding="utf-8")
hex_block = re.search(r"var HEX = \{([\s\S]*?)\n  \};", usmap)
if not hex_block:
    fail("us-map.js is missing the HEX layout")
else:
    hex_keys = set(re.findall(r"\b([A-Z]{2}):\[", hex_block.group(1)))
    if len(hex_keys) != 51 or "MA" not in hex_keys or "FL" not in hex_keys or "DC" not in hex_keys:
        fail(f"HEX layout has {len(hex_keys)} cells, not 51 with MA, FL, and DC")
    else:
        ok("HEX layout has 51 jurisdictions")

for app in apps:
    tid = app["id"]
    if tid in SKIP_VOICE or app.get("wave") != "live":
        continue
    path = ledger_path(tid)
    if not path.exists():
        continue
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("status") != "live" or not uses_national_lens(tid, ledger):
        continue
    slug = "electricity" if tid == "DL-04" else app.get("slug")
    page = ROOT / slug / "index.html"
    if not page.exists():
        continue
    html = page.read_text(encoding="utf-8")
    if not re.search(r'id="chRank"[^>]*data-mode="hex"', html):
        fail(f"{tid} ({slug}) Figure 1 is not the hex cartogram")
    else:
        ok(f"{tid} hex Figure 1")

if "mode: 'hex'" not in elec_html and 'mode: "hex"' not in elec_html:
    fail("DL-04 electricity map is not locked to hex")
else:
    ok("DL-04 hex Figure 1")

# ---- 6. Fifty-state tools have one Place picker, not a second Compare menu ----
for app in apps:
    tid = app["id"]
    if tid in SKIP_VOICE or app.get("wave") != "live":
        continue
    path = ledger_path(tid)
    if not path.exists():
        continue
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("status") != "live" or not uses_national_lens(tid, ledger):
        continue
    slug = "electricity" if tid == "DL-04" else app.get("slug")
    page = ROOT / slug / "index.html"
    if not page.exists():
        continue
    html = page.read_text(encoding="utf-8")
    if 'id="compareSel"' in html or "Pin a second state" in html:
        fail(f"{tid} ({slug}) still has a second state Compare menu")
    else:
        ok(f"{tid} one Place picker")

# ---- 7. Flagship pages share the finding chrome; atlas hex has no gold/rust ----
atlas = (ROOT / "tax-atlas/index.html").read_text(encoding="utf-8")
if 'id="compareSel"' in atlas:
    fail("tax-atlas still has a second state Compare menu")
else:
    ok("tax-atlas has no Compare menu")
if 'id="answerQ"' not in atlas or 'id="chRank"' not in atlas:
    fail("tax-atlas is missing the finding hero or hex Figure 1")
else:
    ok("tax-atlas finding hero and hex Figure 1")
if "roleOutlines: false" not in atlas and "roleOutlines:false" not in atlas:
    fail("tax-atlas hex map still uses gold/rust role outlines")
else:
    ok("tax-atlas hex map has no gold/rust outlines")

fl_html = (ROOT / "florida-insurance/index.html").read_text(encoding="utf-8")
if 'id="compareSel"' in fl_html:
    fail("florida-insurance still has a Compare menu")
else:
    ok("florida-insurance has no Compare menu")
if 'id="answerQ"' not in fl_html:
    fail("florida-insurance is missing the finding hero")
else:
    ok("florida-insurance finding hero")
if "Policymaker Briefing Edition" in fl_html:
    fail("florida-insurance title still says Policymaker Briefing Edition")
else:
    ok("florida-insurance title")

if failures:
    print("\nANSWER CONTRACT FAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\nall answer-contract checks pass")
