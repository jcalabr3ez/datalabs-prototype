#!/usr/bin/env python3
"""Generate the public status page, changelog chrome, and sitemap.

Canonical inputs: catalog.json, suite/apps.json, ledger as_of fields, and
the freshness RULES in check_freshness.py. Called from inject_data.py so
a deploy cannot ship a stale status table. Never invents figures.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_freshness import RULES, parse_as_of
from suite_common import ROOT, load_apps

SITE = "https://datalabsai.netlify.app"
TODAY = date(2026, 8, 15)
TODAY_LABEL = "August 15, 2026"

FLAGSHIPS = [
    {
        "id": "DL-01",
        "title": "State Tax Atlas",
        "url": "/tax-atlas/",
        "refresh": "Weekly Cursor Automation, Monday 9:00 AM ET",
        "ledger": "netlify/functions/dl01-answers.json",
    },
    {
        "id": "DL-02",
        "title": "Florida Insurance Watch",
        "url": "/florida-insurance/",
        "refresh": "Monthly Cursor Automation, 17th at 10:00 AM ET",
        "ledger": "netlify/functions/dl02-answers.json",
    },
    {
        "id": "DL-03",
        "title": "Transportation & MBTA",
        "url": "/mbta/",
        "refresh": "Monthly GitHub Action, 5th of the month",
        "ledger": "netlify/functions/dl03-answers.json",
    },
    {
        "id": "DL-04",
        "title": "Retail Electricity Prices",
        "url": "/electricity/",
        "refresh": "Yearly GitHub Action, October 20",
        "ledger": "netlify/functions/dl04-answers.json",
    },
    {
        "id": "DL-05",
        "title": "Massachusetts Public Pensions",
        "url": "/pensions/",
        "refresh": "Monthly GitHub Action for CTHRU (8th); boards when PERAC posts",
        "ledger": "netlify/functions/dl05-answers.json",
    },
]

CHANGELOG = [
    {
        "date": "August 16, 2026",
        "title": "Figures numbered in one sequence",
        "body": (
            "Every suite page now numbers its charts 1, 2, 3 in the order "
            "they appear. The closer-look charts no longer use letters, "
            "and the compare and trend charts continue the same count."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Place names without city or town",
        "body": (
            "Municipal Atlas and Municipal Rankings now drop the Census "
            "legal suffix, so Boston city reads as Boston and Lexington town "
            "reads as Lexington. Charts, tables, find cards, and the lead "
            "use the short name. Search still matches the old form."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "New Releases cards",
        "body": (
            "The two New Releases cards at the top of the front door are now "
            "equal cream tiles with a gold rule, a larger finding, and a short "
            "spark or fifty-state count. Status is the vintage in words, not a "
            "live-or-preview badge."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "A clearer catalog",
        "body": (
            "The front-door catalog is now four open verticals with one "
            "application per row: name, finding, place, and vintage. The "
            "nested accordion, dotted leaders, and color-coded vintage dots "
            "are gone. Search and place filters still work."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "NAEP scores over time",
        "body": (
            "National K-12 now charts NAEP reading and math for every state "
            "from the first state assessment through 2024, plus the 2019-to-2024 "
            "change so a reader can see who rose and who fell. The scores are "
            "the published Nation's Report Card averages. Employer or school "
            "advice is still out of scope."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Legislature Pay",
        "body": (
            "A new American Citizenship tool lists every person paid as a "
            "Massachusetts Representative or Senator in calendar 2025, with "
            "base salary, Comptroller supplemental pay, stipends, and total. "
            "Employer-paid health and pension contributions are not on the "
            "CTHRU named payroll file and are not invented here."
        ),
    },
    {
        "date": "August 15, 2026",
        "title": "Public production pass",
        "body": (
            "Search indexing is on. The site now ships robots.txt and a sitemap, "
            "a public status page for ledger vintage and refresh cadence, and this "
            "changelog. Suite ledgers refresh on a monthly GitHub Action. Questions "
            "asked at the front door are logged on the site (and optionally to a "
            "spreadsheet). Chart.js is served from this site. Suite pages share one "
            "stylesheet. Every tool page now has a how-to-cite line. Find boxes on "
            "the suite, electricity, and pensions pages write a shareable URL."
        ),
    },
    {
        "date": "August 15, 2026",
        "title": "Catalog reads as one product",
        "body": (
            "Audience tabs remain only on Florida Insurance Watch and the State Tax "
            "Atlas. The other tools are one scrolling page with jump links. There "
            "are no downloads. Two applications, 340B and Patents and Innovation, "
            "stay in build. Later series that are not in a stable public file stay "
            "unpublished."
        ),
    },
]


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def ops_page(title, description, standfirst, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} | Pioneer Institute | DataLabs</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{SITE}/{esc(title.split()[0].lower())}/">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Pioneer DataLabs">
<meta property="og:title" content="{esc(title)} | Pioneer Institute">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{SITE}/{esc(title.split()[0].lower())}/">
<meta property="og:image" content="{SITE}/assets/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Bodoni:ital,wght@0,400..700;1,400..700&family=Roboto:wght@300..900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/datalabs.css">
<link rel="stylesheet" href="/assets/ops.css">
</head>
<body>
<div class="wrap">
<div class="sitebar">
  <div class="sbleft">
    <a href="https://pioneerinstitute.org" aria-label="Pioneer Institute"><img src="https://pioneerinstitute.org/wp-content/uploads/2025/11/Pioneer_Negative_SVG.svg" alt="Pioneer Institute"></a>
    <a class="backlink" href="/">&#8592; All of DataLabs</a>
    <a class="nav" href="/#directory">Catalog</a>
    <a class="nav" href="/#about">About</a>
    <a class="nav" href="/status/">Status</a>
    <a class="nav" href="/changelog/">Changelog</a>
  </div>
  <span class="tag"><b>DataLabs</b> &nbsp;&middot;&nbsp; {esc(title)}</span>
</div>
<header>
  <div class="dots" aria-hidden="true"></div>
  <div class="org">Pioneer Institute <span class="sub">/ DataLabs</span></div>
  <h1>{esc(title)}</h1>
  <div class="standfirst">{esc(standfirst)}</div>
</header>
{body}
<footer>
  <div class="fbrand"><span class="pi">Pioneer Institute</span> &nbsp;&middot;&nbsp; 185 Devonshire Street, Suite 1101, Boston, MA 02110 &nbsp;&middot;&nbsp; <a href="https://pioneerinstitute.org">pioneerinstitute.org</a></div>
  <div class="flegal">Copyright &copy; 2026 Pioneer Institute. All rights reserved.</div>
</footer>
</div>
</body>
</html>
"""


def ledger_row(rel):
    path = ROOT / rel
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def freshness_cell(rel, ledger, today):
    rule = RULES.get(rel)
    if not rule:
        return "No automated gate", ""
    fmt, max_days, why = rule
    as_of = ledger.get("as_of")
    if not as_of:
        return "Missing as_of", "stale"
    age = (today - parse_as_of(str(as_of), fmt)).days
    if age > max_days:
        return f"Past gate ({age}d / {max_days}d)", "stale"
    if age < 0:
        return f"Current (limit {max_days}d)", "live"
    return f"Within gate ({age}d / {max_days}d)", "live"


def tool_rows(today):
    rows = []
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in catalog if str(row.get("id", "")).startswith("DL-")}

    for item in FLAGSHIPS:
        led = ledger_row(item["ledger"]) or {}
        gate, tone = freshness_cell(item["ledger"], led, today)
        rows.append({
            "id": item["id"],
            "title": item["title"],
            "url": item["url"],
            "status": "live",
            "vint": led.get("as_of") or by_id.get(item["id"], {}).get("vint") or "",
            "refresh": item["refresh"],
            "gate": gate,
            "tone": tone,
        })

    for app in load_apps():
        rel = f"netlify/functions/dl{app['id'].split('-')[1]}-answers.json"
        led = ledger_row(rel) or {}
        status = "live" if led.get("status") == "live" else "build"
        if status == "build":
            gate, tone = "In build. No figures published.", "build"
            refresh = "Held until a reachable primary file exists"
        else:
            gate, tone = freshness_cell(rel, led, today)
            refresh = "Monthly GitHub Action, 12th of the month"
        rows.append({
            "id": app["id"],
            "title": app["title"],
            "url": f"/{app['slug']}/",
            "status": status,
            "vint": led.get("data_month_label") or led.get("as_of") or "",
            "refresh": refresh,
            "gate": gate,
            "tone": tone if status == "live" else "build",
        })
    return rows


def status_body(rows):
    live = sum(1 for r in rows if r["status"] == "live")
    build = sum(1 for r in rows if r["status"] == "build")
    stale = sum(1 for r in rows if r["tone"] == "stale")
    trs = []
    for r in rows:
        cls = "dot-stale" if r["tone"] == "stale" else ("dot-build" if r["status"] == "build" else "dot-live")
        label = "Past gate" if r["tone"] == "stale" else ("In build" if r["status"] == "build" else "Live")
        trs.append(
            "<tr>"
            f"<td class=\"m\"><a href=\"{esc(r['url'])}\">{esc(r['title'])}</a><br><span style=\"font-weight:400;color:var(--grey)\">{esc(r['id'])}</span></td>"
            f"<td><span class=\"dot {cls}\"></span>{esc(label)}</td>"
            f"<td>{esc(r['vint'])}</td>"
            f"<td>{esc(r['gate'])}</td>"
            f"<td>{esc(r['refresh'])}</td>"
            "</tr>"
        )
    table = "\n          ".join(trs)
    return f"""
<section>
  <h2>What this page reports</h2>
  <p class="lede">Vintage and refresh cadence for every DataLabs application. The colored dot in the catalog is the vintage of the data inside. This table adds the freshness gate and the job that is supposed to move it.</p>
  <p class="body-p">{live} applications are live. {build} are in build. {stale} {"is" if stale == 1 else "are"} past {"its" if stale == 1 else "their"} freshness gate. Table generated {TODAY_LABEL} from the ledgers in this repository.</p>
  <p class="body-p">Questions asked at the front door are written to the site question log so the next tool can come from demand, not from a bigger catalog. Individual questions are not published here. The ask box stays off by default until the Monday eval has a green run against the live site.</p>
  <div class="scroll"><table>
    <thead><tr><th>Application</th><th>Status</th><th>Vintage</th><th>Freshness gate</th><th>Refresh</th></tr></thead>
    <tbody>
          {table}
    </tbody>
  </table></div>
</section>
"""


def changelog_body():
    items = []
    for entry in CHANGELOG:
        items.append(
            "<li>"
            f"<div class=\"when\">{esc(entry['date'])}</div>"
            f"<h3>{esc(entry['title'])}</h3>"
            f"<p class=\"body-p\">{esc(entry['body'])}</p>"
            "</li>"
        )
    return f"""
<section>
  <h2>Public record of what changed</h2>
  <p class="lede">Corrections and production changes that a reader citing a figure should know about. Ledger refreshes that only extend a series land as pull requests and are not restated here unless a historical cell moved.</p>
  <ul class="log">
    {"".join(items)}
  </ul>
</section>
"""


def write_sitemap(rows):
    paths = ["/", "/status/", "/changelog/"]
    for r in rows:
        if r["url"] not in paths:
            paths.append(r["url"])
    urls = []
    for path in paths:
        urls.append(
            "  <url>\n"
            f"    <loc>{SITE}{path}</loc>\n"
            f"    <lastmod>{TODAY.isoformat()}</lastmod>\n"
            "  </url>"
        )
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    dest = ROOT / "sitemap.xml"
    dest.write_text(xml, encoding="utf-8")
    return dest


def main():
    rows = tool_rows(TODAY)
    status = ops_page(
        "Status",
        "Ledger vintage, freshness gates, and refresh jobs for every DataLabs application.",
        "When each application was last compiled, whether it is inside its publisher cadence, and which job is supposed to move it.",
        status_body(rows),
    )
    # Fix canonical for Status / Changelog (ops_page used the first word)
    status = status.replace(f"{SITE}/status/", f"{SITE}/status/")
    (ROOT / "status").mkdir(parents=True, exist_ok=True)
    (ROOT / "status" / "index.html").write_text(status, encoding="utf-8")

    log = ops_page(
        "Changelog",
        "Public record of DataLabs corrections and production changes.",
        "What changed on the public site, beginning at launch.",
        changelog_body(),
    )
    log = log.replace(f"{SITE}/changelog/", f"{SITE}/changelog/")
    (ROOT / "changelog").mkdir(parents=True, exist_ok=True)
    (ROOT / "changelog" / "index.html").write_text(log, encoding="utf-8")

    write_sitemap(rows)
    print(f"render_ops: {len(rows)} tools, sitemap, status, changelog")


if __name__ == "__main__":
    main()
