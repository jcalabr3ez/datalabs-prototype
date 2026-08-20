#!/usr/bin/env python3
"""Fail when the public question and hero number are different metrics,
or when jump nav points at missing insight figures.

Does not invent figures. Skips the tax atlas (DL-01) jump-href scan.
Florida insurance (DL-02) has its own hero, figure, and PIF-pin checks below.
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
    if tid == "DL-34":
        compact = value.replace(",", "")
        if "44416" not in compact:
            fail(f"{tid} hero should be BPS enrollment 44,416, value={value!r}")
        else:
            ok(f"{tid} BPS enrollment")
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
usmap_css = (ROOT / "assets" / "us-map.css").read_text(encoding="utf-8")
if re.search(r"\.usmap-pin\{[^}]*position:absolute", usmap_css):
    fail("hex hover pin still overlays the cartogram")
else:
    ok("hex hover pin sits under the cartogram")
if "var step =" in usmap:
    fail("hex cartogram still uses a paper gutter between cells")
else:
    ok("hex cartogram is a packed plate")
if "var pad = 20" in usmap:
    fail("hex viewBox still pads from centers and clips edge cells")
elif "minY - size" not in usmap and "minX - size" not in usmap:
    fail("hex viewBox still pads from centers and clips edge cells")
else:
    ok("hex viewBox includes hex vertices")
if "60 * i - 30" not in usmap or "1.5 * r" not in usmap:
    fail("hex cartogram is not pointy-top latitude rows")
else:
    ok("hex cartogram uses pointy-top rows like the country")
if not re.search(r"\.usmap\.is-hex \.st polygon\{[^}]*stroke:#293C5C", usmap_css):
    fail("hex plate is missing hairline navy rules")
else:
    ok("hex plate uses hairline navy rules")
if re.search(r"\.usmap\.is-hex \.st-lab\{[^}]*stroke:#fff", usmap_css):
    fail("hex labels still use a white halo")
else:
    ok("hex labels have no halo")
if "max-width:680px" not in usmap_css:
    fail("full-width hex figures have no size cap")
else:
    ok("full-width hex figures are capped at 680px")

# ---- copy: no AI-looking chrome ----
from audience_starters import starters_html  # noqa: E402
chip_html = starters_html("DL-16")
if "ask-who" in chip_html or "General public" in chip_html:
    fail("ask chips still show audience labels")
else:
    ok("ask chips have no audience labels")
if "Ask this page" in chip_html or "Ask in your own words" in chip_html:
    fail("ask chrome still uses chatbot labels")
else:
    ok("ask chrome is lookup language")
if "Equal hexes, so a small state" in usmap:
    fail("hex lecture is still in us-map.js")
hex_lecture_pages = []
for rel in ("housing-market/index.html", "electricity/index.html"):
    if "Equal hexes, so a small state" in (ROOT / rel).read_text(encoding="utf-8"):
        hex_lecture_pages.append(rel)
if hex_lecture_pages:
    fail("hex lecture still on " + ", ".join(hex_lecture_pages))
else:
    ok("hex map lede is a series line")
later_qs = [
    row.get("q") or ""
    for row in json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    if isinstance(row, dict) and "later view" in (row.get("q") or "").lower()
]
if later_qs:
    fail(f"catalog deks still say later views: {later_qs[:3]}")
else:
    ok("catalog deks dropped later views")
front = (ROOT / "index.html").read_text(encoding="utf-8")
if "inform what we build next" in front or "Open the application" in front or "askbadge" in front:
    fail("landing ask chrome still sounds like a product demo")
else:
    ok("landing ask chrome is plain")
if (
    "<h3>One-month internal beta</h3>" in front
    or "Pioneer staff · through Sept" in front
    or "How a figure gets on a page" in front
    or "<h3>How to cite</h3>" in front
    or "<h3>Corrections</h3>" in front
):
    fail("landing still prints the beta briefing")
else:
    ok("landing dropped the beta briefing")
if "DataLabs · Beta" in front or ">Beta</span>" in front:
    fail("landing still says Beta")
elif "Prototype" not in front:
    fail("landing masthead is missing Prototype")
else:
    ok("landing marks the catalog as Prototype")
if "Every figure compiled here traces to a public record." in front:
    fail("landing still prints the public-record credo")
else:
    ok("landing dropped the public-record credo")
atlas_events = json.loads((ROOT / "netlify/functions/dl01-answers.json").read_text(encoding="utf-8"))
ev_text = " ".join(
    e.get("detail") or ""
    for ph in ((atlas_events.get("events") or {}).get("phases") or [])
    for e in ph.get("events") or []
)
if "Why it matters" in ev_text or "Potential impact" in ev_text or "two Americas" in ev_text:
    fail("tax-atlas events still use briefing wrappers")
else:
    ok("tax-atlas events dropped the wrappers")
atlas_html = (ROOT / "tax-atlas" / "index.html").read_text(encoding="utf-8")
if "Twenty-six dates that will decide" in atlas_html:
    fail("tax-atlas events intro is still a teaser")
else:
    ok("tax-atlas events intro is factual")

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

# ---- 7. Atlas opens on the hex map; Florida keeps its finding hero ----
atlas = (ROOT / "tax-atlas/index.html").read_text(encoding="utf-8")
if 'id="compareSel"' in atlas:
    fail("tax-atlas still has a second state Compare menu")
else:
    ok("tax-atlas has no Compare menu")
if 'id="answerQ"' in atlas or 'id="answer"' in atlas:
    fail("tax-atlas still has a finding hero above the map")
else:
    ok("tax-atlas has no finding hero")
if 'id="chRank"' not in atlas:
    fail("tax-atlas is missing hex Figure 1")
else:
    ok("tax-atlas hex Figure 1")
if "roleOutlines: false" not in atlas and "roleOutlines:false" not in atlas:
    fail("tax-atlas hex map still uses gold/rust role outlines")
else:
    ok("tax-atlas hex map has no gold/rust outlines")
if "Rates and vehicles" in atlas or "Start with Current Policy" in atlas:
    fail("tax-atlas still has the heading or how-to lede above the hexes")
else:
    ok("tax-atlas dropped the heading and how-to lede")
toggle = re.search(r'<div class="toggle".*?</div>', atlas, re.S)
if not toggle:
    fail("tax-atlas is missing the map view tabs")
else:
    t = toggle.group(0)
    if 'class="who"' in t or "Current Policy" in t or "Active Proposals" in t or "Ballot Access" in t or "Near-Term Risk" in t:
        fail("tax-atlas map tabs are still two-line labels")
    elif not all(word in t for word in ("Current", "Proposals", "Ballot", "Risk")):
        fail("tax-atlas map tabs are missing a one-word label")
    else:
        ok("tax-atlas map tabs are one word")
if 'id="placeSel"' in atlas or "Find a state" in atlas:
    fail("tax-atlas still has a Find a state filter")
else:
    ok("tax-atlas has no Find a state filter")
src_i = atlas.find('id="mapSrc"')
cap_i = atlas.find('id="caption"')
map_i = atlas.find('id="chRank"')
if cap_i < 0 or src_i < 0 or map_i < 0 or cap_i < src_i or cap_i < map_i:
    fail("tax-atlas caption is still above the hexes")
else:
    ok("tax-atlas caption sits under the source line")
if not re.search(r'var selected = "CA"', atlas):
    fail("tax-atlas does not open on California")
else:
    ok("tax-atlas opens on California")

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
if 'id="btn-home"' in fl_html:
    fail("florida-insurance still has the three view buttons under the hero")
else:
    ok("florida-insurance has no view buttons under the hero")
if "What are the key takeaways?" in fl_html:
    fail("florida-insurance still reprints the key-takeaways strip")
else:
    ok("florida-insurance dropped the key-takeaways strip")
if "What do Floridians actually pay?" in fl_html:
    fail("florida-insurance still reprints the county-pay strip")
else:
    ok("florida-insurance dropped the county-pay strip")
if "florida-miami-change" in fl_html:
    fail("florida-insurance strip still leads with the Miami-Dade $48 change")
else:
    ok("florida-insurance strip dropped the $48 change")
cit_fig = fl_html.find("Policies in force at Citizens")
cty_fig = fl_html.find("County premiums the state publishes twice a year")
if cit_fig < 0 or cty_fig < 0 or cit_fig > cty_fig:
    fail("florida-insurance Figure 1 is not the Citizens series")
else:
    ok("florida-insurance Figure 1 is the Citizens series")
if "help you" in fl_html or "your county" in fl_html.lower() or "Both facts are accurate" in fl_html:
    fail("florida-insurance still uses sales voice above the figures")
else:
    ok("florida-insurance dropped the sales voice")
if "How many homes does Citizens still insure" in fl_html:
    fail("florida-insurance still calls Citizens policies homes")
else:
    ok("florida-insurance says policies, not homes")

# Pin the live Citizens vintage so a silent ledger or page drift fails CI.
# Update this pin only after a two-path check of a newer month-end PIF page.
PINNED_PIF = {
    "month": "2026-07",
    "policies": 278196,
    "url_slug": "20260731-policies-in-force",
    "personal_residential": 273822,
    "commercial": 4374,
}
fl_ledger = json.loads((ROOT / "netlify/functions/dl02-answers.json").read_text(encoding="utf-8"))
latest_pif = (fl_ledger.get("citizens_policies_monthly") or [{}])[-1]
key = fl_ledger.get("citizens_key_facts") or {}
latest_key = key.get("latest") or {}
book = ((fl_ledger.get("sourced_facts") or {}).get("citizens_july_2026_book") or {})
if latest_pif.get("m") != PINNED_PIF["month"] or latest_pif.get("v") != PINNED_PIF["policies"]:
    fail(
        "DL-02 latest PIF is not the pinned July 31, 2026 vintage of 278,196; "
        "update PINNED_PIF in check_answers.py after a two-path check of the new Citizens page"
    )
else:
    ok("DL-02 latest PIF matches the pinned July 31, 2026 vintage")
if PINNED_PIF["url_slug"] not in fl_html:
    fail("florida-insurance is missing the pinned July 31, 2026 Citizens PIF URL")
else:
    ok("florida-insurance cites the pinned July 31, 2026 Citizens PIF URL")
pif_fmt = f"{PINNED_PIF['policies']:,}"
if pif_fmt not in fl_html:
    fail(f"florida-insurance is missing the pinned PIF count {pif_fmt}")
else:
    ok("florida-insurance prints the pinned PIF count")
if book.get("policies") != PINNED_PIF["policies"] or PINNED_PIF["url_slug"] not in str(book.get("source") or ""):
    fail("DL-02 sourced_facts.citizens_july_2026_book does not match the pinned vintage")
else:
    ok("DL-02 sourced_facts book matches the pinned vintage")
if (
    latest_key.get("policies") != PINNED_PIF["policies"]
    or latest_key.get("personal_residential") != PINNED_PIF["personal_residential"]
    or latest_key.get("commercial") != PINNED_PIF["commercial"]
):
    fail("DL-02 citizens_key_facts.latest does not match the pinned personal/commercial split")
else:
    ok("DL-02 key facts keep the personal/commercial split")
strip = re.search(
    r'<div class="place-strip" id="placeStrip">(.*?)</div>\s*<p class="answer-ctx"',
    fl_html,
    re.S,
)
strip_html = strip.group(1) if strip else ""
for needle in ("March 31, 2026", "July 31, 2026", "Sept. 30, 2023"):
    if needle not in strip_html:
        fail(f"florida-insurance place-strip is missing the dated label {needle}")
    else:
        ok(f"florida-insurance place-strip dates {needle}")
grades_note = fl_html.find("How to read these grades")
chips = fl_html.find('class="rc-strip"')
if grades_note < 0 or chips < 0 or grades_note > chips:
    fail("florida-insurance report-card judgment note is not above the grade chips")
else:
    ok("florida-insurance report-card judgment note sits above the chips")

atlas_cap = (ROOT / "netlify/functions/dl01-answers.json")
cap = json.loads(atlas_cap.read_text(encoding="utf-8")).get("captions", {})
cur = cap.get("current") or ""
if "Proposition 40" not in cur or "Initiative 645" not in cur or "Rhode Island" not in cur:
    fail("tax-atlas current caption does not name the live vehicles")
else:
    ok("tax-atlas current caption names the live vehicles")

bps_html = (ROOT / "boston-schools/index.html").read_text(encoding="utf-8")
find_m = re.search(r"const FIND=(\{.*\});\n", bps_html)
if not find_m:
    fail("DL-34 page is missing FIND")
else:
    find = json.loads(find_m.group(1))
    if find.get("kind") != "school":
        fail(f"DL-34 FIND.kind is {find.get('kind')!r}, not school")
    elif find.get("default_q") != "Boston Latin School":
        fail(f"DL-34 FIND.default_q is {find.get('default_q')!r}")
    elif "boston latin school" not in (find.get("cards") or {}):
        fail("DL-34 FIND.cards is missing Boston Latin School")
    else:
        ok("DL-34 school finder defaults to Boston Latin School")
if "trend_right" not in bps_html or "Total expenditures per pupil" not in bps_html:
    fail("DL-34 trend is missing the per-pupil series")
elif "trend_academic" not in bps_html or "SRC-634-04" not in bps_html:
    fail("DL-34 trend is missing the MCAS overlay")
elif "44416" not in bps_html or "34833" not in bps_html:
    fail("DL-34 combined trend lede is missing the published endpoints")
elif "31%" not in bps_html or "29%" not in bps_html:
    fail("DL-34 MCAS lede is missing the published ELA endpoints")
elif "id=\"view-bps-ppe-trend\"" in bps_html:
    fail("DL-34 still has a standalone spending-trend view")
else:
    chart_m = re.search(r"const CHART=(\{.*\});\n", bps_html)
    acad = ((json.loads(chart_m.group(1)).get("trend_academic") or [{}])[0].get("points") or []) if chart_m else []
    invented_2020 = [p for p in acad if str(p.get("y")) == "2020" and p.get("v") is not None]
    if invented_2020:
        fail("DL-34 MCAS overlay invents a 2020 point")
    else:
        ok("DL-34 trend combines enrollment, spending, and MCAS")
if 'id="proofFind"' not in bps_html or 'id="proofFindList"' not in bps_html:
    fail("DL-34 school lookup is missing the typeahead list")
else:
    ok("DL-34 school lookup has a typeahead list")
if "function findHitsFor" not in bps_html or "find-pick" not in bps_html:
    fail("DL-34 school lookup cannot resolve a short name to a pick list")
else:
    ok("DL-34 school lookup resolves short names")

if failures:
    print("\nANSWER CONTRACT FAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\nall answer-contract checks pass")
