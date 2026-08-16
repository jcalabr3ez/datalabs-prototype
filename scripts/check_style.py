#!/usr/bin/env python3
"""House-style and cross-file consistency checks. Run in CI and locally.

1. Em-dash lint: the house rule is no em dashes anywhere, in copy or code
   strings (use commas, colons, or middots). Checks the literal character
   and the HTML entity across every tracked text file. The needles are
   built from escapes so this checker never trips itself.

2. Florida page sentinels: charts, dateline, the Citizens PIF headline,
   and the county-change ranking sentence are generated from the ledger.
   Remaining narrative is still hand-authored. The page must still carry
   the ledger's latest Citizens policies-in-force figure and its as_of
   month so a refresh cannot silently drop those headlines.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_EXT = {".html", ".js", ".mjs", ".json", ".md", ".py", ".yml", ".yaml", ".toml"}
SKIP_PARTS = {".git", "node_modules", "__pycache__"}

failures = []

# ---- 1. em-dash lint ----
for p in sorted(ROOT.rglob("*")):
    if not p.is_file() or p.suffix not in TEXT_EXT:
        continue
    if SKIP_PARTS & set(p.parts):
        continue
    if p.name.endswith(".min.js"):
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    for needle, label in (("\u2014", "em dash"), ("&" + "mdash;", "em dash entity")):
        if needle in text:
            lines = [i + 1 for i, l in enumerate(text.split("\n")) if needle in l][:5]
            failures.append(f"{p.relative_to(ROOT)}: {label} on line(s) {lines}")
print(f"em-dash lint: {'FAIL' if failures else 'clean'}")

# ---- 2. Florida page sentinels ----
fl = json.loads((ROOT / "netlify/functions/dl02-answers.json").read_text(encoding="utf-8"))
page = (ROOT / "florida-insurance/index.html").read_text(encoding="utf-8")
latest = fl["citizens_policies_monthly"][-1]
pif_formatted = f"{latest['v']:,}"
sentinels = [
    (pif_formatted, f"latest Citizens policies in force ({pif_formatted}, month {latest['m']})"),
    (fl["as_of"], f"ledger as_of ({fl['as_of']})"),
    (fl["page"]["revised"], f"page.revised ({fl['page']['revised']})"),
]
if "DATA:BEGIN florida-charts" not in page:
    failures.append(
        "florida-insurance/index.html is missing the generated florida-charts block"
    )
    print("florida charts: MISS generated block")
else:
    print("florida charts: ok   generated block present")

# Flagship page scripts must parse. A missing brace blanks every chart
# and leaves the view tabs as no-ops (showView is never defined).
for rel in (
    "florida-insurance/index.html",
    "electricity/index.html",
    "pensions/index.html",
    "mbta/index.html",
):
    html = (ROOT / rel).read_text(encoding="utf-8")
    start = html.rfind("<script>")
    stop = html.rfind("</script>")
    if start < 0 or stop < start:
        failures.append(f"{rel}: could not find the trailing chart script")
        print(f"js syntax {rel}: MISS script")
        continue
    js = html[start + 8 : stop]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
        tmp.write(js)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            ["node", "--check", tmp_path],
            capture_output=True,
            text=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "syntax error").strip().splitlines()[-1]
        failures.append(f"{rel}: chart script does not parse ({err})")
        print(f"js syntax {rel}: FAIL {err}")
    else:
        print(f"js syntax {rel}: ok")

for needle, label in sentinels:
    ok = needle in page
    print(f"florida sentinel: {'ok  ' if ok else 'MISS'} {label}")
    if not ok:
        failures.append(
            f"florida-insurance/index.html does not mention {label}; "
            "the DL-02 ledger moved but the hand-authored page did not follow"
        )

# ---- 3. Electricity page sentinels ----
el = json.loads((ROOT / "netlify/functions/dl04-answers.json").read_text(encoding="utf-8"))
epage = (ROOT / "electricity/index.html").read_text(encoding="utf-8")
us_fmt = f"{el['latest']['us']['price_cents']:.2f}"
el_sentinels = [
    (us_fmt, f"latest U.S. all-sector price ({us_fmt} cents, year {el['data_year']})"),
    (str(el["data_year"]), f"ledger data year ({el['data_year']})"),
    (el["page"]["revised"], f"page.revised ({el['page']['revised']})"),
]
if "DATA:BEGIN electricity-data" not in epage:
    failures.append("electricity/index.html is missing the generated electricity-data block")
    print("electricity charts: MISS generated block")
else:
    print("electricity charts: ok   generated block present")
for needle, label in el_sentinels:
    ok = needle in epage
    print(f"electricity sentinel: {'ok  ' if ok else 'MISS'} {label}")
    if not ok:
        failures.append(
            f"electricity/index.html does not mention {label}; "
            "the DL-04 ledger moved but the hand-authored page did not follow"
        )

# ---- 4. Pensions page sentinels ----
pn = json.loads((ROOT / "netlify/functions/dl05-answers.json").read_text(encoding="utf-8"))
ppage = (ROOT / "pensions/index.html").read_text(encoding="utf-8")
st_fmt = f"{pn['latest']['state']['funded_pct']}"
pn_sentinels = [
    (st_fmt, f"State funded ratio ({st_fmt} percent, valuation {pn['latest']['state']['valuation_year']})"),
    (str(pn["retiree_year"]), f"ledger retiree year ({pn['retiree_year']})"),
    (str(pn.get("search_year") or ""), f"ledger search year ({pn.get('search_year')})"),
    (pn["page"]["revised"], f"page.revised ({pn['page']['revised']})"),
]
search_dir = ROOT / "pensions/search"
if not (search_dir / "manifest.json").exists():
    failures.append("pensions/search/manifest.json is missing; run scripts/refresh_dl05.py")
    print("pensions search: MISS manifest")
else:
    print("pensions search: ok   manifest present")
if not (search_dir / "M.json.gz").exists():
    failures.append("pensions/search/M.json.gz is missing; run scripts/refresh_dl05.py")
    print("pensions search: MISS M shard")
else:
    print("pensions search: ok   M shard present")
if "DATA:BEGIN pensions-data" not in ppage:
    failures.append("pensions/index.html is missing the generated pensions-data block")
    print("pensions charts: MISS generated block")
else:
    print("pensions charts: ok   generated block present")
for needle, label in pn_sentinels:
    ok = needle in ppage
    print(f"pensions sentinel: {'ok  ' if ok else 'MISS'} {label}")
    if not ok:
        failures.append(
            f"pensions/index.html does not mention {label}; "
            "the DL-05 ledger moved but the hand-authored page did not follow"
        )

# ---- 5. Suite live-page sentinels (every live DL-06+ ledger) ----
sys.path.insert(0, str(ROOT / "scripts"))
from suite_common import load_apps, ledger_path  # noqa: E402

for app in load_apps():
    led_path = ledger_path(app["id"])
    slug = app["slug"]
    page_path = ROOT / slug / "index.html"
    rel = str(led_path.relative_to(ROOT))
    if not led_path.exists() or not page_path.exists():
        failures.append(f"{slug}: missing ledger or page; run scripts/refresh_suite.py")
        print(f"suite {slug}: MISS ledger or page")
        continue
    led = json.loads(led_path.read_text(encoding="utf-8"))
    page = page_path.read_text(encoding="utf-8")
    if led.get("status") != "live":
        print(f"suite {slug}: skip status={led.get('status')}")
        continue
    if f"DATA:BEGIN {slug}-data" not in page:
        failures.append(f"{slug}/index.html is missing the generated {slug}-data block")
        print(f"suite {slug}: MISS generated block")
    else:
        print(f"suite {slug}: ok   generated block present")
    if led.get("status") == "live":
        as_of = str(led.get("as_of") or "")
        if as_of and as_of not in page:
            failures.append(f"{slug}/index.html does not mention ledger as_of ({as_of})")
            print(f"suite {slug}: MISS as_of {as_of}")
        else:
            print(f"suite {slug}: ok   as_of {as_of}")
    if app["id"] == "DL-32":
        for needle, label in (
            ("Base salary", "base salary column"),
            ("Supplemental", "supplemental column"),
            ("Stipend", "stipend column"),
        ):
            if needle not in page:
                failures.append(f"legislature-pay/index.html is missing the {label}")
                print(f"suite {slug}: MISS {label}")
            else:
                print(f"suite {slug}: ok   {label}")

# ---- 6. Catalog is native DataLabs applications only ----
catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
legacy_rows = [r.get("id") for r in catalog if r.get("legacy")]
archive_rows = [r.get("id") for r in catalog if r.get("id") == "ARCHIVE"]
offsite = [
    r.get("id")
    for r in catalog
    if r.get("url") and not (str(r["url"]).startswith("/") and not str(r["url"]).startswith("//"))
]
if legacy_rows:
    failures.append("catalog.json still has legacy partner rows on " + ", ".join(legacy_rows))
    print("catalog hygiene: MISS leftover legacy arrays")
else:
    print("catalog hygiene: ok   no legacy partner rows")
if archive_rows:
    failures.append("catalog.json still has an ARCHIVE entry")
    print("catalog hygiene: MISS ARCHIVE")
else:
    print("catalog hygiene: ok   no ARCHIVE")
if offsite:
    failures.append("catalog.json has off-site urls on " + ", ".join(offsite))
    print("catalog hygiene: MISS off-site urls")
else:
    print("catalog hygiene: ok   every application url is local")

# Stub Tableau links may be off-site. They belong only on in-build rows.
for r in catalog:
    dashes = r.get("dashboards") or []
    if not dashes:
        continue
    if r.get("st") != "build":
        failures.append(f"catalog.json {r.get('id')} has dashboards but is not in build")
        print(f"catalog hygiene: MISS dashboards on live {r.get('id')}")
        continue
    bad = [d.get("t") or "?" for d in dashes if not str(d.get("u") or "").startswith("https://")]
    if bad:
        failures.append(f"catalog.json {r.get('id')} dashboard urls must be https ({', '.join(bad)})")
        print(f"catalog hygiene: MISS dashboard url on {r.get('id')}")
    else:
        print(f"catalog hygiene: ok   {r.get('id')} has {len(dashes)} Tableau dashboard(s)")

if failures:
    print("\nSTYLE/CONSISTENCY FAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\nall style and consistency checks pass")
