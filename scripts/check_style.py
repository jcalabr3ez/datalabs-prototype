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
import sys
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

for needle, label in sentinels:
    ok = needle in page
    print(f"florida sentinel: {'ok  ' if ok else 'MISS'} {label}")
    if not ok:
        failures.append(
            f"florida-insurance/index.html does not mention {label}; "
            "the DL-02 ledger moved but the hand-authored page did not follow"
        )

if failures:
    print("\nSTYLE/CONSISTENCY FAILURES:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("\nall style and consistency checks pass")
