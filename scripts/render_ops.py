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
TODAY = date(2026, 8, 16)
TODAY_LABEL = "August 16, 2026"

FLAGSHIPS = [
    {
        "id": "DL-01",
        "title": "State Wealth Taxes",
        "url": "/tax-atlas/",
        "refresh": "Weekly Cursor Automation, Monday 9:00 AM ET",
        "ledger": "netlify/functions/dl01-answers.json",
    },
    {
        "id": "DL-02",
        "title": "Florida Homeowners Insurance",
        "url": "/florida-insurance/",
        "refresh": "Monthly Cursor Automation, 17th at 10:00 AM ET",
        "ledger": "netlify/functions/dl02-answers.json",
    },
    {
        "id": "DL-03",
        "title": "MBTA Performance",
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
        "title": "Per capita income compare uses every state",
        "body": (
            "The Per capita personal income, 2025 bar on State GDP now "
            "keeps every state and D.C. from the same BEA SAINC4 file, "
            "so Compare a state is not limited to the highlight four. "
            "The same published-row attach covers Fall 2024 public K-12 "
            "enrollment on Massachusetts Schools and the 9-quarter "
            "establishment birth-rate window on Business Formation. "
            "State Wealth Taxes and Florida Homeowners Insurance were "
            "not edited."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Ask can answer a named-state participation rate",
        "body": (
            "The front-door ask box now keeps a compact state map for "
            "labor-force participation and the other companion rankings, "
            "so a Wyoming participation question can answer from the core "
            "slice. The full monthly unemployment cube is no longer sent "
            "on every labor question."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Fifty-one jurisdiction rows on companion snaps",
        "body": (
            "Labor-force participation, employment-population ratio, "
            "employment, and labor-force levels now keep every state and "
            "D.C., so a Wyoming participation question can answer from the "
            "same BLS LAUS file. Other companion rankings that already "
            "parsed the full set keep those rows too. State Wealth Taxes "
            "and Florida Homeowners Insurance were not edited."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Landing drops the About label",
        "body": (
            "The front-door About section no longer prints an ABOUT "
            "eyebrow. The heading above the two briefing tiles is now "
            "New releases, matching Every application."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "One-month Pioneer staff beta",
        "body": (
            "The catalog is open for Pioneer staff from August 16 through "
            "September 16, 2026. This is not a public launch. Patents by "
            "State stays in build. Write jcalabrese@pioneerinstitute.org "
            "if a figure is wrong or a page is hard to read."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Insight bars draw again",
        "body": (
            "A missing color name in the suite chart script stopped every "
            "Compare a state bar, including labor-force participation on "
            "State Unemployment. Those figures draw again. One broken "
            "insight no longer blocks the rest of the page."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Housing Permits drops house-price charts",
        "body": (
            "Housing Permits now shows authorized units only. The "
            "Case-Shiller Boston and Miami indexes and the FHFA annual "
            "change bar are off the page. Those series stay in the ledger "
            "for Ask. The ledger was not rebuilt."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "One namesake, fewer bars",
        "body": (
            "Live pages outside State Wealth Taxes and Florida Homeowners "
            "Insurance now open on one namesake. Companion series stay as "
            "later views. Bars that only repeated the fifty-state map, or "
            "that mixed unlike units on one axis, are gone. Remaining "
            "state-comparison bars take a Compare a state control built "
            "from published cells only. Boston City Payroll opens on the "
            "citywide earnings total. Ledgers were not rebuilt."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Mismatched overlays use an index, first year = 100",
        "body": (
            "When United States, Massachusetts, and Florida cannot share "
            "one count axis, the headline trend now plots an index of each "
            "series' first year, set to 100, instead of percent change from "
            "that year. Lines start at 100. Hover still shows the raw "
            "figure. Charter enrollment, college, 340B sites, business "
            "applications, housing units, real GDP, energy CO2, "
            "Massachusetts vs Boston population, and Massachusetts tax "
            "collections by type take this path. Comparable "
            "series stay on their native scale. State Wealth Taxes and "
            "Florida Homeowners Insurance were not edited."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Education pages follow one namesake",
        "body": (
            "Massachusetts Schools now opens on Fall 2024 public-school "
            "enrollment, not U.S. per-pupil spending. The fifty-state "
            "spending map is gone from that page; spending, MCAS, and "
            "Chapter 74 stay as later views. State School Scores is locked "
            "to 2024 NAEP grade 4 reading for the hero, map, table, and "
            "vintage. College Enrollment no longer repeats the ranking as a "
            "bar chart. Charter Enrollment treats a published zero as zero "
            "and names the lowest count above zero. Staff charts on that "
            "page are labeled as all public schools. State Wealth Taxes and "
            "Florida Homeowners Insurance were not edited."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Catalog tiles a step lighter",
        "body": (
            "Catalog rows now use Pioneer Institute's paler blue "
            "(#CAD3E2). Hover still uses the earlier light blue. "
            "The masthead is unchanged."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Open for Pioneer staff beta",
        "body": (
            "The front door now reads Internal beta for Pioneer staff. "
            "About says what to try and where to write. This is not a "
            "public launch. Patents by State stays in build."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Corrections go to Jim Calabrese",
        "body": (
            "Every tool and the front door now list "
            "jcalabrese@pioneerinstitute.org for corrections. The "
            "shared DataLabs inbox is no longer published."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Catalog tiles in Pioneer light blue",
        "body": (
            "Catalog rows now use Pioneer Institute's light blue "
            "(#859DC1) instead of the header navy, so the directory "
            "is lighter than the masthead. Type on those tiles is "
            "navy. New Releases and the header are unchanged."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Masthead and footer use Pioneer blue",
        "body": (
            "The front-door heading and footer, and the heading on every "
            "data tool, now use Pioneer Institute's header and footer "
            "blue (#293C5C). The near-black chrome is gone. Ledgers and "
            "figures are unchanged."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Suite refresh unblocked, and close-of-day hygiene",
        "body": (
            "The monthly suite rebuild now expects all 27 suite apps, "
            "including Legislature Pay. Unused one-off migration scripts "
            "are gone. The landing page no longer embeds an unused "
            "all-sector electricity blob. Legislature Pay no longer prints "
            "an empty Tableau heritage line. Repeated later-view vintage "
            "notes are collapsed. 340B now names the mixed HRSA and CMS "
            "vintages. The ask-engine goldens include the national public "
            "starters. State Wealth Taxes and Florida Homeowners Insurance "
            "were not edited."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Fifty-state tools open on a national question",
        "body": (
            "Live fifty-state tools, including Retail Electricity Prices, "
            "now open on a United States question, the published national "
            "figure, and the same fifty-state map. A Place control rewrites "
            "that question, number, and clause for any published state. "
            "When the file has no U.S. row, the page opens on the highest "
            "state instead of inventing a national total. Massachusetts-only "
            "finders, agency lists, State Wealth Taxes, and Florida "
            "Homeowners Insurance were not edited."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Full history cubes and trailing-window ranks",
        "body": (
            "Live tools now keep the years and jurisdictions the published "
            "file already has, and the ask box reads precomputed trailing "
            "windows instead of averaging unpublished cells. Business "
            "Formation adds every BFS month from 2004, high-propensity and "
            "projected-formation columns from the same Census file, "
            "applications per 100,000 residents, and BLS establishment "
            "birth and death rates for all 51 jurisdictions, including the "
            "9-quarter window ending 2024 Q3. Unemployment, housing "
            "permits, quarterly taxes, and the other live cubes pick up "
            "the same window ranks. Faculty, FEMA, Boston payroll, and "
            "Census of Governments companions already on those ledgers "
            "are later views. Patents by State stays in build. State "
            "Wealth Taxes and Florida Homeowners Insurance were not edited."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Catalog cards name the tool and what it covers",
        "body": (
            "Each catalog row now leads with the tool name and the coverage "
            "line already on the catalog, not a Massachusetts figure. The "
            "numbers stay on the tool pages."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "One page spine, Census Albers maps, and a quieter catalog",
        "body": (
            "Live tools other than State Wealth Taxes and Florida Homeowners "
            "Insurance now open on the public starter question, one large "
            "number, and a matching first figure. Ask chips sit below that "
            "figure. Fifty-state maps use a Census Albers USA drawing, or a "
            "tile grid for ranks such as unemployment and NAEP, with a numeric "
            "legend and no Florida outline on this pass. Suite insight charts "
            "are capped at two. The front-door catalog leads with the "
            "Massachusetts number already on each tool, and Patents by State "
            "stays in build, quieter than the live rows. No flagship ledger "
            "cells were rewritten."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Ask chips on State Wealth Taxes and Florida Homeowners Insurance",
        "body": (
            "State Wealth Taxes and Florida Homeowners Insurance now open "
            "with the same four audience starter questions as the rest of "
            "the live catalog, wired to the page ask box. Patents by State "
            "is still the only live-looking tool without them, and it "
            "remains in build."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Find-card units, education leads, and household electricity tab",
        "body": (
            "State GDP find cards now scale millions of dollars the same way "
            "the charts do. Ranking tables and find cards name the unit "
            "instead of Value. About and Status say only Patents by State "
            "is in build. Massachusetts Schools and State School Scores "
            "now open on the story in the title. The Households jump on "
            "Retail Electricity Prices lands on the residential map and "
            "updates the standfirst."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Landing masthead marks the catalog as Beta",
        "body": (
            "The front door now reads DataLabs Beta. The supporting line "
            "says this is an internal staff review. The browser tab and "
            "share title say the same."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Audience starters, household power prices, and taxpayer destinations",
        "body": (
            "Every live tool except State Wealth Taxes and Florida "
            "Homeowners Insurance now opens with four starter questions, "
            "one each for the general public, a journalist, a researcher, "
            "and a policymaker, wired to the ask box. Retail Electricity "
            "Prices now publishes the EIA-861 residential, commercial, and "
            "industrial averages, so a household question has a household "
            "number. Taxpayer Migration now names the largest destinations "
            "from Massachusetts, including the Florida pair, from the same "
            "IRS state files. Companion series already on Labor, Migration, "
            "GDP, Energy, State Tax Collections, and the school tools sit "
            "in the jump nav."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Ask box on, and darker New Releases tiles",
        "body": (
            "The front-door question box is on and sits in the dark header "
            "band. The two New Releases tiles use the same dark field as "
            "the masthead: white titles, steel supporting lines, gold for "
            "the ask prompts. Questions still write to the site question "
            "log. ?ai=0 hides the box."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Each tool opens with the namesake trend",
        "body": (
            "Live tools that have a time series now open with that line, "
            "right after the headline numbers, so the first chart answers "
            "whether the figure in the tool name has risen or fallen. "
            "When the file has every state, a selector adds a state to "
            "the United States, Massachusetts, and Florida lines. Charter "
            "enrollment, college enrollment, school enrollment, business "
            "applications, unemployment, GDP, migration, cost of living, "
            "and energy CO2 compile those state series from the same "
            "published files. Retail electricity prices already had the "
            "selector; that line is now Figure 1. Tools without a published "
            "history still open on the snapshot they have. No flagship "
            "ledger cells were rewritten."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "The fifty-state table sits on a map tab",
        "body": (
            "The ranking of every state no longer sits under the country "
            "map. That table is a tab on the map. Click a state to open "
            "its row. Extra views, such as sales and generation on Retail "
            "Electricity Prices, share the same United States graphic."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "One country map, colored by the ranking",
        "body": (
            "Each state tool keeps a single United States map. The ranking "
            "is the color on the states. The list of states and the strip "
            "under the map are gone. Extra state views, such as NAEP "
            "change, sit as tabs on that one map."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Catalog names say what the page is",
        "body": (
            "Tool names now name the live figure, not the sector or a "
            "metaphor. State Tax Atlas is State Wealth Taxes. Florida "
            "Insurance Watch is Florida Homeowners Insurance. Transportation "
            "and MBTA is MBTA Performance. Suite titles follow the same "
            "rule, from Charter Enrollment to State Imprisonment. URLs "
            "are unchanged."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "State maps, trends, and lists",
        "body": (
            "Fifty-state maps are larger, with steel borders and a Northeast "
            "panel so small states are easier to click. Click a state to open "
            "its row. The change-since-first-year chart now lines up each "
            "series on one timeline, including Florida. Massachusetts and "
            "Florida are no longer marked in the every-state list; the map "
            "and trend lines still use gold and rust."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Catalog names match what the page can show",
        "body": (
            "Catalog names now match the page. Charters and Teachers replaces "
            "Charters and School Staff. Medicaid Spending and Fraud replaces "
            "Medicaid and State Health Spending. Headings name only topics "
            "the page can show. New figures cover attendance, dropouts, "
            "district PPE, the national six-year rate, bachelor's-or-higher "
            "shares, public-campus payroll, and prisoner releases."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Fifty-state figures are maps",
        "body": (
            "Any ranking that covers the fifty states is now a United States "
            "map instead of a tall bar chart. Darker navy is a higher value. "
            "Massachusetts keeps a gold outline and Florida a rust outline. "
            "Hover a state for the figure; the table still lists every row."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Massachusetts K-12 enrollment on the page",
        "body": (
            "Massachusetts K-12 now opens with public-school enrollment from "
            "Fall 1990 through Fall 2024. The figure is NCES Digest table "
            "203.20, the same published cells as the National K-12 ranking."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Tool sitebars match the landing masthead",
        "body": (
            "Every tool page now uses the same dark field as the front door: "
            "white Pioneer wordmark and links, no gold rule. The page title "
            "and figures below the bar are unchanged."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "New Releases as two briefing tiles",
        "body": (
            "The two New Releases entries on the front door are now equal "
            "institutional tiles: gold hairline, serif title, finding, and "
            "vintage. Florida Insurance Watch and the State Tax Atlas are "
            "unchanged as the only releases."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Chart labels stay off the lines",
        "body": (
            "Value labels now skip a placement when they would sit on a series "
            "stroke or a neighboring bar. Multi-series line ends stack in a "
            "right-hand column so the figures do not pile up on the last point. "
            "A white halo keeps type readable when a label must sit near a line."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Florida on every US-tool chart that already shows Massachusetts",
        "body": (
            "Live US tools that already plot Massachusetts now carry the "
            "matching Florida series from the same published files. County "
            "and state compare figures keep both states in view. The "
            "underlying cells are unchanged."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "340B rebuilt from OPAIS, CMS, and Census",
        "body": (
            "The three 340B tools are live on one page. Program growth is "
            "participating covered-entity sites and unique contract pharmacies "
            "from the HRSA OPAIS daily export. Hospital charity care is "
            "Worksheet S-10 cost as a share of total costs on the CMS Hospital "
            "Provider Cost Report PUF, the public file behind RAND TL-303. "
            "Legislative mapping assigns each pharmacy ZIP to a 2024 state "
            "house district by Census ZCTA land-area majority. Patents and "
            "Innovation remains in build."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Landing masthead matches the footer",
        "body": (
            "The front-door header now uses the same dark field as the footer: "
            "white wordmark and links, steel deck line. The light wash and gold "
            "rule are gone so the masthead reads against the white page."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Florida in rust, with a matching KPI",
        "body": (
            "Florida is now rust, a higher-contrast mark next to Massachusetts "
            "in gold. Every fifty-state tool carries a Florida KPI on the same "
            "metric. Ranking charts and compare figures already keep both states "
            "in view. The landing masthead has a light wash and a gold rule."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Florida marked on the fifty-state tools",
        "body": (
            "State ranking charts and tables now mark Florida in steel next to "
            "Massachusetts in gold. Both states stay on the chart when they "
            "are outside the top twelve. Figures are unchanged."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "A white institutional field",
        "body": (
            "The cream bands are gone. Pages now use a white field, near-black "
            "type, and cool hairline rules. Gold is a thin rule under the "
            "wordmark only. The footer no longer carries a gold stripe."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Charts read as a statistical brief",
        "body": (
            "Figures now use a shared paper theme: Roboto ticks, square bars, "
            "straight lines without dots, hairline grids, and a square ink "
            "tooltip. Gold remains the Massachusetts highlight."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Shorter copy on the tools",
        "body": (
            "Suite pages now open with one finding. Chart captions that only "
            "restated the figure are gone. The source register no longer "
            "repeats the full scope on every row."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Subtle institutional contrast",
        "body": (
            "Pages now carry a cream band under the title and the key figures, "
            "with slightly darker type and rules. The footer keeps a gold rule. "
            "Florida Insurance Watch and the State Tax Atlas pick up the same "
            "colors from the shared palette."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Catalog verticals fold closed",
        "body": (
            "The four Pioneer verticals on the front door are dropdowns. "
            "Open Education, Healthcare, Economic Opportunity, or American "
            "Citizenship to see the applications inside."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Pages read as papers",
        "body": (
            "The front door and the tools other than Florida Insurance Watch "
            "and the State Tax Atlas now open as white pages: a Pioneer "
            "masthead, one finding, then the table and charts. Gold is reserved "
            "for the wordmark rule. The ask box is not on the public page."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Version labels off the tools",
        "body": (
            "Tool pages no longer show a version number in the masthead, "
            "footer, or how-to-cite line. The data vintage and revised date remain."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Catalog in A-Z order",
        "body": (
            "Applications inside each Pioneer vertical are now listed "
            "alphabetically by name, so Education, Healthcare, Economic "
            "Opportunity, and American Citizenship each read as a register."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "A quieter front door",
        "body": (
            "Catalog rows now show the application name, place, and vintage. "
            "The DL codes and one-line comments are gone. The two New Releases "
            "entries are ruled columns, not cards, and the line under the "
            "heading is gone."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Legislature pay by person",
        "body": (
            "The Legislature Pay table now shows each member's base salary, "
            "Comptroller supplemental pay, stipend, and total for calendar 2025, "
            "not only the combined figure. Type a name to jump to that row."
        ),
    },
    {
        "date": "August 16, 2026",
        "title": "Two-line trends on a shared scale",
        "body": (
            "When a trend chart overlays series of very different size, "
            "such as Massachusetts and Boston population, the lines are now "
            "percent change from the first year. Hover a point for the raw "
            "count. Each series has its own color."
        ),
    },
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
    <a class="piword" href="https://pioneerinstitute.org">Pioneer Institute</a>
    <a class="backlink" href="/">DataLabs catalog</a>
    <a class="nav" href="/#about">About</a>
    <a class="nav" href="/status/">Status</a>
    <a class="nav" href="/changelog/">Changelog</a>
  </div>
</div>
<header>
  <h1>{esc(title)}</h1>
  <div class="standfirst">{esc(standfirst)}</div>
  <div class="byline">Pioneer Institute DataLabs</div>
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
  <p class="lede">Vintage and refresh cadence for every DataLabs application. The vintage on each catalog row is the vintage of the data inside. This table adds the freshness gate and the job that is supposed to move it.</p>
  <p class="body-p">{live} applications are live. {build} {"is" if build == 1 else "are"} in build. {stale} {"is" if stale == 1 else "are"} past {"its" if stale == 1 else "their"} freshness gate. Table generated {TODAY_LABEL} from the ledgers in this repository.</p>
  <p class="body-p">The catalog is in a one-month internal beta for Pioneer staff, August 16 through September 16, 2026. Questions asked at the front door are written to the site question log so the next tool can come from demand, not from a bigger catalog. Individual questions are not published here. The ask box is on at the front door. Use ?ai=0 to hide it.</p>
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
