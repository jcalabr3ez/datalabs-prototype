#!/usr/bin/env python3
"""Render house-style pages for every suite app from its ledger."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audience_starters import starters_html
from insight_figures import insight_figures
from page_voice import (
    census_place_names,
    display_lead,
    mixed_vintage_lines,
    place_strip_html,
    short_place_text,
    source_vintage,
    table_value_label,
    uses_national_lens,
    voice_for,
)
from suite_common import ROOT, catalog_dashboards, commify, load_apps, ledger_path, paper_dateline

def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def src_rows(ledger):
    lines = []
    for sid, s in ledger.get("source_id_map", {}).items():
        vintage = source_vintage(ledger, sid, s)
        lines.append(
            "<tr><td class=\"src\"><a href=\"" + esc(s.get("url", "#"))
            + "\" target=\"_blank\" rel=\"noopener\">" + esc(s.get("name", sid))
            + " (" + esc(sid) + ")</a></td><td>" + esc(s.get("cadence", ""))
            + "</td><td>" + esc(vintage)
            + "</td><td>" + esc(s.get("cadence", "See publisher"))
            + "</td></tr>"
        )
    return "\n          ".join(lines)


REGION_BAR = """    <div class="region-bar" hidden>
      <span class="sel-lab">Census region</span>
      <div class="region-chips" role="group" aria-label="Filter by Census region">
        <button type="button" data-region="all" class="on">All states</button>
        <button type="button" data-region="northeast">Northeast</button>
        <button type="button" data-region="midwest">Midwest</button>
        <button type="button" data-region="south">South</button>
        <button type="button" data-region="west">West</button>
      </div>
    </div>
"""

EXPLORE_BAR = """    <div class="explore-bar" hidden>
      <span class="sel-lab">Show</span>
      <div class="region-chips" role="group" aria-label="Filter the ranking">
        <button type="button" data-band="all" class="on">All</button>
        <button type="button" data-band="above" hidden>Above U.S.</button>
        <button type="button" data-band="below" hidden>Below U.S.</button>
        <button type="button" data-band="top10">Top 10</button>
        <button type="button" data-band="bottom10">Bottom 10</button>
      </div>
    </div>
"""

def kpi_html(kpis):
    blocks = []
    srcs = []
    cells = [k for k in (kpis or []) if k and k.get("value") not in (None, "", "see register")][:4]
    for k in cells:
        src = (k.get("src") or "").strip()
        if src and src not in srcs:
            srcs.append(src)
        blocks.append(
            "      <div class=\"cell\">\n"
            "        <div class=\"cl\">" + esc(k["label"]) + "</div>\n"
            "        <div class=\"cv\">" + esc(k["value"]) + "</div>\n"
            "        <div class=\"cd\">" + k["detail"] + "</div>\n"
            "      </div>"
        )
    html = "\n".join(blocks)
    if srcs:
        html += (
            "\n      <div class=\"cell kpi-src\">\n"
            "        <div class=\"csrc\">Source: "
            + esc("; ".join(srcs))
            + "</div>\n"
            "      </div>"
        )
    return html


def lens_html(answers):
    if not answers or not answers.get("US"):
        return ""
    us = answers["US"]
    us_lab = "Highest" if us.get("kind") == "rank" else "United States"
    opts = ['<option value="US">' + esc(us_lab) + "</option>"]
    keys = []
    if "MA" in answers:
        keys.append("MA")
    keys.extend(sorted(
        (k for k in answers if k not in ("US", "MA")),
        key=lambda k: (answers[k].get("geo") or k),
    ))
    for k in keys:
        lab = answers[k].get("geo") or k
        opts.append('<option value="' + esc(k) + '">' + esc(lab) + "</option>")
    return (
        '    <div class="lens-bar" id="lensBar">\n'
        '      <label class="sel-lab" for="lensSel">Place</label>\n'
        '      <select id="lensSel" aria-label="United States or a state">'
        + "".join(opts)
        + "</select>\n"
        "    </div>\n"
    )


def answer_html(answer, kpis_markup="", slug="", vintages=None, answers=None):
    if not answer or not answer.get("value"):
        return ""
    ctx = answer.get("context") or ""
    cite = answer.get("cite") or ""
    meta_bits = [b for b in (
        answer.get("geo"),
        answer.get("vintage"),
        answer.get("src_id"),
    ) if b]
    kpi_block = ""
    if kpis_markup:
        begin = f"<!-- DATA:BEGIN {slug}-kpis -->" if slug else ""
        end = f"<!-- DATA:END {slug}-kpis -->" if slug else ""
        kpi_block = (
            '    <div class="strip metrics">\n'
            + (begin + "\n" if begin else "")
            + kpis_markup
            + ("\n" + end + "\n" if end else "\n")
            + "    </div>\n"
        )
    vintage_block = ""
    mixed = [v for v in (vintages or []) if v and v[1]]
    if len({v[1].lower() for v in mixed}) >= 2:
        parts = []
        for name, lab in mixed[:6]:
            if name:
                parts.append(esc(name) + ": " + esc(lab))
            else:
                parts.append(esc(lab))
        vintage_block = (
            '    <p class="vintage-mix">Figures on this page mix vintages. '
            + "; ".join(parts)
            + ".</p>\n"
        )
    cite_btn = ""
    if cite:
        cite_btn = (
            '    <button type="button" class="cite-copy" data-cite="'
            + esc(cite)
            + '">Copy citation</button>\n'
        )
    meta_html = ""
    if meta_bits:
        meta_html = (
            '    <p class="answer-meta" id="answerMeta">'
            + esc(" · ".join(str(b) for b in meta_bits))
            + "</p>\n"
        )
    return (
        '  <section id="answer" class="answer-block">\n'
        + lens_html(answers)
        + "    <h2 id=\"answerQ\">" + esc(answer.get("q") or "The finding") + "</h2>\n"
        '    <div class="answer-num" id="answerNum">' + esc(answer["value"]) + "</div>\n"
        + place_strip_html(answers)
        + ('    <p class="answer-ctx" id="answerCtx">' + esc(ctx) + "</p>\n" if ctx else "")
        + meta_html
        + cite_btn
        + vintage_block
        + kpi_block
        + "  </section>\n"
    )


TOWN_TOOLS = {"DL-25", "DL-26"}
FINDER_TOOLS = {"DL-10", "DL-25", "DL-26"}
HIST_TOOLS = {"DL-32"}


def ranked_state_rows(rows, val_key="v"):
    items = []
    for r in rows or []:
        if not r.get("st") or r.get(val_key) is None:
            continue
        items.append({
            "st": r["st"],
            "name": r.get("name") or r["st"],
            "v": r[val_key],
            "rank": r.get("rank"),
        })
    items.sort(key=lambda x: -float(x["v"]))
    n = len(items)
    for i, rec in enumerate(items, 1):
        rec["rank"] = i
        rec["n"] = n
    return items


def naep_score_rows(ledger):
    hist = (
        ((ledger.get("derived") or {}).get("secondary") or {})
        .get("naep_2024") or {}
    ).get("history") or {}
    rec = ((hist.get("read4") or {}).get("change_2019_2024") or {})
    return ranked_state_rows(rec.get("rows") or [], val_key="to")


def src_cite(ledger, sid=None):
    smap = ledger.get("source_id_map") or {}
    if not sid:
        sid = next(iter(smap), "")
    rec = smap.get(sid) or {}
    name = rec.get("name") or "see the register"
    if sid:
        return name + " (" + sid + ")"
    return name


def replaces_list(app, ledger):
    items = ledger.get("replaces") or app.get("replaces") or []
    return ", ".join(items)


def dashboards_html(app):
    items = catalog_dashboards(app)
    if not items:
        return ""
    cards = []
    for d in items:
        host = ""
        raw = d.get("u") or ""
        if "://" in raw:
            host = raw.split("://", 1)[1].split("/", 1)[0]
            if host.startswith("www."):
                host = host[4:]
        note = d.get("q") or ""
        cards.append(
            '      <a class="dash" href="' + esc(raw) + '" target="_blank" rel="noopener">'
            '<span class="dash-t">' + esc(d["t"]) + "</span>"
            + ('<span class="dash-n">' + esc(note) + "</span>" if note else "")
            + ('<span class="dash-h">Opens on ' + esc(host) + "</span>" if host else "")
            + "</a>"
        )
    return (
        '  <section id="dashboards">\n'
        "    <h2>Current dashboards</h2>\n"
        '    <p class="lede">This DataLabs page is in build. The live Tableau workbooks stay up until the ledger is compiled.</p>\n'
        '    <div class="dashes">\n'
        + "\n".join(cards)
        + "\n    </div>\n"
        "  </section>\n"
    )


LIMIT_MARKERS = (
    "waitlist", "not published", "not in this", "omitted", "pending",
    "not comparable", "no state column", "so the state bars",
    "so state bars", "does not draw", "not drawn", "remain pending",
    "not a published", "not posted", "not in the statewide",
    "not in that", "gaps are years",
)


def figure_limit(fig):
    """Keep a chart note only when it states a limit, not when it restates the figure."""
    for text in (fig.get("note") or "", fig.get("lede") or ""):
        low = text.lower()
        if text.strip() and any(m in low for m in LIMIT_MARKERS):
            return text.strip()
    return ""


def insight_html(insights, start=1):
    if not insights:
        return ""
    blocks = []
    for i, fig in enumerate(insights):
        span = " span2" if fig.get("span") == 2 or len(insights) == 1 else ""
        if fig.get("type") == "map" or fig.get("height") == "map":
            hclass = "plot plot-map"
        elif fig.get("type") in ("hist", "slope", "dots"):
            hclass = "plot"
        elif fig.get("height") == "mid":
            hclass = "plot"
        elif fig.get("height") == "ranks":
            hclass = "plot-ranks"
        elif fig.get("span") == 2 or len(insights) == 1:
            hclass = "plot"
        else:
            hclass = "plot"
        note = figure_limit(fig)
        note_html = (
            "      <div class=\"note\">" + esc(note) + "</div>\n" if note else ""
        )
        lede_html = (
            "      <div class=\"lede\">" + esc(fig.get("lede")) + "</div>\n"
            if fig.get("lede") else ""
        )
        fid = fig.get("id") or ("fig" + str(start + i))
        pick = ""
        if fig.get("type") == "bar" and len(fig.get("filter_states") or []) >= 3:
            pick = (
                '      <div class="findrow insight-pick" id="insightPick'
                + str(i)
                + '">\n'
                '        <label class="sel-lab" for="insightSel'
                + str(i)
                + '">Compare a state</label>\n'
                '        <select id="insightSel'
                + str(i)
                + '" aria-label="Compare a state"></select>\n'
                "      </div>\n"
            )
        blocks.append(
            "    <div class=\"exhibit" + span + "\" id=\"insight-" + esc(fid) + "\">\n"
            "      <div class=\"ex-head\"><span class=\"ex-n\">Figure " + str(start + i) + "</span>\n"
            "        <span class=\"ex-t\">" + esc(fig["title"]) + "</span></div>\n"
            + lede_html
            + pick
            + "      <div class=\"" + hclass + "\""
            + (" id=\"chInsight" + str(i) + "\"" if fig.get("type") == "map" else "")
            + ">"
            + ("" if fig.get("type") == "map" else "<canvas id=\"chInsight" + str(i) + "\"></canvas>")
            + "</div>\n"
            + note_html
            + "      <div class=\"srcline\"><b>Source:</b> " + esc(fig.get("src") or "see the register")
            + ". <b>Unit:</b> " + esc(fig.get("unit") or "see the register") + ".</div>\n"
            "    </div>"
        )
    return (
        "  <section id=\"insights\">\n"
        "    <div class=\"insight-grid\">\n"
        + "\n".join(blocks)
        + "\n    </div>\n"
        "  </section>\n"
    )


def later_view_html(later, start_fig, canvas_start):
    """First-class later exhibits beyond the two-insight cap."""
    if not later:
        return ""
    blocks = []
    for i, fig in enumerate(later):
        fid = fig.get("id") or ("later" + str(i))
        note = figure_limit(fig)
        note_html = (
            "      <div class=\"note\">" + esc(note) + "</div>\n" if note else ""
        )
        pick = ""
        idx = canvas_start + i
        if fig.get("type") == "bar" and len(fig.get("filter_states") or []) >= 3:
            pick = (
                '    <div class="findrow insight-pick" id="insightPick'
                + str(idx)
                + '">\n'
                '      <label class="sel-lab" for="insightSel'
                + str(idx)
                + '">Compare a state</label>\n'
                '      <select id="insightSel'
                + str(idx)
                + '" aria-label="Compare a state"></select>\n'
                "    </div>\n"
            )
        lede = (
            ('    <div class="lede">' + esc(fig.get("lede")) + "</div>\n")
            if fig.get("lede") else ""
        )
        blocks.append(
            "  <section id=\"view-" + esc(fid) + "\">\n"
            "    <h2>" + esc(fig.get("title") or fid) + "</h2>\n"
            + lede
            + pick
            + "    <div class=\"exhibit span2\">\n"
            "      <div class=\"ex-head\"><span class=\"ex-n\">Figure "
            + str(start_fig + i) + "</span>\n"
            "        <span class=\"ex-t\">" + esc(fig.get("title") or fid) + "</span></div>\n"
            "      <div class=\"plot\"><canvas id=\"chInsight"
            + str(idx) + "\"></canvas></div>\n"
            + note_html
            + "      <div class=\"srcline\"><b>Source:</b> "
            + esc(fig.get("src") or "see the register")
            + ". <b>Unit:</b> " + esc(fig.get("unit") or "see the register") + ".</div>\n"
            "    </div>\n"
            "  </section>\n"
        )
    return "".join(blocks)


RELATED_PAIRS = {
    "DL-06": ["DL-07", "DL-09", "DL-08"],
    "DL-07": ["DL-06", "DL-08", "DL-09"],
    "DL-08": ["DL-07", "DL-06"],
    "DL-09": ["DL-06", "DL-07"],
    "DL-10": ["DL-11", "DL-12", "DL-33"],
    "DL-11": ["DL-10", "DL-12"],
    "DL-12": ["DL-10", "DL-11"],
    "DL-33": ["DL-10", "DL-12"],
    "DL-13": ["DL-14", "DL-15"],
    "DL-14": ["DL-13", "DL-15"],
    "DL-15": ["DL-14", "DL-19"],
    "DL-16": ["DL-17", "DL-19"],
    "DL-17": ["DL-16", "DL-20", "DL-25"],
    "DL-19": ["DL-15", "DL-20"],
    "DL-20": ["DL-17", "DL-21"],
    "DL-21": ["DL-20"],
    "DL-22": ["DL-03"],
    "DL-23": ["DL-22", "DL-24"],
    "DL-24": ["DL-04", "DL-23"],
    "DL-25": ["DL-26", "DL-27"],
    "DL-26": ["DL-25", "DL-27"],
    "DL-27": ["DL-25", "DL-26"],
    "DL-28": ["DL-29", "DL-30"],
    "DL-29": ["DL-28", "DL-21"],
    "DL-30": ["DL-32", "DL-28"],
    "DL-31": ["DL-26"],
    "DL-32": ["DL-30", "DL-28", "DL-05"],
}

FLAGSHIP_LINKS = {
    "DL-01": {"title": "State Wealth Taxes", "slug": "tax-atlas"},
    "DL-03": {"title": "MBTA Performance", "slug": "mbta"},
    "DL-04": {"title": "Retail Electricity Prices", "slug": "electricity"},
    "DL-05": {"title": "Massachusetts Public Pensions", "slug": "pensions"},
}


def related_html(app, apps):
    by_id = {a["id"]: a for a in apps}
    seen = {app["id"]}
    picks = []

    def add(tid):
        if tid in seen:
            return
        if tid in FLAGSHIP_LINKS:
            seen.add(tid)
            picks.append(FLAGSHIP_LINKS[tid])
            return
        other = by_id.get(tid)
        if other:
            seen.add(tid)
            picks.append({"title": other["title"], "slug": other["slug"]})

    for tid in RELATED_PAIRS.get(app["id"], []):
        add(tid)
        if len(picks) >= 3:
            break
    if len(picks) < 3:
        for other in apps:
            if other["id"] in seen:
                continue
            if other.get("group") == app.get("group"):
                add(other["id"])
            if len(picks) >= 3:
                break
    if not picks:
        return ""
    links = "".join(
        '<a href="/' + esc(p["slug"]) + '/">' + esc(p["title"]) + "</a>"
        for p in picks[:3]
    )
    return (
        '  <section id="related">\n'
        "    <h2>Related applications</h2>\n"
        '    <div class="related">' + links + "</div>\n"
        "  </section>\n"
    )


TREND_NAMES = {"US": "United States", "MA": "Massachusetts", "FL": "Florida", "Boston": "Boston"}
TREND_LEDE_NAMES = {"US": "the United States", "MA": "Massachusetts", "FL": "Florida", "Boston": "Boston"}
TREND_CORE_KEYS = ("US", "MA", "FL", "Boston")
TREND_INDEX_RATIO = 2.5
TREND_INDEX_UNIT = "Indexed to each series' first year (100 = starting level)"
TREND_INDEX_NOTE = (
    "Indexed to each series' first year (100 = starting level). "
    "The dashed line is the starting level. Hover a point for the raw figure, then the index."
)
JUMP_SHORT = {
    "ch74-seats": "Chapter 74",
    "ch74-programs": "CTE programs",
    "mcas-2025": "MCAS",
    "attendance-2025": "Attendance",
    "dropouts-2025": "Dropouts",
    "dist-ppe-ma": "District spending",
    "ma-race": "Enrollment by race",
    "ma-selected": "Selected populations",
    "ma-grades": "Enrollment by grade",
    "ppe-compare": "Per-pupil spending",
    "naep-read4-slope": "NAEP change",
    "npefs-ppe": "Per-pupil spending",
    "sat-2023": "SAT",
    "faculty-ft": "Faculty",
    "he-faculty": "Public faculty",
    "he-ratio": "Students per faculty",
    "ipeds-6yr-state": "Graduation rate",
    "he-tuition": "Tuition",
    "he-approp": "Appropriations",
    "he-exp": "Expenditures",
    "he-ba": "Bachelor's degrees",
    "fhfa-hpi": "House prices",
    "cs-boston": "Boston and Miami",
    "teachers-fte": "Teachers",
    "k12-staff": "Staff",
    "k12-aides": "Aides",
}

# Opening line: the namesake question. Select-a-state copy is added in JS
# when more than the core series exist.
HEADLINE = {
    "DL-06": {
        "title": "Massachusetts public-school enrollment over time",
        "lede": (
            "Fall enrollment in Massachusetts public schools. "
            "This is the stock the rest of the page sits on."
        ),
        "from": "secondary.public_k12_enrollment",
    },
    "DL-07": {
        "title": "NAEP grade 4 reading over time",
        "lede": (
            "National public and Massachusetts scale scores. "
            "The map on this page is the 2024 ranking, not enrollment."
        ),
        "from": "skip",
    },
    "DL-08": {
        "title": "College enrollment over time",
        "lede": (
            "Fall enrollment in degree-granting postsecondary institutions. "
            "The United States line is the national stock. Select a state to add it."
        ),
    },
    "DL-09": {
        "title": "Charter enrollment over time",
        "lede": (
            "Fall enrollment in public charter schools. The United States "
            "line shows whether the national charter stock has risen or "
            "fallen. Select a state to add it."
        ),
    },
    "DL-11": {
        "title": "340B sites over time",
        "lede": (
            "Currently participating 340B sites by the year they started. "
            "A site that later left is not in this series."
        ),
    },
    "DL-13": {
        "title": "Business applications over time",
        "lede": (
            "Seasonally adjusted business applications. The United States "
            "line shows whether formation has risen or fallen. Select a "
            "state to add it."
        ),
    },
    "DL-14": {
        "title": "Unemployment rate over time",
        "lede": (
            "Seasonally adjusted statewide unemployment rates. The U.S. "
            "civilian rate is not in this BLS file. Select a state to add it."
        ),
    },
    "DL-15": {
        "title": "Real GDP over time",
        "lede": (
            "Real GDP, chained 2017 dollars. The United States line is "
            "national output. Select a state to add it."
        ),
    },
    "DL-17": {
        "title": "Domestic migration over time",
        "lede": (
            "Domestic migration, not headcount. Select a state to add it."
        ),
    },
    "DL-19": {
        "title": "Cost of living over time",
        "lede": (
            "Regional price parities, United States = 100. Select a state "
            "to add it."
        ),
    },
    "DL-24": {
        "title": "Energy CO2 over time",
        "lede": (
            "Carbon dioxide from energy. The United States line is the "
            "national stock. Select a state to add it."
        ),
    },
    "DL-25": {
        "title": "Massachusetts population over time",
        "lede": "Statewide resident population, with Boston when the series exists.",
    },
}


def trend_compare_mode(trend, keys=None):
    """Index to 100 when two strictly positive series cannot share one level axis."""
    trend = trend or {}
    if keys is None:
        keys = [k for k in TREND_CORE_KEYS if trend.get(k)]
    if len(keys) < 2:
        keys = [k for k, v in trend.items() if v]
    series = [(k, trend.get(k)) for k in keys if trend.get(k)]
    if len(series) < 2:
        return "level"
    maxs = []
    all_pos = True
    for _k, pts in series:
        vs = []
        for p in pts:
            if not isinstance(p, dict) or p.get("v") is None:
                continue
            n = float(p["v"])
            if n <= 0:
                all_pos = False
            vs.append(abs(n))
        if vs:
            maxs.append(max(vs))
    if not all_pos or len(maxs) < 2 or min(maxs) == 0:
        return "level"
    return "index_100" if max(maxs) / min(maxs) >= TREND_INDEX_RATIO else "level"


def chart_spec(app, ledger):
    """Titles, units, and highlight for the shared suite charts."""
    tid = app["id"]
    unit = ledger.get("unit") or ""
    label = ledger.get("metric_label") or "Figure"
    n_rows = len(ledger.get("rows") or [])
    named = {
        "DL-10": ("hospital", 12, None),
        "DL-22": ("transit agency", 12, "Massachusetts Bay Transportation Authority"),
        "DL-25": ("city or town", 12, "Boston"),
        "DL-26": ("city or town", 12, "Boston"),
        "DL-27": ("department", 12, "Boston Police Department"),
        "DL-28": ("tax type", n_rows or 12, "Total Taxes"),
        "DL-30": ("department", 12, None),
        "DL-32": ("legislator", 12, None),
        "DL-33": ("income group", 5, "Less than 139% FPL"),
    }
    if tid in named:
        geo, n_chart, highlight = named[tid]
        n_chart = min(n_chart, n_rows) if n_rows else n_chart
    else:
        geo, n_chart, highlight = "state", (n_rows or 51), "MA"
    ulow = unit.lower()
    if "percent" in ulow:
        fmt = "percent"
    elif "star" in ulow:
        fmt = "stars"
    elif "million" in ulow and "dollar" in ulow:
        fmt = "usd_millions"
    elif "dollar" in ulow:
        fmt = "usd"
    else:
        fmt = "number"
    if tid == "DL-06":
        # Namesake is Fall enrollment. Spending stays a later view.
        fmt = "number"
        unit = "students"
    axis_unit = unit
    if fmt == "usd_millions":
        axis_unit = "chained 2017 dollars" if "chained" in ulow else "dollars"
    if geo == "state" or geo not in label.lower():
        title = label + " by " + geo
    else:
        title = label
    if n_rows and n_chart < n_rows and geo != "state" and tid not in TOWN_TOOLS | HIST_TOOLS | FINDER_TOOLS:
        title += f" (largest {n_chart} of {n_rows})"
    latest = ledger.get("latest") or {}
    us_raw = latest.get("us")
    if isinstance(us_raw, dict) and us_raw.get("v") is not None:
        us_val = us_raw.get("v")
    elif isinstance(us_raw, (int, float)):
        us_val = us_raw
    else:
        us_val = None
    state_vals = [
        r.get("v")
        for r in (ledger.get("rows") or [])
        if isinstance(r, dict) and r.get("v") is not None
    ]
    us_compare = (
        us_val is not None
        and state_vals
        and min(state_vals) <= us_val <= max(state_vals)
    )
    if tid == "DL-07":
        # Default map and table are NAEP scores, not enrollment vs the U.S.
        us_compare = False
    lede = ""
    if geo == "state":
        n_file = n_rows or n_chart
        series = (label or "").rstrip(".")
        if tid == "DL-07":
            series = "NAEP grade 4 reading, 2024"
        elif tid == "DL-08":
            series = "Fall enrollment in degree-granting institutions, 2022"
        elif tid == "DL-09":
            series = "Charter school fall enrollment, 2022-23"
        lede = series + "." if series else ""
        if n_file == 50:
            lede = (lede + " " if lede else "") + "The District of Columbia is not in this file."
        elif n_file == 46:
            lede = (lede + " " if lede else "") + "Not every state is in this file."
    headline = HEADLINE.get(tid) or {}
    trend_source = dict(ledger.get("trend") or {})
    if headline.get("from") == "secondary.public_k12_enrollment":
        enr = ((ledger.get("derived") or {}).get("secondary") or {}).get("public_k12_enrollment") or {}
        pts = enr.get("trend") or []
        if pts:
            trend_source = {"MA": pts}
    if headline.get("from") == "skip":
        trend_source = {}
    trend_keys = [k for k, v in trend_source.items() if v]
    has_trend = any(len(v) >= 2 for v in trend_source.values() if v)
    trend_mode = trend_compare_mode(trend_source)
    trend_names = [TREND_NAMES.get(k, k) for k in trend_keys]
    lede_names = [TREND_LEDE_NAMES.get(k, k) for k in trend_keys]
    if len(trend_names) == 2:
        trend_named = trend_names[0] + " and " + trend_names[1]
        trend_lede_named = lede_names[0] + " and " + lede_names[1]
    elif trend_names:
        trend_named = ", ".join(trend_names[:-1]) + ", and " + trend_names[-1]
        trend_lede_named = ", ".join(lede_names[:-1]) + ", and " + lede_names[-1]
    else:
        trend_named = ""
        trend_lede_named = ""
    if headline.get("title"):
        trend_title = headline["title"]
        trend_lede = headline.get("lede") or ""
        trend_unit = (
            "students"
            if headline.get("from") == "secondary.public_k12_enrollment"
            else unit
        )
    elif geo == "state":
        trend_title = (label or "The figure") + " over time"
        trend_lede = (
            "The line shows whether the figure has risen or fallen. "
            "Select a state to add it when that series is on file."
        )
        trend_unit = unit
    elif trend_mode == "index_100":
        trend_title = (label or "The figure") + " over time"
        trend_lede = TREND_INDEX_NOTE
        trend_unit = TREND_INDEX_UNIT
    else:
        trend_title = label + " over time"
        trend_lede = ""
        trend_unit = unit
    compare_title = {
        "state": (
            "Across the 50 states and D.C." if (n_rows or n_chart) == 51
            else "Across the 50 states" if (n_rows or n_chart) == 50
            else f"Across {n_rows or n_chart} jurisdictions"
        ),
        "hospital": "Compared with other hospitals",
        "transit agency": "Compared with other agencies",
        "city or town": "Compared with other cities and towns",
        "department": "Compared with other departments",
        "tax type": "Compared by tax type",
        "legislator": "Pay by person",
    }.get(geo, "Compared")
    table_noun = {
        "state": "Every state",
        "hospital": "Every hospital",
        "transit agency": "Every transit agency",
        "city or town": "Every city or town",
        "department": "Every department",
        "tax type": "Every tax type",
        "legislator": "Every legislator",
        "income group": "Every income group",
    }.get(geo, "Every row")
    col_name = {
        "state": "State",
        "hospital": "Hospital",
        "transit agency": "Agency",
        "city or town": "City or town",
        "department": "Department",
        "tax type": "Tax type",
        "legislator": "Legislator",
        "income group": "Income group",
    }.get(geo, "Name")
    if tid == "DL-11":
        table_columns = [
            {"key": "name", "label": "State", "cls": "m"},
            {"key": "v", "label": "Sites", "align": "n", "fmt": "value"},
            {"key": "pharmacies", "label": "Pharmacies", "align": "n", "fmt": "value"},
            {"key": "rank", "label": "Rank", "align": "n"},
        ]
        table_lede = (
            "Filter by Census region or by the top or bottom ten. Click a "
            "column head to sort. Type a name. Sites are currently "
            "participating 340B IDs. Pharmacies are unique active contract "
            "pharmacy IDs in that state."
        )
        table_note = (
            "Ranks are Pioneer calculations (derived, SRC-611-01). Year-over-year "
            "change is not on this file. The start-year trend is the current "
            "participating roster, not a reconstructed historical stock."
        )
        trend_title = "Currently participating sites by start year"
        trend_lede = (
            "Each line is the number of sites that are participating on the "
            "August 15, 2026 OPAIS file and that had a participating start date "
            "on or before that year. Sites that later left the program are not "
            "in this series."
        )
        trend_unit = "currently participating sites"
    elif tid == "DL-32":
        table_columns = [
            {"key": "name", "label": "Legislator", "cls": "m"},
            {"key": "chamber", "label": "Chamber"},
            {"key": "base", "label": "Base salary", "align": "n", "fmt": "usd_cents"},
            {"key": "aa1", "label": "Supplemental", "align": "n", "fmt": "usd_cents"},
            {"key": "a14", "label": "Stipend", "align": "n", "fmt": "usd_cents"},
            {"key": "v", "label": "Total", "align": "n", "fmt": "usd_cents"},
            {"key": "rank", "label": "Rank", "align": "n"},
        ]
        table_lede = "Type a name to jump to a row. Click a column head to sort."
        table_note = (
            "Amounts are the published CTHRU named-employee lines. Ranks are "
            "Pioneer calculations (derived). Year-over-year change is not on this file."
        )
    elif tid == "DL-07":
        table_columns = [
            {"key": "name", "label": "State", "cls": "m"},
            {"key": "v", "label": "Scale score", "align": "n", "fmt": "value"},
            {"key": "rank", "label": "Rank", "align": "n"},
        ]
        table_lede = (
            "Filter by Census region or by the top or bottom ten. Click a "
            "column head to sort. Type a name to jump to a row. Year-over-year "
            "change is not on this NAEP file."
        )
        table_note = (
            "Ranks are Pioneer calculations (derived, SRC-607-05). "
            "The table is the 2024 grade 4 reading scale, not enrollment."
        )
    elif tid == "DL-33":
        table_columns = [
            {"key": "name", "label": "Income group", "cls": "m"},
            {"key": "v", "label": "High OOP burden", "align": "n", "fmt": "percent"},
            {"key": "rank", "label": "Rank", "align": "n"},
        ]
        table_lede = (
            "Family income as a percent of the federal poverty level. "
            "The share is residents in families with a high out-of-pocket "
            "burden, not a dollar average."
        )
        table_note = (
            "CHIA counts out-of-pocket costs above 5 percent of income below "
            "200 percent FPL, or above 10 percent at or above 200 percent FPL. "
            "Ranks are Pioneer calculations (derived, SRC-633-02)."
        )
    else:
        table_columns = [
            {"key": "name", "label": col_name, "cls": "m"},
            {"key": "v", "label": table_value_label(unit, label), "align": "n", "fmt": "value"},
            {"key": "rank", "label": "Rank", "align": "n"},
            {"key": "yoy_pct", "label": "YoY", "align": "n", "kind": "yoy"},
        ]
        table_lede = (
            (
                "Filter by Census region"
                + (", by place against the U.S.," if us_compare else ",")
                + " or by the top or bottom ten. Click a column head to sort. "
                "Type a name to jump to a row."
            )
            if geo == "state"
            else "Type a name to jump to a row. Click a column head to sort."
        )
        table_note = (
            "Ranks and year-over-year changes are Pioneer calculations (derived)."
        )
    if trend_mode == "index_100":
        trend_unit = TREND_INDEX_UNIT
        if "set to 100" not in (trend_lede or ""):
            trend_lede = ((trend_lede.rstrip() + " ") if trend_lede else "") + TREND_INDEX_NOTE
    if tid == "DL-11":
        compare_title = "Program growth"
        table_noun = "Every state"
    return {
        "geo": geo,
        "format": fmt,
        "highlight": highlight,
        "highlights": (["MA"] if geo == "state" else ([highlight] if highlight else [])),
        "n_chart": n_chart,
        "unit": unit,
        "axis_unit": axis_unit,
        "label": label,
        "title": title,
        "compare_title": compare_title,
        "lede": lede,
        "has_trend": has_trend,
        "headline_from": headline.get("from") or "",
        "table_noun": table_noun,
        "col_name": col_name,
        "table_columns": table_columns,
        "table_lede": table_lede,
        "table_note": table_note,
        "trend_mode": trend_mode,
        "trend_title": trend_title,
        "trend_lede": trend_lede,
        "trend_unit": trend_unit,
        "us": us_val,
        "us_compare": us_compare,
        "map_mode": "hex",
        "compare": (
            "map" if geo == "state"
            else "town" if tid in TOWN_TOOLS
            else "hist" if tid in HIST_TOOLS
            else "finder" if tid in FINDER_TOOLS
            else "dots"
        ),
        "hero_finder": tid in FINDER_TOOLS,
        "show_map": tid != "DL-06",
    }


def _pct_rows_table(rows, value_label="Share"):
    body = []
    for r in rows or []:
        name = esc(r.get("name") or "")
        v = r.get("v")
        val = f"{v:.1f}%" if isinstance(v, (int, float)) else ""
        rank = r.get("rank") or ""
        body.append(
            f"<tr><td class=\"m\">{name}</td>"
            f"<td class=\"n\">{val}</td>"
            f"<td class=\"n\">{esc(rank)}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Group</th>"
        f"<th class=\"n\">{esc(value_label)}</th>"
        "<th class=\"n\">Rank</th></tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def extra_tool_sections(app, ledger, n_fig, has_trend):
    """Stacked later tools that do not fit the single ranking table."""
    if app["id"] == "DL-33":
        sec = ((ledger.get("derived") or {}).get("secondary") or {})
        fig = n_fig + (2 if has_trend else 1) + 1
        afford_i = sec.get("affordability_income") or {}
        afford_r = sec.get("affordability_race") or {}
        unmet = sec.get("unmet_need_types") or {}
        unmet_i = sec.get("unmet_need_income") or {}
        bills = sec.get("medical_bills_income") or {}
        latest = ledger.get("latest") or {}
        dist = sec.get("oop_share_distribution") or {}
        cov = sec.get("coverage_2025") or {}
        return f"""
<section id="view-afford">
    <h2>Family affordability</h2>
    <div class="lede">Two in five residents reported any family healthcare affordability issue in the past 12 months. The burden is higher below 400 percent of poverty and for Black and Hispanic residents.</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure {fig}</span>
        <span class="ex-t">Any family affordability issue by income</span></div>
      <div class="scroll">{_pct_rows_table(afford_i.get("rows"), "Share")}</div>
      <div class="srcline"><b>Source:</b> CHIA 2025 MHIS table D.1-5 (SRC-633-02). Ranks are Pioneer calculations (derived).</div>
    </div>
    <div class="scroll">{_pct_rows_table(afford_r.get("rows"), "Share")}</div>
    <div class="srcline"><b>Source:</b> CHIA 2025 MHIS table D.1-3 (SRC-633-02).</div>
  </section>
<section id="view-unmet">
    <h2>Unmet need due to cost</h2>
    <div class="lede">{latest.get("unmet_need_pct"):.1f} percent of residents were in families that went without needed care because of cost. Dental care and prescription drugs are the published type cuts on this page.</div>
    <div class="scroll">{_pct_rows_table(unmet.get("rows"), "Share")}</div>
    <div class="srcline"><b>Source:</b> CHIA 2025 MHIS table D.2-1 (SRC-633-02).</div>
    <div class="scroll">{_pct_rows_table(unmet_i.get("rows"), "Share")}</div>
    <div class="srcline"><b>Source:</b> CHIA 2025 MHIS table D.2-5 (SRC-633-02). Ranks are Pioneer calculations (derived).</div>
  </section>
<section id="view-debt">
    <h2>Medical bills and debt</h2>
    <div class="lede">{latest.get("bills_pct"):.1f} percent had problems paying family medical bills. {latest.get("debt_pct"):.1f} percent were paying medical bills over time.</div>
    <div class="scroll">{_pct_rows_table(bills.get("rows"), "Share")}</div>
    <div class="srcline"><b>Source:</b> CHIA 2025 MHIS table E.1-5 (SRC-633-02). Ranks are Pioneer calculations (derived).</div>
  </section>
<section id="view-oopshare">
    <h2>Out-of-pocket as a share of income</h2>
    <div class="lede">MHIS does not publish an average dollar out-of-pocket cost. It publishes the share of family income spent out of pocket. {dist.get("five_or_more_pct"):.1f} percent of residents were in families that spent 5 percent or more of income (derived, SRC-633-02).</div>
    <div class="scroll">{_pct_rows_table(dist.get("rows"), "Share")}</div>
    <div class="srcline"><b>Source:</b> CHIA 2025 MHIS table F.1-1 (SRC-633-02). The 5 percent or more figure adds the published 5-to-10 and 10-or-more buckets (derived).</div>
  </section>
<section id="view-coverage">
    <h2>Coverage and high-deductible plans</h2>
    <div class="lede">{cov.get("insured_pct"):.1f} percent of residents were insured at the time of the survey. {cov.get("hdhp_privately_insured_pct"):.1f} percent of the privately insured had a high-deductible plan (at least $1,400 single or $2,800 family). Among residents with a behavioral health visit, {cov.get("bh_visit_all_oop_pct"):.1f} percent paid entirely out of pocket.</div>
    <div class="srcline"><b>Source:</b> CHIA 2025 MHIS tables B.1-1, B.3-1, and G.2-1 (SRC-633-02).</div>
  </section>
"""
    if app["id"] != "DL-11":
        return ""
    sec = ((ledger.get("derived") or {}).get("secondary") or {})
    charity = sec.get("charity_care") or {}
    legis = sec.get("legislative") or {}
    if not charity and not legis:
        return ""
    fig_t = n_fig + (2 if has_trend else 1) + 1
    us = charity.get("us") or {}
    split = charity.get("hospital_split_2023") or {}
    b340 = split.get("340b") or {}
    both = split.get("other") or {}
    split_txt = ""
    if b340.get("share_pct") is not None and both.get("share_pct") is not None:
        split_txt = (
            f" Participating 340B hospitals (matched on CCN) filed at "
            f"{b340['share_pct']} percent of total costs; other hospitals "
            f"filed at {both['share_pct']} percent."
        )
    charity_lede = (
        f"Charity-care cost was {us.get('v')} percent of hospital total costs "
        f"on the 2023 CMS Provider Cost Report PUF, the public Worksheet S-10 "
        f"file behind RAND TL-303.{split_txt} The ranking is the state share, "
        f"not dollars."
    )
    mapped = legis.get("mapped_contracts")
    unmapped = legis.get("unmapped_contracts")
    ndist = legis.get("districts_with_pharmacies")
    npharm = legis.get("unique_pharmacies")
    legis_lede = (
        f"{commify(npharm) if npharm is not None else ''} unique active "
        f"contract pharmacies are assigned to {commify(ndist) if ndist is not None else ''} "
        f"state house districts (2024 boundaries) by Census ZCTA land-area majority. "
        f"{commify(unmapped) if unmapped is not None else ''} contract rows "
        f"had a ZIP with no 2020 ZCTA in that file. A ZIP can cross district "
        f"lines. Filter the table by state."
    ).strip()
    return f"""
<section id="view-charity">
    <h2>Hospital charity care</h2>
    <div class="lede">{esc(charity_lede)}</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure {fig_t}</span>
        <span class="ex-t">Charity-care share since 2011</span></div>
      <div class="plot"><canvas id="chCharityTrend"></canvas></div>
      <div class="srcline"><b>Source:</b> CMS Hospital Provider Cost Report PUF (SRC-611-02). <b>Unit:</b> percent of total costs.</div>
    </div>
    <div class="findrow">
      <label class="sel-lab" for="charityFind">Find a state</label>
      <input id="charityFind" type="search" placeholder="Type a name" autocomplete="off">
      <span id="charityCount" class="findcount"></span>
    </div>
    <div class="scroll">
      <table id="tblCharity">
        <thead><tr><th>State</th><th class="n">Share</th><th class="n">Charity-care cost</th><th class="n">Total costs</th><th class="n">Rank</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="srcline"><b>Source:</b> SRC-611-02. Ranks are Pioneer calculations (derived).</div>
  </section>
<section id="view-districts">
    <h2>Legislative mapping</h2>
    <div class="lede">{esc(legis_lede)}</div>
    <div class="findrow">
      <label class="sel-lab" for="distState">State</label>
      <select id="distState"></select>
      <label class="sel-lab" for="distFind">Find a district</label>
      <input id="distFind" type="search" placeholder="Type a district" autocomplete="off">
      <span id="distCount" class="findcount"></span>
    </div>
    <div class="scroll">
      <table id="tblDistricts">
        <thead><tr><th>District</th><th>State</th><th class="n">Pharmacies</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="srcline"><b>Source:</b> OPAIS daily export (SRC-611-01) and Census 2024 SLDL-to-ZCTA (SRC-611-03). Pioneer Institute one-page fact sheets remain on <a href="https://pioneerinstitute.org/340b-abuse/340b-state-one-page-fact-sheets/" target="_blank" rel="noopener">pioneerinstitute.org</a>.</div>
  </section>
"""


def extra_tool_js(app, ledger):
    if app["id"] != "DL-11":
        return ""
    return r"""
  (function(){
    var sec=(DL&&DL.derived&&DL.derived.secondary)||{};
    var charity=sec.charity_care||{};
    var legis=sec.legislative||{};
    function money(v){
      if(v==null||v==='') return '';
      var n=Number(v), sign=n<0?'\u2212':'', a=Math.abs(n);
      if(a>=1e12) return sign+'$'+(a/1e12).toFixed(2)+' trillion';
      if(a>=1e9) return sign+'$'+(a/1e9).toFixed(2)+' billion';
      if(a>=1e6) return sign+'$'+(a/1e6).toFixed(2)+' million';
      return sign+'$'+Math.round(a).toLocaleString();
    }
    var crows=charity.rows||[];
    var ctr=charity.trend||{};
    var tel=document.getElementById('chCharityTrend');
    if(tel&&window.Chart&&(ctr.US||ctr.MA||ctr.FL)){
      var series=[{key:'US',label:'United States',color:INK},{key:'MA',label:'Massachusetts',color:GOLD},{key:'FL',label:'Florida',color:RUST}];
      var years={};
      series.forEach(function(s){ (ctr[s.key]||[]).forEach(function(p){ years[p.y]=1; }); });
      var labels=Object.keys(years).map(Number).sort(function(a,b){return a-b;});
      var tsets=series.map(function(s){
        var by={}; (ctr[s.key]||[]).forEach(function(p){ by[p.y]=p.v; });
        return {label:s.label,data:labels.map(function(y){return by[y];}),borderColor:s.color,backgroundColor:'transparent',spanGaps:false};
      });
      new Chart(tel,{type:'line',
        data:{labels:labels,datasets:tsets},
        options:{plugins:{legend:{display:true},
          tooltip:{callbacks:{label:function(c){return ' '+c.dataset.label+': '+Number(c.parsed.y).toFixed(2)+'%';}}}},
          scales:{y:fitScale({ticks:{callback:function(v){return v+'%';}},title:{display:true,text:'percent of total costs'}}, seriesValues(tsets))}},
        plugins:[dataLabels(function(v){return Number(v).toFixed(1)+'%';},'end')]
      });
    }
    var ctb=document.querySelector('#tblCharity tbody');
    if(ctb){
      ctb.innerHTML=crows.map(function(r){
        return '<tr data-q="'+((r.name||'')+' '+(r.st||'')).toLowerCase()+'"><td class="m">'+(r.name||'')+'</td><td class="n">'+(r.v==null?'':Number(r.v).toFixed(2)+'%')+'</td><td class="n">'+money(r.charity)+'</td><td class="n">'+money(r.costs)+'</td><td class="n">'+(r.rank||'')+'</td></tr>';
      }).join('');
      var cf=document.getElementById('charityFind');
      var cc=document.getElementById('charityCount');
      function applyC(){
        var q=(cf&&cf.value||'').toLowerCase();
        var shown=0, n=0;
        [].slice.call(ctb.querySelectorAll('tr')).forEach(function(tr){
          var ok=!q || (tr.getAttribute('data-q')||'').indexOf(q)>=0;
          tr.hidden=!ok; n++; if(ok) shown++;
        });
        if(cc) cc.textContent=q? (shown+' of '+n) : (n+' rows');
      }
      if(cf) cf.addEventListener('input', applyC);
      applyC();
    }
    var drows=legis.rows||[];
    var dtb=document.querySelector('#tblDistricts tbody');
    var sel=document.getElementById('distState');
    if(dtb&&sel){
      var names={};
      ((DL&&DL.rows)||[]).forEach(function(r){ if(r.st) names[r.st]=r.name||r.st; });
      var keys=Object.keys(drows.reduce(function(acc,r){ if(r.st) acc[r.st]=1; return acc; },{})).sort(function(a,b){
        return String(names[a]||a).localeCompare(names[b]||b);
      });
      sel.innerHTML=keys.map(function(s){
        return '<option value="'+s+'"'+(s==='MA'?' selected':'')+'>'+(names[s]||s)+'</option>';
      }).join('');
      function applyD(){
        var st=sel.value||'MA';
        var q=(document.getElementById('distFind')&&document.getElementById('distFind').value||'').toLowerCase();
        var shown=0, n=0;
        dtb.innerHTML=drows.filter(function(r){ return r.st===st; }).map(function(r){
          n++;
          var key=((r.name||'')+' '+(r.st||'')).toLowerCase();
          var hide=q && key.indexOf(q)<0;
          if(!hide) shown++;
          return '<tr'+(hide?' hidden':'')+' data-q="'+key+'"><td class="m">'+(r.name||r.id||'')+'</td><td>'+(r.st||'')+'</td><td class="n">'+(r.v==null?'':Number(r.v).toLocaleString())+'</td></tr>';
        }).join('');
        var dc=document.getElementById('distCount');
        if(dc) dc.textContent=q? (shown+' of '+n) : (n+' districts');
      }
      sel.addEventListener('change', applyD);
      var df=document.getElementById('distFind');
      if(df) df.addEventListener('input', applyD);
      applyD();
    }
  })();
"""


def page_html(app, ledger, apps=None):
    live = ledger.get("status") == "live"
    title = app["title"]
    slug = app["slug"]
    standfirst = app["q"]
    apps = apps or []
    as_of_label = ledger.get("data_month_label") or "pending"
    revised = ledger.get("page", {}).get("revised", "")
    metric_label = ledger.get("metric_label") or "Figure"
    unit = ledger.get("unit") or ""
    replaces = esc(replaces_list(app, ledger))
    nsrc = len(ledger.get("source_id_map") or {})
    src_word = "source" if nsrc == 1 else "sources"
    voice = voice_for(app, ledger) if app.get("id") not in ("DL-01", "DL-02") else None
    lead = display_lead(voice, ledger) if live else short_place_text(
        ledger.get("lead")
        or (
            "This application is in build. The source register below is the inventory. "
            "Figures will appear here once they are recomputed from those sources."
        ),
        census_place_names(ledger),
    )
    finding_kpis = (voice or {}).get("kpis") or []
    kpis = kpi_html(finding_kpis or ledger.get("kpis") or [])
    cite = (voice or {}).get("cite") or (
        f"Pioneer Institute DataLabs, {title}, {as_of_label and ('data through ' + as_of_label + '. ') or ''}"
        f"Name the source id next to the figure. The vintage in the masthead belongs in the citation."
    )
    find_spec = (voice or {}).get("find") or {"kind": None, "cards": {}, "metric": ""}
    spec = chart_spec(app, ledger) if live else {}
    first_sid = next(iter((ledger.get("source_id_map") or {})), "")
    fig1_src = src_cite(ledger, first_sid) if live else "see the register"
    all_insights = insight_figures(app, ledger) if live else []
    insights = all_insights
    if spec.get("headline_from") == "secondary.public_k12_enrollment":
        insights = [f for f in insights if f.get("id") != "ma-enroll"]
    map_insights = [f for f in insights if f.get("type") == "map" and f.get("rows")]
    insights = [f for f in insights if f.get("type") != "map"]
    map_views = []
    if live and spec.get("geo") == "state" and spec.get("show_map") is not False:
        src_ids = list((ledger.get("source_id_map") or {}))
        mode = spec.get("map_mode") or "hex"
        if app["id"] == "DL-07":
            map_views.append({
                "id": "naep",
                "tab": "Grade 4 reading",
                "title": "NAEP grade 4 reading, 2024",
                "lede": spec.get("lede") or "",
                "src": src_cite(ledger, "SRC-607-05"),
                "unit": "scale score",
                "format": "number",
                "primary": True,
                "rows": naep_score_rows(ledger),
                "mode": "hex",
            })
        else:
            map_views.append({
                "id": "latest",
                "tab": spec.get("label") or "Latest",
                "title": spec.get("title") or spec.get("label") or "",
                "lede": spec.get("lede") or "",
                "src": src_cite(ledger, src_ids[0] if src_ids else ""),
                "unit": spec.get("unit") or unit or "",
                "format": spec.get("format") or "number",
                "primary": True,
                "mode": mode,
            })
    has_trend = bool(spec.get("has_trend"))
    later_insights = []
    if has_trend:
        later_insights = insights[1:]
        insights = insights[:1]
    else:
        later_insights = insights[2:]
        insights = insights[:2]
    find_noun = (spec.get("geo") or "name").replace("_", " ")
    jump = ""
    compare_h2 = spec.get("compare_title") or spec.get("title") or "Compared"
    table_h2 = spec.get("table_noun") or "Every row"
    chips = starters_html(app["id"]) if live else ""
    if live:
        jump_links = ['<a href="#answer">The finding</a>']
        if spec.get("hero_finder"):
            noun = "hospital" if app["id"] == "DL-10" else "city or town"
            jump_links.append('<a href="#view-proof">Look up a ' + esc(noun) + "</a>")
        if app["id"] in TOWN_TOOLS:
            jump_links.append('<a href="#view-town-map">Town map</a>')
        if app["id"] in HIST_TOOLS:
            jump_links.append('<a href="#view-hist">Distribution</a>')
        has_compare = (
            spec.get("show_map") is not False
            and (
                spec.get("geo") == "state"
                or app["id"] in TOWN_TOOLS
                or app["id"] in HIST_TOOLS
                or (spec.get("compare") or "") in ("dots", "map", "town", "hist")
            )
        )
        if has_compare:
            jump_links.append('<a href="#view-rank">' + esc(compare_h2) + "</a>")
        if has_trend:
            jump_links.append('<a href="#view-trend">The trend</a>')
        if spec.get("show_map") is not False:
            if spec.get("geo") == "state":
                jump_links.append('<a href="#view-table">Table</a>')
            else:
                jump_links.append('<a href="#view-table">' + esc(table_h2) + "</a>")
        if app["id"] == "DL-11":
            jump_links.append('<a href="#view-charity">Charity care</a>')
            jump_links.append('<a href="#view-districts">Legislative mapping</a>')
        if app["id"] == "DL-33":
            jump_links.append('<a href="#view-afford">Affordability</a>')
            jump_links.append('<a href="#view-unmet">Unmet need</a>')
            jump_links.append('<a href="#view-debt">Medical bills</a>')
            jump_links.append('<a href="#view-oopshare">Share of income</a>')
            jump_links.append('<a href="#view-coverage">Coverage</a>')
        for fig in insights:
            fid = fig.get("id")
            if not fid:
                continue
            label = JUMP_SHORT.get(fid) or (fig.get("title") or fid).strip()
            if len(label) > 36:
                label = label[:34] + "\u2026"
            jump_links.append(
                '<a href="#insight-' + esc(fid) + '">' + esc(label) + "</a>"
            )
        for fig in later_insights:
            fid = fig.get("id")
            if not fid:
                continue
            label = JUMP_SHORT.get(fid) or (fig.get("title") or fid).strip()
            if len(label) > 36:
                label = label[:34] + "\u2026"
            jump_links.append(
                '<a href="#view-' + esc(fid) + '">' + esc(label) + "</a>"
            )
        jump = (
            '<nav class="jump" aria-label="On this page">'
            '<details class="jump-fold">'
            "<summary>On this page</summary>"
            '<div class="jump-links">'
            + "".join(jump_links)
            + "</div></details></nav>\n"
        )
    latest_section = ""
    n_fig = len(insights) if live else 0
    trend_block = ""
    if live and has_trend:
        trend_n = 1 if spec.get("show_map") is False else 2
        trend_block = f"""
<section id="view-trend">
    <h2>{esc(spec.get("trend_title") or "The trend")}</h2>
{('    <div class="lede">' + esc(spec["trend_lede"]) + "</div>\n") if spec.get("trend_lede") else ""}    <div class="findrow" id="trendPick" hidden>
      <label class="sel-lab" for="trendSel">Add a state</label>
      <select id="trendSel"></select>
    </div>
    <div class="series-win" id="trendWindow" hidden>
      <span class="sel-lab">Show</span>
      <button type="button" data-win="recent" class="on">Last 36 months</button>
      <button type="button" data-win="full">Full series</button>
    </div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure {trend_n}</span>
        <span class="ex-t" id="trendTitle">{esc(spec.get("trend_title") or "Trend")}</span></div>
      <div class="plot"><canvas id="chTrend"></canvas></div>
      <div class="srcline"><b>Source:</b> {esc(fig1_src)}. <b>Unit:</b> {esc(spec.get("trend_unit") or unit or "see the register")}. <b>Calculation:</b> Pioneer Institute.</div>
    </div>
  </section>
"""
    table_cols = spec.get("table_columns") or [
        {"key": "name", "label": spec.get("col_name") or "Name", "cls": "m"},
        {"key": "v", "label": table_value_label(spec.get("unit") or unit, spec.get("label") or metric_label), "align": "n"},
        {"key": "rank", "label": "Rank", "align": "n"},
        {"key": "yoy_pct", "label": "YoY", "align": "n", "kind": "yoy"},
    ]
    th_html = "".join(
        (
            '<th'
            + (' class="n"' if c.get("align") == "n" else "")
            + ' data-key="'
            + esc(c.get("key") or "")
            + '" scope="col"><button type="button" class="th-sort">'
            + esc(c.get("label") or "")
            + "</button></th>"
        )
        for c in table_cols
    )
    table_lede = esc(spec.get("table_lede") or "Type a name to jump to a row.")
    table_note = spec.get("table_note") or (
        "Ranks and year-over-year changes are Pioneer calculations (derived)."
    )
    table_body = f"""    <div class="lede">{table_lede}</div>
    <div class="findrow">
      <label class="sel-lab" for="tblFind">Find a {esc(find_noun)}</label>
      <input id="tblFind" type="search" placeholder="Type a name" autocomplete="off">
      <span id="tblCount" class="findcount"></span>
    </div>
    <div id="findCard" class="findcard" hidden></div>
    <div class="scroll">
      <table id="tblStates">
        <thead><tr>{th_html}</tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="srcline"><b>Source:</b> see the register. {esc(table_note)}</div>
"""
    map_tabs = ""
    if spec.get("geo") == "state":
        buttons = []
        for i, view in enumerate(map_views):
            on = " is-on" if i == 0 else ""
            buttons.append(
                f'<button type="button" class="map-tab{on}" data-view="{i}">'
                + esc(view.get("tab") or view.get("title") or "View")
                + "</button>"
            )
        buttons.append(
            '<button type="button" class="map-tab" data-pane="table">Table</button>'
        )
        map_tabs = (
            '    <div class="map-tabs" id="mapTabs" role="tablist" '
            'aria-label="Map view">' + "".join(buttons) + "</div>\n"
        )
    map_lede = spec.get("lede") or ""
    compare = spec.get("compare") or ("map" if spec.get("geo") == "state" else "dots")
    finder_block = ""
    if live and spec.get("hero_finder"):
        noun = "hospital" if app["id"] == "DL-10" else "city or town"
        finder_block = (
            '  <section id="view-proof" class="proof-find">\n'
            f"    <h2>Look up a {esc(noun)}</h2>\n"
            '    <div class="findrow">\n'
            f'      <label class="sel-lab" for="proofFind">Type a {esc(noun)}</label>\n'
            '      <input id="proofFind" type="search" placeholder="Type a name" autocomplete="off">\n'
            "    </div>\n"
            '    <div id="proofCard" class="findcard"></div>\n'
            "  </section>\n"
        )
    if live:
        if spec.get("geo") == "state" and spec.get("show_map") is not False:
            mode = (map_views[0].get("mode") if map_views else spec.get("map_mode")) or "hex"
            fig1_title = (
                (map_views[0].get("title") if map_views else None)
                or spec.get("title")
                or metric_label
            )
            fig1_unit = (
                (map_views[0].get("unit") if map_views else None)
                or unit
                or "see the register"
            )
            rank_inner = (
                f"{map_tabs}"
                + (
                    f'    <div class="lede" id="mapLede">{esc(map_lede)}</div>\n'
                    if map_lede
                    else '    <div class="lede" id="mapLede" hidden></div>\n'
                )
                + REGION_BAR
                + EXPLORE_BAR
                + '    <div id="mapPane">\n'
                + '    <div class="exhibit">\n'
                + '      <div class="ex-head"><span class="ex-n">Figure 1</span>\n'
                + f'        <span class="ex-t" id="rankTitle">{esc(fig1_title)}</span></div>\n'
                + f'      <div class="plot plot-map" id="chRank" data-mode="{esc(mode)}"></div>\n'
                + '      <div class="note" id="mapNote" hidden></div>\n'
                + '      <div class="srcline" id="mapSrc"><b>Source:</b> '
                + esc(fig1_src)
                + '. <b>Calculation:</b> Pioneer Institute (ranks only). <b>Unit:</b> '
                + esc(fig1_unit)
                + ".</div>\n"
                + "    </div>\n"
                + "    </div>\n"
                + '    <div id="view-table" hidden>\n'
                + table_body
                + "    </div>\n"
            )
        elif compare == "town":
            rank_inner = (
                (
                    f'    <div class="lede" id="mapLede">{esc(map_lede)}</div>\n'
                    if map_lede
                    else '    <div class="lede" id="mapLede" hidden></div>\n'
                )
                + '    <div class="exhibit" id="fig1">\n'
                + '      <div class="ex-head"><span class="ex-n">Figure 1</span>\n'
                + f'        <span class="ex-t" id="rankTitle">{esc(spec.get("title") or metric_label)}</span></div>\n'
                + '      <div class="plot"><canvas id="chRank"></canvas></div>\n'
                + '      <div class="note" id="mapNote" hidden></div>\n'
                + '      <div class="srcline" id="mapSrc"><b>Source:</b> '
                + esc(fig1_src)
                + '. <b>Calculation:</b> Pioneer Institute (ranks only). <b>Unit:</b> '
                + esc(unit or "see the register")
                + ".</div>\n"
                + "    </div>\n"
            )
        elif compare in ("hist", "dots", "finder"):
            rank_inner = (
                (
                    f'    <div class="lede" id="mapLede">{esc(map_lede)}</div>\n'
                    if map_lede
                    else '    <div class="lede" id="mapLede" hidden></div>\n'
                )
                + '    <div class="exhibit" id="fig1">\n'
                + '      <div class="ex-head"><span class="ex-n">Figure 1</span>\n'
                + f'        <span class="ex-t" id="rankTitle">{esc(spec.get("title") or metric_label)}</span></div>\n'
                + '      <div class="plot"><canvas id="chRank"></canvas></div>\n'
                + '      <div class="note" id="mapNote" hidden></div>\n'
                + '      <div class="srcline" id="mapSrc"><b>Source:</b> '
                + esc(fig1_src)
                + '. <b>Calculation:</b> Pioneer Institute (ranks only). <b>Unit:</b> '
                + esc(unit or "see the register")
                + ".</div>\n"
                + "    </div>\n"
            )
        else:
            rank_inner = ""
        answer_block = answer_html(
            (voice or {}).get("answer"),
            kpis,
            slug,
            (voice or {}).get("vintages") or mixed_vintage_lines(ledger),
            (voice or {}).get("answers"),
        )
        if not answer_block:
            answer_block = f"""
<section id="answer" class="answer-block">
    <p class="lede lead-graf">
<!-- DATA:BEGIN {slug}-lead -->
{lead}
<!-- DATA:END {slug}-lead -->
    </p>
    <div class="strip metrics">
<!-- DATA:BEGIN {slug}-kpis -->
{kpis}
<!-- DATA:END {slug}-kpis -->
    </div>
  </section>
"""
        rank_section = (
            f"""
  <section id="view-rank">
    <h2>{esc(compare_h2)}</h2>
{rank_inner}  </section>
"""
            if rank_inner
            else ""
        )
        has_map = bool(rank_inner)
        insight_start = (2 if has_map else 1) + (1 if has_trend else 0)
        later_start = insight_start + len(insights)
        town_map_n = later_start + len(later_insights)
        if live and compare == "town":
            rank_section += f"""
  <section id="view-town-map">
    <h2>Every city and town</h2>
    <div class="lede">The map is a later view. Figure 1 is the selected town versus its nearest Census peer and Boston.</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure {town_map_n}</span>
        <span class="ex-t">Massachusetts cities and towns</span></div>
      <div class="plot plot-map" id="chTownMap" data-mode="town"></div>
      <div class="srcline"><b>Source:</b> {esc(fig1_src)}. <b>Unit:</b> {esc(unit or "people")}.</div>
    </div>
  </section>
"""
            jump_links_town = True
        else:
            jump_links_town = False
        if live and compare == "hist":
            rank_section += f"""
  <section id="view-hist">
    <h2>How pay is distributed</h2>
    <div class="lede">Each bar is a count of members in a pay band. Figure 1 is the selected member versus the House and Senate medians.</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure {town_map_n}</span>
        <span class="ex-t">Pay across the file</span></div>
      <div class="plot"><canvas id="chHist"></canvas></div>
      <div class="srcline"><b>Source:</b> {esc(fig1_src)}. <b>Unit:</b> {esc(unit or "dollars")}.</div>
    </div>
  </section>
"""
        latest_section = (
            answer_block
            + finder_block
            + rank_section
            + trend_block
            + insight_html(insights, start=insight_start)
            + later_view_html(later_insights, later_start, len(insights))
            + chips
        )
    else:
        dash_block = dashboards_html(app)
        jump = (
            '<nav class="jump" aria-label="On this page">'
            '<a href="#dashboards">Dashboards</a>'
            '<a href="#sources">Sources</a>'
            "</nav>\n"
            if dash_block
            else jump
        )
        latest_section = f"""
<section id="finding" style="margin-top:28px">
  <h2>What this application will cover</h2>
  <p class="lede">{esc(app['scope'])}</p>
  <p class="body-p">{esc(app['exclusions'])}</p>
</section>
{dash_block}"""
    table_section = ""
    if live and spec.get("geo") != "state":
        table_section = f"""
<section id="view-table">
    <h2>{esc(spec.get("table_noun") or "Every row")}</h2>
{table_body}  </section>
"""
    elif live:
        table_section = ""
    extra_section = extra_tool_sections(app, ledger, n_fig, has_trend) if live else ""
    related_section = related_html(app, apps) if live else ""
    js = ""
    if live:
        js = """
<script>
/* DATA:BEGIN SLUG-data */
const DL=null;
/* DATA:END SLUG-data */
const CHART=CHART_JSON;
const INSIGHTS=INSIGHTS_JSON;
const MAP_VIEWS=MAP_VIEWS_JSON;
const FIND=FIND_JSON;

(function(){
  var q=new URLSearchParams(location.search);
  if(q.get('embed')==='1'||q.get('embed')==='true') document.body.classList.add('embed');
  var GOLD='#CCB26D', RUST='#C45C26', BLUE='#293C5C', NAVY='#293C5C', INK='#1A1A1A', GREY='#58575A', STEEL='#A9B8C8';
  function roleColor(k, extra){
    if(window.dlRoleColor) return window.dlRoleColor(k, {extra: extra||pickedSt||compareSt});
    var key=String(k||'');
    if(key==='US' || key==='United States') return INK;
    if(key==='MA' || key==='Massachusetts') return GOLD;
    if(key==='FL' || key==='Florida') return RUST;
    if(extra && (key===extra || key===(pretty&&pretty[extra]))) return BLUE;
    return STEEL;
  }
  function parseHash(){
    var raw=(location.hash||'').replace(/^#/,'');
    var view='', st='';
    if(!raw) return {view:view, st:st};
    raw.split('&').forEach(function(part){
      if(!part) return;
      try { part=decodeURIComponent(part); } catch(err) {}
      if(part.indexOf('st=')===0) st=part.slice(3);
      else if(part.indexOf('view-')===0) view=part.slice(5);
      else if(part.indexOf('view=')===0) view=part.slice(5);
      else view=part.replace(/^view-/,'');
    });
    if(view==='latest') view='rank';
    return {view:view, st:st};
  }
  function applyHash(){
    var h=parseHash();
    if(!h.view) return;
    var id='view-'+h.view;
    var el=document.getElementById(id)||document.getElementById(h.view);
    if(el) el.scrollIntoView({behavior:'smooth',block:'start'});
  }
  window.addEventListener('hashchange', applyHash);
  window.addEventListener('load', function(){
    applyHash();
    if(window.dlHighlightExhibit) window.dlHighlightExhibit(location.hash);
  });
  var fmt=CHART.format||'number';
  var unit=CHART.unit||'';
  var axisUnit=CHART.axis_unit||unit;
  function hlList(){
    if(CHART.highlights && CHART.highlights.length) return CHART.highlights;
    if(CHART.geo==='state') return ['MA'];
    if(CHART.highlight) return [CHART.highlight];
    return [];
  }
  function isMA(r){ return r.st==='MA' || r.name==='Massachusetts'; }
  function isFL(r){ return r.st==='FL' || r.name==='Florida'; }
  function isHL(r){
    var list=hlList();
    for(var i=0;i<list.length;i++){ if(r.name===list[i] || r.st===list[i]) return true; }
    return false;
  }
  function hlColor(r){
    if(isMA(r)) return GOLD;
    if(isFL(r)) return RUST;
    if(compareSt && r.st===compareSt && r.st!=='MA' && r.st!=='FL') return BLUE;
    if(r.name==='Boston' && CHART.geo==='state') return BLUE;
    return STEEL;
  }
  function hlClass(r){
    if(isMA(r)) return 'hl-ma';
    if(isFL(r) || (compareSt && r.st===compareSt && r.st!=='MA')) return 'hl-fl';
    return '';
  }
  function fmtVal(v, short){
    if(v==null||v==='') return '';
    var n=Number(v), sign=n<0?'\u2212':'', a=Math.abs(n);
    if(fmt==='usd'||fmt==='usd_millions'){
      var d=fmt==='usd_millions'?a*1e6:a;
      if(d>=1e12) return sign+'$'+(d/1e12).toFixed(2)+(short?'T':' trillion');
      if(d>=1e9) return sign+'$'+(d/1e9).toFixed(2)+(short?'B':' billion');
      if(d>=1e6) return sign+'$'+(d/1e6).toFixed(2)+(short?'M':' million');
      return sign+'$'+Math.round(d).toLocaleString();
    }
    if(fmt==='percent') return n.toFixed(1)+'%';
    if(fmt==='stars') return n+' star'+(n===1?'':'s');
    if(a>=1000) return sign+Math.round(a).toLocaleString();
    if(Math.abs(n-Math.round(n))<1e-6) return sign+String(Math.round(a));
    return sign+a.toLocaleString(undefined,{maximumFractionDigits:1});
  }
  function seriesValues(series){
    var out=[];
    (series||[]).forEach(function(s){
      (s&&s.data?s.data:[]).forEach(function(v){
        if(v==null||v==='') return;
        if(typeof v==='object' && !Array.isArray(v)){
          if(v.x!=null) out.push(v.x);
          if(v.y!=null) out.push(v.y);
          if(v.v!=null) out.push(v.v);
          return;
        }
        if(Array.isArray(v)){ v.forEach(function(x){ if(x!=null&&x!=='') out.push(x); }); return; }
        out.push(v);
      });
    });
    return out;
  }
  function fitScale(scale, values, extra){
    extra=extra||{};
    delete scale.min;
    delete scale.max;
    if(window.dlApplyScale) return window.dlApplyScale(scale, values, extra);
    scale.beginAtZero=false;
    if(scale.grace==null) scale.grace=extra.grace||'12%';
    return scale;
  }
  function copyFit(dest, src){
    if(!dest||!src) return dest;
    dest.beginAtZero=src.beginAtZero;
    dest.grace=src.grace;
    if(src.min==null) delete dest.min; else dest.min=src.min;
    if(src.max==null) delete dest.max; else dest.max=src.max;
    return dest;
  }
  function rowLabel(r){
    if(CHART.geo==='state' && r.st && String(r.st).length===2) return r.st;
    var s=r.name||r.st||'';
    return s.length>28?s.slice(0,26)+'\u2026':s;
  }
  function dataLabels(fmt, mode){ return window.dlChartLabels(fmt, mode); }
  var rows=(DL&&DL.rows)||[];
  var REGIONS={
    all:null,
    northeast:['CT','ME','MA','NH','RI','VT','NJ','NY','PA'],
    midwest:['IL','IN','MI','OH','WI','IA','KS','MN','MO','NE','ND','SD'],
    south:['DE','FL','GA','MD','NC','SC','VA','DC','WV','AL','KY','MS','TN','AR','LA','OK','TX'],
    west:['AZ','CO','ID','MT','NV','NM','UT','WY','AK','CA','HI','OR','WA']
  };
  var REGION_NAMES={all:'all states',northeast:'the Northeast',midwest:'the Midwest',south:'the South',west:'the West'};
  var region='all';
  var band='all';
  var selectedSt='';
  var compareSt='FL';
  var ANSWERS=(DL&&DL.answers)||{};
  var hasLens=!!(ANSWERS.US && ANSWERS.US.value);
  function fillPlaceStrip(){
    var el=document.getElementById('placeStrip');
    if(!el) return;
    function part(cls, k, v, r){
      if(v==null||v==='') return '';
      var lab=k;
      if(r && String(r)!==k) lab=k+', '+String(r).replace(/</g,'');
      return '<span class="ps '+cls+'"><span class="ps-k">'+lab+'</span> <span class="ps-v">'+String(v).replace(/</g,'')+'</span></span>';
    }
    var parts=[];
    function push(cls, k, v, r){
      var html=part(cls, k, v, r);
      if(html) parts.push(html);
    }
    var kind=(FIND&&FIND.kind)||'';
    if(kind==='town'){
      var bos=(FIND.compare&&FIND.compare.boston)||bostonRow();
      var q=(document.getElementById('proofFind')&&document.getElementById('proofFind').value)||(FIND&&FIND.default_q)||'';
      var card=typeof findCardFor==='function'?findCardFor(q):null;
      var row=card?rowByName(card.name):rowByName(q);
      var acs=((FIND.compare&&FIND.compare.acs_peers)||{})[normFind((row&&row.name)||q)];
      push('ps-ma','Boston', bos&&(bos.value||fmtVal(bos.v)), bos&&bos.name);
      push('ps-us','Selected', (card&&card.value)||(row&&fmtVal(row.v)), (row&&row.name)||(card&&card.name)||'A town');
      push('ps-fl','ACS peer', acs&&(acs.value||fmtVal(acs.v)), acs&&acs.name);
    } else if(kind==='legislator'){
      var cmp=FIND.compare||{};
      var q2=(document.getElementById('proofFind')&&document.getElementById('proofFind').value)||(document.getElementById('tblFind')&&document.getElementById('tblFind').value)||(FIND&&FIND.default_q)||'';
      var card2=typeof findCardFor==='function'?findCardFor(q2):null;
      push('ps-ma','House median', cmp.house_median&&cmp.house_median.value);
      push('ps-us','Senate median', cmp.senate_median&&cmp.senate_median.value);
      push('ps-fl','Selected', card2&&card2.value, card2&&card2.name);
    } else if(kind==='hospital'){
      var cmpH=FIND.compare||{};
      var qH=(document.getElementById('proofFind')&&document.getElementById('proofFind').value)||(FIND&&FIND.default_q)||'';
      var cardH=typeof findCardFor==='function'?findCardFor(qH):null;
      push('ps-ma','Selected', cardH&&(cardH.srp!=null?String(cardH.srp):cardH.value), cardH&&cardH.name);
      push('ps-us','Statewide commercial average', cmpH.statewide_srp&&cmpH.statewide_srp.value);
    } else if(hasLens){
      var ma=ANSWERS.MA||{};
      var fl=ANSWERS.FL||{};
      push('ps-ma', 'Massachusetts', ma.value);
      push('ps-fl', 'Florida', fl.value);
    }
    if(!parts.length){
      el.innerHTML='';
      el.hidden=true;
      return;
    }
    el.innerHTML=parts.join('<span class="ps-dot" aria-hidden="true"> · </span>');
    el.hidden=false;
  }
  function answerKey(st){
    if(!st || st==='US') return 'US';
    return String(st).toUpperCase();
  }
  function applyLens(st){
    if(!hasLens) return;
    var a=ANSWERS[answerKey(st)]||ANSWERS.US;
    if(!a || !a.value) return;
    var h2=document.getElementById('answerQ');
    var num=document.getElementById('answerNum');
    var ctx=document.getElementById('answerCtx');
    var meta=document.getElementById('answerMeta');
    var cite=document.querySelector('#answer .cite-copy');
    if(h2) h2.textContent=a.q||'';
    if(num) num.textContent=a.value||'';
    if(ctx){ ctx.textContent=a.context||''; ctx.hidden=!a.context; }
    if(meta){
      var bits=[a.geo,a.vintage,a.src_id].filter(Boolean);
      meta.textContent=bits.join(' \\u00b7 ');
    }
    if(cite && a.cite) cite.setAttribute('data-cite', a.cite);
    fillPlaceStrip();
    var sel=document.getElementById('lensSel');
    if(sel){
      var key=answerKey(st);
      if(sel.querySelector('option[value="'+key+'"]')) sel.value=key;
      else sel.value='US';
    }
  }
  function writeLensHash(st){
    var h=parseHash();
    var parts=[];
    if(h.view) parts.push(h.view.indexOf('view-')===0?h.view:('view-'+h.view));
    var key=answerKey(st);
    if(key && key!=='US') parts.push('st='+key);
    var next=parts.length?('#'+parts.join('&')):'';
    if(location.hash!==next) history.replaceState(null,'',location.pathname+location.search+next);
  }
  function setLens(st, redraw){
    selectedSt=(!st || st==='US')?'':String(st).toUpperCase();
    applyLens(selectedSt||'US');
    writeLensHash(selectedSt||'US');
    if(redraw!==false && typeof drawRank==='function') drawRank();
    if(typeof fillTableBody==='function') fillTableBody();
    if(typeof applyFind==='function') applyFind();
  }
  var mapView=0;
  var rankChart=null;
  var chartRows=[];
  var applyFind=function(){};
  var writeQuery=function(){};
  var fillTableBody=function(){};
  function usFigure(){
    if(CHART.us!=null && CHART.us!=='') return Number(CHART.us);
    var u=DL && DL.latest && DL.latest.us;
    if(u && typeof u==='object' && u.v!=null) return Number(u.v);
    if(typeof u==='number') return u;
    return null;
  }
  var usVal=usFigure();
  var usCompare=!!CHART.us_compare;
  if(usVal!=null && isFinite(usVal) && CHART.us_compare==null){
    var _vals=rows.map(function(r){ return Number(r.v); }).filter(isFinite);
    usCompare=!!(_vals.length && usVal>=Math.min.apply(null,_vals) && usVal<=Math.max.apply(null,_vals));
  }
  function regionList(){
    return REGIONS[region]||null;
  }
  function currentMapView(){ return (MAP_VIEWS||[])[mapView]||{primary:true}; }
  function mapBaseRows(){
    var view=currentMapView();
    return (view.rows && view.rows.length) ? view.rows : rows;
  }
  function bandStates(){
    if(CHART.geo!=='state' || band==='all') return null;
    var usable=rows.filter(function(r){ return r && r.st && r.v!=null && r.v!==''; });
    if(band==='above' && usCompare && usVal!=null) return usable.filter(function(r){ return Number(r.v)>usVal; }).map(function(r){ return r.st; });
    if(band==='below' && usCompare && usVal!=null) return usable.filter(function(r){ return Number(r.v)<usVal; }).map(function(r){ return r.st; });
    var ranked=usable.slice().sort(function(a,b){
      var ra=a.rank!=null?Number(a.rank):999, rb=b.rank!=null?Number(b.rank):999;
      if(ra!==rb) return ra-rb;
      return Number(b.v)-Number(a.v);
    });
    if(band==='top10') return ranked.slice(0,10).map(function(r){ return r.st; });
    if(band==='bottom10') return ranked.slice(-10).map(function(r){ return r.st; });
    return null;
  }
  function activeStates(){
    if(CHART.geo!=='state') return null;
    var reg=regionList();
    var bd=bandStates();
    if(!reg && !bd) return null;
    return rows.filter(function(r){
      if(reg && reg.indexOf(r.st)<0) return false;
      if(bd && bd.indexOf(r.st)<0) return false;
      return true;
    }).map(function(r){ return r.st; });
  }
  function mapActiveStates(){
    if(CHART.geo!=='state') return null;
    var view=currentMapView();
    var base=mapBaseRows();
    var reg=regionList();
    if(!reg && band==='all') return null;
    var usable=base.filter(function(r){ return r && r.st && r.v!=null && r.v!==''; });
    var keep=null;
    if(band==='top10' || band==='bottom10'){
      var ranked=usable.slice().sort(function(a,b){
        var ra=a.rank!=null?Number(a.rank):999, rb=b.rank!=null?Number(b.rank):999;
        if(ra!==rb) return ra-rb;
        return Number(b.v)-Number(a.v);
      });
      keep=band==='top10'?ranked.slice(0,10):ranked.slice(-10);
      keep=keep.map(function(r){ return r.st; });
    } else if((band==='above' || band==='below') && usCompare && usVal!=null && view.primary){
      keep=usable.filter(function(r){
        return band==='above' ? Number(r.v)>usVal : Number(r.v)<usVal;
      }).map(function(r){ return r.st; });
    }
    return base.filter(function(r){
      if(reg && reg.indexOf(r.st)<0) return false;
      if(keep && keep.indexOf(r.st)<0) return false;
      return true;
    }).map(function(r){ return r.st; });
  }
  function filteredRows(){
    var list=activeStates();
    if(!list) return rows.slice();
    return rows.filter(function(r){ return list.indexOf(r.st)>=0; });
  }
  function chartRowsFor(){
    var fr=filteredRows();
    if(CHART.geo!=='state'){
      if(CHART.compare==='hist' || CHART.compare==='dots' || CHART.compare==='town') return fr;
      var n=CHART.n_chart||12;
      var cr=fr.slice(0,n);
      hlList().forEach(function(h){
        if(cr.some(function(r){ return r.name===h || r.st===h; })) return;
        for(var hi=0;hi<rows.length;hi++){
          if(rows[hi].name===h || rows[hi].st===h){ cr=cr.concat([rows[hi]]); break; }
        }
      });
      return cr;
    }
    return fr;
  }
  function sizeRankPlot(n){
    var plot=document.querySelector('#view-rank .plot');
    if(!plot || plot.classList.contains('plot-map')) return;
    plot.style.height=Math.max(240, Math.min(420, n*18+40))+'px';
  }
  function rankTitleText(){
    var view=currentMapView();
    if(view && view.title){
      if(CHART.geo==='state' && region!=='all') return view.title+' in '+REGION_NAMES[region];
      return view.title;
    }
    var base=CHART.title||CHART.label||'';
    if(CHART.geo!=='state' || region==='all') return base;
    return (CHART.label||base)+' in '+REGION_NAMES[region];
  }
  function writeMapChrome(){
    var view=currentMapView();
    var ledeEl=document.getElementById('mapLede');
    if(ledeEl){
      var text=view.lede||(view.primary?(CHART.lede||''):'');
      ledeEl.hidden=!text;
      ledeEl.textContent=text;
    }
    var noteEl=document.getElementById('mapNote');
    if(noteEl){
      var note=view.note||'';
      noteEl.hidden=!note;
      noteEl.textContent=note;
    }
    var srcEl=document.getElementById('mapSrc');
    if(srcEl){
      var src=view.src||'see the register';
      var u=view.unit||unit||'see the register';
      srcEl.innerHTML='<b>Source:</b> '+src+'. <b>Calculation:</b> Pioneer Institute (ranks only). <b>Unit:</b> '+u+'.';
    }
  }
  function drawRankMap(){
    var el=document.getElementById('chRank');
    if(!el||!window.dlStateMap) return;
    var view=currentMapView();
    var base=mapBaseRows();
    chartRows=base;
    var titleEl=document.getElementById('rankTitle');
    if(titleEl) titleEl.textContent=rankTitleText();
    writeMapChrome();
    var viewFmt=view.format||fmt;
    window.dlStateMap(el,{
      mode: view.mode || CHART.map_mode || el.getAttribute('data-mode') || 'hex',
      highlightFlorida: true,
      compareSt: compareSt,
      rows:base,
      format:function(v){
        return view.primary?fmtVal(v,true):fmtInsight(viewFmt,v,true);
      },
      extra:function(){ return unit && fmt!=='usd' && fmt!=='usd_millions' && fmt!=='percent' && fmt!=='stars' ? unit : ''; },
      active:mapActiveStates(),
      selected:selectedSt,
      ref: view.primary && usVal!=null && isFinite(usVal) ? {label:'United States',value:usVal,compare:usCompare} : null,
      onSelect:function(r){
        if(hasLens){
          setLens(r.st||'US', true);
          return;
        }
        selectedSt=r.st||'';
        var find=document.getElementById('tblFind');
        if(find) find.value=r.name||r.st||'';
        applyFind();
        setRankPane('table');
        var tr=document.getElementById('row-'+r.st)||document.querySelector('#tblStates tr[data-st="'+r.st+'"]');
        if(tr) tr.scrollIntoView({behavior:'smooth',block:'center'});
      }
    });
  }
  function shortEdge(v){
    if(v==null||v==='') return '';
    var n=Number(v), a=Math.abs(n), sign=n<0?'\u2212':'';
    if(fmt==='usd'||fmt==='usd_millions'){
      var d=fmt==='usd_millions'?a*1e6:a;
      if(d>=1e6) return sign+'$'+Math.round(d/1e6)+'M';
      if(d>=1000) return sign+'$'+Math.round(d/1000)+'k';
      return sign+'$'+Math.round(d);
    }
    if(fmt==='percent') return Math.round(n)+'%';
    return fmtVal(v,true);
  }
  function drawHist(canvasId){
    var el=document.getElementById(canvasId||'chRank');
    if(!el||!window.Chart) return;
    var vals=rows.map(function(r){return Number(r.v);}).filter(isFinite);
    if(!vals.length) return;
    var lo=Math.min.apply(null,vals), hi=Math.max.apply(null,vals);
    var nbin=10;
    var width=hi===lo?1:(hi-lo)/nbin;
    var counts=Array(nbin).fill(0);
    vals.forEach(function(v){
      var i=Math.min(Math.floor((v-lo)/width), nbin-1);
      counts[i]++;
    });
    var labels=[];
    for(var i=0;i<nbin;i++){
      var a=lo+i*width;
      labels.push(shortEdge(a));
    }
    var sorted=vals.slice().sort(function(a,b){return a-b;});
    var mid=sorted[Math.floor(sorted.length/2)];
    if(!canvasId || canvasId==='chRank'){
      var titleEl=document.getElementById('rankTitle');
      if(titleEl) titleEl.textContent=CHART.trend_title||CHART.title||'Distribution';
    }
    var plugins=[dataLabels(function(v){return v;}, counts.length>8?'none':'all')];
    var midBin=Math.min(Math.floor((mid-lo)/width), nbin-1);
    if(window.dlRefLineX && mid!=null) plugins.push(window.dlRefLineX(midBin, GOLD, 'median'));
    if(histChart && el.id==='chHist'){ histChart.destroy(); histChart=null; }
    var ch=new Chart(el,{type:'bar',
      data:{labels:labels,datasets:[{data:counts,backgroundColor:STEEL}]},
      options:{indexAxis:'x',responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        layout:{padding:{top:18,right:16}},
        scales:{x:{ticks:{color:GREY,maxRotation:0,minRotation:0,font:{size:10},autoSkip:false}},
          y:fitScale({ticks:{color:GREY},grid:{color:'rgba(34,34,34,.08)'}}, counts)}},
      plugins:plugins});
    if(el.id==='chHist') histChart=ch;
    else rankChart=ch;
  }
  function drawDots(){
    var el=document.getElementById('chRank');
    if(!el||!window.Chart) return;
    chartRows=chartRowsFor();
    var pts=chartRows.map(function(r,i){
      return {x:Number(r.v), y:-(r.rank||i+1), name:r.name, st:r.st, rank:r.rank};
    });
    var xs=pts.map(function(p){return p.x;});
    new Chart(el,{type:'scatter',
      data:{datasets:[{data:pts,backgroundColor:chartRows.map(hlColor),pointRadius:5}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},
          tooltip:{callbacks:{
            title:function(items){var p=items[0]&&items[0].raw; return (p&&p.name)||'';},
            label:function(c){var p=c.raw||{}; return ' '+fmtVal(p.x)+' \u00b7 rank '+(p.rank||'');}
          }}},
        scales:{
          x:fitScale({title:{display:!!axisUnit,text:axisUnit,color:GREY,font:{size:11}},
            ticks:{color:GREY,callback:function(v){return fmtVal(v,true);}},grid:{color:'rgba(34,34,34,.08)'}}, xs),
          y:{reverse:false,ticks:{color:GREY,callback:function(v){return String(Math.abs(v));}},
            title:{display:true,text:'Rank',color:GREY,font:{size:11}},grid:{color:'rgba(34,34,34,.08)'}}
        }}});
  }
  var lookupChart=null;
  var histChart=null;
  function normFind(s){
    return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\\b(city|town|the)\\b/g,' ').replace(/^\\s+|\\s+$/g,'').replace(/\\s+/g,' ');
  }
  function findCardFor(q){
    if(!FIND || !FIND.cards) return null;
    var nq=normFind(q);
    if(FIND.cards[nq]) return FIND.cards[nq];
    var hits=[];
    Object.keys(FIND.cards).forEach(function(k){
      if(k.indexOf(nq)>=0 || nq.indexOf(k)>=0) hits.push(FIND.cards[k]);
    });
    return hits.length===1?hits[0]:null;
  }
  function rowByName(name){
    var nq=normFind(name);
    var hit=null;
    rows.forEach(function(r){
      if(normFind(r.name)===nq) hit=r;
    });
    return hit;
  }
  function nearestPeerRow(row){
    if(!row) return null;
    var best=null, bestD=Infinity;
    rows.forEach(function(r){
      if(!r || r.name===row.name) return;
      var d=Math.abs(Number(r.v)-Number(row.v));
      if(isFinite(d) && d<bestD){ bestD=d; best=r; }
    });
    return best;
  }
  function drawLookupBars(items, title, unitText){
    var el=document.getElementById('chRank');
    if(!el||!window.Chart||!items||items.length<2) return false;
    var labels=items.map(function(it){return it.name;});
    var vals=items.map(function(it){return it.v;});
    var colors=items.map(function(it,i){
      if(i===0) return GOLD;
      if(/massachusetts|statewide|house median|senate median/i.test(it.name)) return INK;
      return STEEL;
    });
    var titleEl=document.getElementById('rankTitle');
    if(titleEl) titleEl.textContent=title||CHART.title||'Compared';
    var right=window.dlRightPad?window.dlRightPad(vals.map(function(v){return fmtVal(v,true);}),72):72;
    var payload={labels:labels,datasets:[{data:vals,backgroundColor:colors}]};
    var xScale=fitScale({title:{display:!!(unitText||axisUnit),text:unitText||axisUnit,color:GREY,font:{size:11}},
      ticks:{color:GREY,callback:function(v){return fmtVal(v,true);}},grid:{color:'rgba(34,34,34,.08)'},grace:'14%'}, vals);
    if(lookupChart){ lookupChart.destroy(); lookupChart=null; }
    lookupChart=new Chart(el,{type:'bar',
      data:payload,
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        layout:{padding:{right:right,top:6}},
        plugins:{legend:{display:false},
          tooltip:{callbacks:{label:function(c){return ' '+fmtVal(c.parsed.x);}}}},
        scales:{
          x:xScale,
          y:{ticks:{color:INK,font:{size:11,family:'Roboto,sans-serif'},autoSkip:false},
            grid:{display:false},border:{display:false}}
        }},
      plugins:[dataLabels(function(v){return fmtVal(v,true);},'all')]});
    rankChart=lookupChart;
    return true;
  }
  function drawLookupFig(){
    var cmp=FIND&&FIND.compare;
    var kind=(FIND&&FIND.kind)||'';
    var q=(document.getElementById('proofFind')&&document.getElementById('proofFind').value)||
          (document.getElementById('tblFind')&&document.getElementById('tblFind').value)||
          (FIND&&FIND.default_q)||'';
    var card=findCardFor(q);
    var row=card?rowByName(card.name):rowByName(q);
    if(kind==='town'){
      var sel=row||bostonRow()||rows[0];
      if(!sel) return false;
      var peer=null;
      var peers=(cmp&&cmp.pop_peers)||{};
      var p=peers[normFind(sel.name)];
      if(p) peer={name:p.name,v:p.v};
      if(!peer) peer=nearestPeerRow(sel);
      var bos=(cmp&&cmp.boston)||bostonRow();
      var items=[{name:sel.name,v:Number(sel.v)}];
      if(peer && peer.name!==sel.name) items.push({name:peer.name,v:Number(peer.v)});
      if(bos && bos.name && normFind(bos.name)!==normFind(sel.name) && (!peer || normFind(bos.name)!==normFind(peer.name))){
        items.push({name:bos.name||'Boston',v:Number(bos.v)});
      }
      return drawLookupBars(items, (sel.name||'This town')+' versus its nearest Census peer and Boston', 'people');
    }
    if(kind==='hospital'){
      var srp=card&&card.srp;
      if(srp==null && row && row.v!=null && fmt==='stars') srp=null;
      var avg=cmp&&cmp.statewide_srp;
      if(srp==null || !avg) return false;
      return drawLookupBars([
        {name: (card&&card.name)||(row&&row.name)||'This hospital', v:Number(srp)},
        {name: avg.name||'Statewide commercial average', v:Number(avg.v)}
      ], 'Commercial relative price versus the statewide average', 'relative price (1.00 = statewide)');
    }
    if(kind==='legislator'){
      var house=cmp&&cmp.house_median;
      var senate=cmp&&cmp.senate_median;
      var person=row||(card&&rowByName(card.name));
      if(!person || !house || !senate) return false;
      return drawLookupBars([
        {name: person.name, v:Number(person.v)},
        {name: house.name, v:Number(house.v)},
        {name: senate.name, v:Number(senate.v)}
      ], (person.name||'This member')+' versus House and Senate medians', 'dollars');
    }
    return false;
  }
  function bostonRow(){
    for(var i=0;i<rows.length;i++){
      if(/^boston/i.test(rows[i].name||'')) return rows[i];
    }
    return null;
  }
  function drawTownMapLater(){
    var el=document.getElementById('chTownMap');
    if(!el||!window.dlTownMap) return;
    window.dlTownMap(el,{
      rows:rows.map(function(r){ return {name:r.name, st:r.st||r.name, v:r.v, rank:r.rank}; }),
      format:function(v){ return fmtVal(v,true); },
      selected: selectedSt || (FIND && FIND.default_q) || '',
      onSelect:function(r){
        selectedSt=r.name||r.st||'';
        var find=document.getElementById('tblFind');
        if(find) find.value=r.name||'';
        var pf=document.getElementById('proofFind');
        if(pf) pf.value=r.name||'';
        applyFind();
        drawLookupFig();
        fillPlaceStrip();
      }
    });
  }
  function drawRank(){
    if(CHART.geo==='state'){ drawRankMap(); return; }
    if(CHART.compare==='town' || CHART.compare==='finder' || (FIND && (FIND.kind==='town'||FIND.kind==='hospital'||FIND.kind==='legislator'))){
      if(drawLookupFig()){
        drawTownMapLater();
        if(document.getElementById('chHist')) drawHist('chHist');
        return;
      }
    }
    if(CHART.compare==='town'){ drawTownMapLater(); return; }
    if(CHART.compare==='hist'){ drawHist(); return; }
    if(CHART.compare==='dots'){ drawDots(); return; }
    if(CHART.compare==='finder') return;
    var el=document.getElementById('chRank');
    if(!el||!window.Chart) return;
    chartRows=chartRowsFor();
    if(!chartRows.length) return;
    sizeRankPlot(chartRows.length);
    var titleEl=document.getElementById('rankTitle');
    if(titleEl) titleEl.textContent=rankTitleText();
    var vals=chartRows.map(function(r){return r.v;});
    var payload={
      labels:chartRows.map(rowLabel),
      datasets:[{data:vals,backgroundColor:chartRows.map(hlColor)}]
    };
    var xScale=fitScale({title:{display:!!axisUnit,text:axisUnit,color:GREY,font:{size:11}},
      ticks:{color:GREY,callback:function(v){return fmtVal(v,true);}},grid:{color:'rgba(34,34,34,.08)'},grace:'14%'}, vals);
    if(rankChart){
      rankChart.data=payload;
      copyFit(rankChart.options.scales.x, xScale);
      rankChart.update();
      return;
    }
    rankChart=new Chart(el,{type:'bar',
      data:payload,
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        layout:{padding:{right:72,top:6}},
        plugins:{legend:{display:false},
          tooltip:{callbacks:{
            title:function(items){var i=items[0]&&items[0].dataIndex; return (chartRows[i]&&chartRows[i].name)||'';},
            label:function(c){var r=chartRows[c.dataIndex]||{}; var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' \u00b7 '+unit:''); return ' '+fmtVal(c.parsed.x)+' \u00b7 rank '+(r.rank||'')+extra;}
          }}},
        scales:{
          x:xScale,
          y:{ticks:{color:INK,font:{size:11,family:'Roboto,sans-serif'},autoSkip:false,
            callback:function(v){return String(this.getLabelForValue(v));}},
            grid:{display:false},border:{display:false}}
        }},
      plugins:[dataLabels(function(v){return fmtVal(v,true);},'all')]});
  }
  function setRegion(next){
    region=(next && REGIONS.hasOwnProperty(next))?next:'all';
    [].slice.call(document.querySelectorAll('[data-region]')).forEach(function(btn){
      btn.classList.toggle('on', btn.getAttribute('data-region')===region);
    });
    drawRank();
    applyFind();
    writeQuery();
  }
  function setBand(next){
    var allowed={all:1,above:1,below:1,top10:1,bottom10:1};
    if(next==='above' || next==='below'){ if(!usCompare) next='all'; }
    band=(next && allowed[next])?next:'all';
    [].slice.call(document.querySelectorAll('[data-band]')).forEach(function(btn){
      btn.classList.toggle('on', btn.getAttribute('data-band')===band);
    });
    drawRank();
    applyFind();
    writeQuery();
  }
  [].slice.call(document.querySelectorAll('.region-bar')).forEach(function(bar){
    if(CHART.geo!=='state') return;
    bar.hidden=false;
    [].slice.call(bar.querySelectorAll('[data-region]')).forEach(function(btn){
      btn.addEventListener('click', function(){ setRegion(btn.getAttribute('data-region')); });
    });
  });
  [].slice.call(document.querySelectorAll('.explore-bar')).forEach(function(bar){
    if(CHART.geo!=='state') return;
    bar.hidden=false;
    [].slice.call(bar.querySelectorAll('[data-band]')).forEach(function(btn){
      var kind=btn.getAttribute('data-band');
      if((kind==='above' || kind==='below') && usCompare) btn.hidden=false;
      btn.addEventListener('click', function(){ setBand(btn.getAttribute('data-band')); });
    });
  });
  var startRegion=(q.get('region')||'').toLowerCase();
  if(startRegion && REGIONS.hasOwnProperty(startRegion)) region=startRegion;
  var startBand=(q.get('band')||'').toLowerCase();
  if(startBand) setBand(startBand);
  [].slice.call(document.querySelectorAll('[data-region]')).forEach(function(btn){
    btn.classList.toggle('on', btn.getAttribute('data-region')===region);
  });
  [].slice.call(document.querySelectorAll('[data-band]')).forEach(function(btn){
    btn.classList.toggle('on', btn.getAttribute('data-band')===band);
  });
  compareSt='FL';
  (function(){
    var sel=document.getElementById('lensSel');
    if(!sel || !hasLens) return;
    sel.addEventListener('change', function(){
      setLens(sel.value||'US', true);
    });
  })();
  var tabs=document.getElementById('mapTabs');
  function setRankPane(pane){
    var mapPane=document.getElementById('mapPane');
    var tablePane=document.getElementById('view-table');
    var showTable=pane==='table';
    if(mapPane) mapPane.hidden=showTable;
    if(tablePane && CHART.geo==='state') tablePane.hidden=!showTable;
    var ledeEl=document.getElementById('mapLede');
    if(ledeEl && CHART.geo==='state') ledeEl.hidden=showTable || !ledeEl.textContent;
    if(tabs){
      [].slice.call(tabs.querySelectorAll('.map-tab')).forEach(function(b){
        var on=showTable
          ? b.getAttribute('data-pane')==='table'
          : (b.getAttribute('data-pane')!=='table' && Number(b.getAttribute('data-view'))===mapView);
        b.classList.toggle('is-on', !!on);
      });
    }
    if(showTable){
      if(typeof fillTableBody==='function') fillTableBody();
      applyFind();
    }
    else drawRank();
  }
  if(tabs){
    tabs.addEventListener('click', function(ev){
      var btn=ev.target.closest('.map-tab');
      if(!btn) return;
      if(btn.getAttribute('data-pane')==='table'){
        setRankPane('table');
        return;
      }
      mapView=Number(btn.getAttribute('data-view'))||0;
      setRankPane('map');
    });
  }
  function applyDeepLink(){
    var h=parseHash();
    if(h.st){
      var want=String(h.st);
      var up=want.toUpperCase();
      if(up==='US'){
        selectedSt='';
      } else {
        var match=null;
        for(var i=0;i<rows.length;i++){
          var r=rows[i];
          if(r.st && String(r.st).toUpperCase()===up){ match=r; break; }
          if(r.name && String(r.name).toLowerCase()===want.toLowerCase()){ match=r; break; }
        }
        selectedSt=match ? (match.st||match.name||want) : (CHART.geo==='state'?up:want);
        var findEl=document.getElementById('tblFind');
        if(findEl && match) findEl.value=match.name||match.st||want;
        else if(findEl && !findEl.value) findEl.value=want;
      }
    }
    if(hasLens) applyLens(selectedSt||'US');
    if(h.view==='table' && CHART.geo==='state') setRankPane('table');
    applyFind();
    if(h.view==='rank' && CHART.geo==='state') drawRank();
  }
  window.addEventListener('hashchange', applyDeepLink);
  drawRank();
  applyDeepLink();
  fillPlaceStrip();
  var chTrend=document.getElementById('chTrend');
  var trend=(DL&&DL.trend)||{};
  if(CHART.headline_from==='secondary.public_k12_enrollment'){
    var enr=((((DL||{}).derived||{}).secondary)||{}).public_k12_enrollment||{};
    if(enr.trend && enr.trend.length) trend={MA:enr.trend};
  }
  var allTrendKeys=Object.keys(trend).filter(function(k){return trend[k]&&trend[k].length>=2;});
  var pretty={US:'United States',MA:'Massachusetts',FL:'Florida',Boston:'Boston'};
  function trendName(st){
    if(pretty[st]) return pretty[st];
    for(var i=0;i<rows.length;i++) if(rows[i].st===st) return rows[i].name;
    return st;
  }
  var coreKeys=['US','MA','FL','Boston'].filter(function(k){ return allTrendKeys.indexOf(k)>=0; });
  var extraKeys=allTrendKeys.filter(function(k){ return coreKeys.indexOf(k)<0; }).sort();
  var pickedSt='';
  var trendChart=null;
  var startTrend=(q.get('trend')||'').toUpperCase();
  if(startTrend && allTrendKeys.indexOf(startTrend)>=0 && coreKeys.indexOf(startTrend)<0) pickedSt=startTrend;
  var pickWrap=document.getElementById('trendPick');
  var pickSel=document.getElementById('trendSel');
  if(pickWrap && pickSel && extraKeys.length){
    pickWrap.hidden=false;
    pickSel.innerHTML='<option value=\"\">'+coreKeys.map(trendName).join(', ')+'</option>'+
      extraKeys.map(function(st){
        return '<option value=\"'+st+'\"'+(st===pickedSt?' selected':'')+'>'+trendName(st)+'</option>';
      }).join('');
    pickSel.addEventListener('change', function(){
      pickedSt=pickSel.value||'';
      drawHeadline();
      if(typeof writeQuery==='function') writeQuery();
    });
  }
  function trendColor(k){
    return roleColor(k, pickedSt);
  }
  function trendKey(p){
    if(!p) return '';
    if(p.m) return String(p.m);
    if(p.q) return String(p.q);
    if(p.y!=null) return String(p.y);
    return '';
  }
  function sortPts(pts){
    return (pts||[]).slice().sort(function(a,b){
      return trendKey(a).localeCompare(trendKey(b));
    });
  }
  function visibleTrendKeys(){
    var keys=coreKeys.slice();
    if(pickedSt && allTrendKeys.indexOf(pickedSt)>=0 && keys.indexOf(pickedSt)<0) keys.push(pickedSt);
    if(!keys.length) keys=allTrendKeys.slice();
    return keys;
  }
  function headlineMode(keys){
    var maxs=[], allPos=true;
    keys.forEach(function(k){
      var vs=[];
      (trend[k]||[]).forEach(function(p){
        if(!p || p.v==null) return;
        var n=Number(p.v);
        if(!isFinite(n)) return;
        if(n<=0) allPos=false;
        vs.push(Math.abs(n));
      });
      if(vs.length) maxs.push(Math.max.apply(null, vs));
    });
    if(!allPos || maxs.length<2 || Math.min.apply(null,maxs)===0) return 'level';
    return (Math.max.apply(null,maxs)/Math.min.apply(null,maxs)>=2.5)?'index_100':'level';
  }
  function fmtIndex(v){
    if(v==null||v==='') return '';
    var n=Number(v);
    if(!isFinite(n)) return '';
    if(Math.abs(n-Math.round(n))<0.05) return String(Math.round(n));
    return n.toFixed(1);
  }
  var trendWindow='recent';
  var winBar=document.getElementById('trendWindow');
  if(winBar){
    [].slice.call(winBar.querySelectorAll('[data-win]')).forEach(function(btn){
      btn.addEventListener('click', function(){
        trendWindow=btn.getAttribute('data-win')||'recent';
        [].slice.call(winBar.querySelectorAll('[data-win]')).forEach(function(b){
          b.classList.toggle('on', b.getAttribute('data-win')===trendWindow);
        });
        drawHeadline();
      });
    });
  }
  function isMonthlyLabs(labs){
    return !!(labs && labs.length && /^\\d{4}-\\d{2}$/.test(String(labs[0])));
  }
  function drawHeadline(){
    if(!chTrend || !window.Chart || !allTrendKeys.length) return;
    var keys=visibleTrendKeys();
    var trendMode=headlineMode(keys);
    var labelSet={};
    var seriesPts={};
    keys.forEach(function(k){
      var pts=sortPts(trend[k]);
      seriesPts[k]=pts;
      pts.forEach(function(p){ var lab=trendKey(p); if(lab) labelSet[lab]=1; });
    });
    var labels=Object.keys(labelSet).sort();
    var monthly=isMonthlyLabs(labels);
    if(winBar) winBar.hidden=!(monthly && labels.length>60);
    if(monthly && labels.length>60 && trendWindow!=='full') labels=labels.slice(-36);
    var rawByKey={};
    var endLabs=[];
    var datasets=keys.map(function(k){
      var pts=seriesPts[k]||[];
      var by={}, first=null;
      pts.forEach(function(p){
        if(first==null && p && p.v!=null && Number(p.v)>0) first=Number(p.v);
        by[trendKey(p)]=p;
      });
      var raws=[], nums=[];
      labels.forEach(function(lab){
        var p=by[lab];
        if(!p || p.v==null || !isFinite(Number(p.v))){ raws.push(null); nums.push(null); return; }
        var raw=Number(p.v);
        raws.push(raw);
        if(trendMode==='index_100' && first) nums.push((raw/first)*100);
        else nums.push(raw);
      });
      rawByKey[k]=raws;
      var last=null;
      for(var i=nums.length-1;i>=0;i--){ if(nums[i]!=null){ last=nums[i]; break; } }
      var yFmtLab=trendMode==='index_100'?fmtIndex(last):fmtVal(last,true);
      if(yFmtLab) endLabs.push(yFmtLab);
      var col=trendColor(k);
      return {label:trendName(k), key:k,
        data:nums,
        borderColor:col,
        backgroundColor:(keys.length===1?'rgba(41,60,92,.08)':'transparent'),
        fill:keys.length===1,
        spanGaps:false,
        pointRadius:labels.length>24?0:2,
        pointHoverRadius:4,
        borderWidth:(k==='MA'||k==='FL'||k===pickedSt)?2:1.75};
    });
    var yTitle=trendMode==='index_100'?"Indexed to each series' first year (100 = starting level)":axisUnit;
    var yFmt=trendMode==='index_100'?fmtIndex:function(v){return fmtVal(v,true);};
    var yNums=[];
    datasets.forEach(function(d){ (d.data||[]).forEach(function(v){ if(v!=null&&v!=='') yNums.push(v); }); });
    function tickLab(v){
      var lab=String(v==null?'':v);
      if(/^\\d{4}-\\d{2}$/.test(lab)) return lab.slice(-2)==='01'?lab.slice(0,4):'';
      return lab;
    }
    var titleEl=document.getElementById('trendTitle');
    var baseTitle=trendMode==='index_100'?"Indexed to each series' first year (100 = starting level)":(CHART.trend_title||CHART.label||'Trend');
    if(titleEl && pickedSt) titleEl.textContent=baseTitle+', plus '+trendName(pickedSt);
    else if(titleEl) titleEl.textContent=baseTitle;
    var payload={labels:labels,datasets:datasets};
    var right=window.dlRightPad?window.dlRightPad(endLabs, 96):96;
    var opts={responsive:true,maintainAspectRatio:false,
      layout:{padding:{top:12,right:right}},
      plugins:{legend:{display:true,position:'top',align:'end'},
        tooltip:{callbacks:{
          title:function(items){
            var i=items[0]&&items[0].dataIndex;
            return (labels[i]!=null)?String(labels[i]):'';
          },
          label:function(c){
          var di=c.dataIndex, key=c.dataset.key, raw=rawByKey[key]?rawByKey[key][di]:null;
          if(trendMode==='index_100'){
            var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' '+unit:'');
            return ' '+c.dataset.label+': '+(raw==null?'':fmtVal(raw)+extra)+(raw==null?'':' \u00b7 index '+fmtIndex(c.parsed.y));
          }
          var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' '+unit:'');
          return ' '+c.dataset.label+': '+fmtVal(c.parsed.y)+extra;
        }}}},
      scales:{
        x:{type:'category',ticks:{color:GREY,autoSkip:true,maxTicksLimit:12,
          callback:function(v){return tickLab(this.getLabelForValue(v));}}},
        y:fitScale({grace:'10%',title:{display:!!yTitle,text:yTitle,color:GREY,font:{size:11}},
          ticks:{color:GREY,callback:function(v){return yFmt(v);}},grid:{color:'rgba(34,34,34,.08)'}}, yNums)
      }};
    var plugins=[dataLabels(yFmt, labels.length>18?'end':'all')];
    if(window.dlEndDot) plugins.push(window.dlEndDot({prefer:'MA'}));
    if(trendMode==='index_100' && window.dlRefLineY) plugins.push(window.dlRefLineY(100, GOLD, 'starting level'));
    if(trendChart){ trendChart.destroy(); trendChart=null; }
    trendChart=new Chart(chTrend,{type:'line',data:payload,options:opts,plugins:plugins});
  }
  drawHeadline();
  function fmtInsight(fmt, v, short){
    if(v==null||v==='') return '';
    var n=Number(v), sign=n<0?'\u2212':'', a=Math.abs(n);
    if(fmt==='usd'||fmt==='usd_millions'){
      var d=fmt==='usd_millions'?a*1e6:a;
      if(d>=1e12) return sign+'$'+(d/1e12).toFixed(2)+(short?'T':' trillion');
      if(d>=1e9) return sign+'$'+(d/1e9).toFixed(2)+(short?'B':' billion');
      if(d>=1e6) return sign+'$'+(d/1e6).toFixed(2)+(short?'M':' million');
      return sign+'$'+Math.round(d).toLocaleString();
    }
    if(fmt==='percent') return n.toFixed(1)+'%';
    if(a>=1000) return sign+Math.round(a).toLocaleString();
    if(Math.abs(n-Math.round(n))<1e-6) return sign+String(Math.round(a));
    return sign+a.toLocaleString(undefined,{maximumFractionDigits:1});
  }
  function catTick(maxLen){
    return {color:INK,font:{size:11,family:'Roboto,sans-serif'},autoSkip:false,
      callback:function(v){
        var lab=this.getLabelForValue(v);
        if(lab==null||lab==='') return '';
        lab=String(lab);
        var cap=maxLen||28;
        if(lab.length<=cap) return lab;
        var cut=lab.lastIndexOf(' ', cap);
        if(cut<8) cut=cap;
        var a=lab.slice(0,cut), b=lab.slice(cut).replace(/^\\s+/, '');
        if(b.length>cap) b=b.slice(0,cap-1)+'\u2026';
        return [a, b];
      }};
  }
  function valTick(fmt){
    return {color:GREY,font:{size:11,family:'Roboto,sans-serif'},
      callback:function(v){return fmtInsight(fmt,v,true);}};
  }
  function valTitle(unit){
    return unit?{display:true,text:unit,color:GREY,font:{size:11}}:{display:false};
  }
  var insightCharts={};
  (INSIGHTS||[]).forEach(function(fig, i){
    try {
    var el=document.getElementById('chInsight'+i);
    if(!el||!fig) return;
    if(fig.type==='map' && window.dlStateMap && fig.rows){
      window.dlStateMap(el,{
        mode:'hex',
        highlightFlorida:true,
        rows:fig.rows,
        format:function(v){return fmtInsight(fig.format||'number',v,true);},
        extra:function(r){return r.rank?('rank '+r.rank):'';}
      });
      return;
    }
    if(!window.Chart||!fig.labels||!fig.series) return;
    var ifmt=fig.format||'number';
    var iunit=fig.unit||(ifmt==='percent'?'percent':((ifmt==='usd'||ifmt==='usd_millions')?'dollars':''));
    var extra=(ifmt==='usd'||ifmt==='usd_millions'||ifmt==='percent')?'':(iunit?' '+iunit:'');
    var horiz=fig.type==='bar';
    var ivals=seriesValues(fig.series);
    var scales=horiz?{
      x:fitScale({ticks:valTick(ifmt),title:valTitle(iunit),grid:{color:'rgba(34,34,34,.08)'},grace:'14%'}, ivals),
      y:{ticks:catTick(32),grid:{display:false},border:{display:false}}
    }:{
      x:{ticks:Object.assign({},catTick(16),{color:GREY,autoSkip:fig.labels.length>12,maxTicksLimit:12}),
        grid:{display:false}},
      y:fitScale({ticks:valTick(ifmt),title:valTitle(iunit),grid:{color:'rgba(34,34,34,.08)'},border:{display:false},grace:'12%'}, ivals)
    };
    var nLab=(fig.labels||[]).length;
    var iRight=fig.type==='line'?(window.dlRightPad?window.dlRightPad((fig.labels||[]).map(function(){return '000';}),96):96):(horiz?72:16);
    var opts={
      responsive:true,maintainAspectRatio:false,
      layout:{padding:{top:fig.type==='grouped'?36:(fig.type==='line'?16:8),right:iRight}},
      plugins:{legend:{display:fig.type==='grouped'||(fig.series.length>1 && fig.series[0].label),
        position:'top',align:'end'},
        tooltip:{callbacks:{
          title:function(items){
            var idx=items[0]&&items[0].dataIndex;
            return (fig.labels&&fig.labels[idx])||'';
          },
          label:function(c){
            var lab=c.dataset.label?c.dataset.label+': ':'';
            var val=horiz?c.parsed.x:c.parsed.y;
            return ' '+lab+fmtInsight(ifmt,val)+extra;
          }
        }}},
      scales:scales
    };
    var lbl=dataLabels(function(v){return fmtInsight(ifmt,v,true);}, fig.type==='line'&&nLab>8?'end':'all');
    if(fig.type==='slope'){
      new Chart(el,{type:'line',
        data:{labels:fig.labels,datasets:fig.series.map(function(s){
          return {label:s.label||fig.title,data:s.data,borderColor:s.color||INK,
            backgroundColor:'transparent',spanGaps:false,tension:0,pointRadius:5,pointHoverRadius:6,borderWidth:2};
        })},
        options:Object.assign({},opts,{indexAxis:'x',layout:{padding:{top:16,right:96}}}),
        plugins:[lbl]});
      return;
    }
    if(fig.type==='hist'){
      var s0=fig.series[0]||{};
      new Chart(el,{type:'bar',
        data:{labels:fig.labels,datasets:[{data:s0.data,backgroundColor:s0.colors||BLUE}]},
        options:Object.assign({},opts,{indexAxis:'x',layout:{padding:{top:8,right:16}}}),
        plugins:[lbl]});
      return;
    }
    if(fig.type==='line'){
      new Chart(el,{type:'line',
        data:{labels:fig.labels,datasets:fig.series.map(function(s){
          return {label:s.label||fig.title,data:s.data,borderColor:s.color||INK,
            backgroundColor:'transparent',spanGaps:false};
        })},
        options:Object.assign({},opts,{indexAxis:'x'}),
        plugins:[lbl]});
      return;
    }
    if(fig.type==='grouped'){
      new Chart(el,{type:'bar',
        data:{labels:fig.labels,datasets:fig.series.map(function(s){
          return {label:s.label,data:s.data,backgroundColor:s.color||BLUE};
        })},
        options:Object.assign({},opts,{indexAxis:'x'}),
        plugins:[lbl]});
      return;
    }
    var s0=fig.series[0]||{};
    function barColors(labs){
      return (labs||[]).map(function(lab){
        return roleColor(lab, compareSt);
      });
    }
    function insightPicks(src){
      var cells=src.filter_states||[];
      var by={}; cells.forEach(function(c){ by[c.st]=c; });
      var picks=[];
      if(by.US) picks.push('US');
      if(by.MA) picks.push('MA');
      if(by.FL && picks.indexOf('FL')<0) picks.push('FL');
      cells.forEach(function(c){
        if(picks.length>=4) return;
        if(picks.indexOf(c.st)<0) picks.push(c.st);
      });
      return picks;
    }
    function applyInsightStates(src, picks){
      var by={}; (src.filter_states||[]).forEach(function(c){ by[c.st]=c; });
      var labels=[], values=[];
      picks.forEach(function(st){
        var c=by[st];
        if(!c) return;
        labels.push(c.name);
        values.push(c.v);
      });
      if(labels.length<2) return false;
      src.labels=labels;
      src.series=[{label:'',data:values,colors:barColors(labels)}];
      return true;
    }
    var pickSel=document.getElementById('insightSel'+i);
    if(fig.type==='bar' && fig.filter_states && fig.filter_states.length>=3 && pickSel){
      var picks=insightPicks(fig);
      var extras=(fig.filter_states||[]).filter(function(c){ return c.st!=='US' && c.st!=='MA'; });
      if(extras.length<2){
        if(pickSel.parentNode) pickSel.parentNode.hidden=true;
      } else {
      pickSel.innerHTML=extras.map(function(c){
        var on=picks.indexOf(c.st)>=0 && c.st!=='US' && c.st!=='MA';
        return '<option value=\"'+c.st+'\"'+(on?' selected':'')+'>'+c.name+'</option>';
      }).join('');
      }
      applyInsightStates(fig, picks);
      s0=fig.series[0]||s0;
      pickSel.addEventListener('change', function(){
        var next=insightPicks(fig);
        if(next.length) next[next.length-1]=pickSel.value;
        if(!applyInsightStates(fig, next)) return;
        if(insightCharts[i]){
          insightCharts[i].data.labels=fig.labels;
          insightCharts[i].data.datasets[0].data=fig.series[0].data;
          insightCharts[i].data.datasets[0].backgroundColor=fig.series[0].colors;
          insightCharts[i].update();
        }
      });
    }
    insightCharts[i]=new Chart(el,{type:'bar',
      data:{labels:fig.labels,datasets:[{data:s0.data,backgroundColor:s0.colors||BLUE}]},
      options:Object.assign({},opts,{indexAxis:'y'}),
      plugins:[lbl]});
    } catch (err) {
      if (window.console && console.error) console.error('insight chart '+((fig&&fig.id)||i), err);
    }
  });
  var tb=document.querySelector('#tblStates tbody');
  if(tb){
    var cols=CHART.table_columns||[
      {key:'name',label:'Name',cls:'m'},
      {key:'v',label:'Value',align:'n',fmt:'value'},
      {key:'rank',label:'Rank',align:'n'},
      {key:'yoy_pct',label:'YoY',align:'n',kind:'yoy'}
    ];
    function fmtCell(col,row){
      var v=row[col.key];
      if(col.kind==='yoy'){
        if(v==null||v==='') return '';
        return (Number(v)>0?'+':'')+v+'%';
      }
      if(col.fmt==='usd_cents'){
        if(v==null||v==='') return '';
        var n=Number(v), sign=n<0?'\u2212':'';
        return sign+'$'+Math.abs(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
      }
      if(col.key==='v' || col.fmt==='value'){
        var view=currentMapView();
        if(view && view.format) return fmtInsight(view.format, v, true);
        return fmtVal(v);
      }
      if(v==null||v==='') return '';
      return String(v).replace(/</g,'');
    }
    function tableRows(){
      if(CHART.geo!=='state') return rows;
      var base=mapBaseRows();
      var keep=mapActiveStates();
      if(!keep) return base.slice();
      return base.filter(function(r){ return keep.indexOf(r.st)>=0; });
    }
    function syncTableHead(){
      var view=currentMapView();
      var src=tableRows();
      var vTh=document.querySelector('#tblStates thead th[data-key="v"] .th-sort');
      if(vTh && view && view.unit){
        var u=String(view.unit);
        vTh.textContent=u.charAt(0).toUpperCase()+u.slice(1);
      } else if(vTh && CHART.unit){
        vTh.textContent=(CHART.table_columns&&CHART.table_columns[1]&&CHART.table_columns[1].label)||'Figure';
      }
      var yoyTh=document.querySelector('#tblStates thead th[data-key="yoy_pct"]');
      var hasYoy=src.some(function(r){ return r && r.yoy_pct!=null && r.yoy_pct!==''; });
      if(yoyTh) yoyTh.hidden=!hasYoy;
    }
    fillTableBody=function(){
      var src=tableRows();
      syncTableHead();
      tb.innerHTML=src.map(function(r){
        var cls=hlClass(r);
        var hl=cls?' class="'+cls+'"':'';
        var key=((r.name||'')+' '+(r.st||'')).toLowerCase();
        var cells=cols.map(function(c){
          if(c.key==='yoy_pct'){
            var yoyTh=document.querySelector('#tblStates thead th[data-key="yoy_pct"]');
            if(yoyTh && yoyTh.hidden) return '';
          }
          var cls=c.cls||(c.align==='n'?'n':'');
          return '<td'+(cls?' class="'+cls+'"':'')+'>'+fmtCell(c,r)+'</td>';
        }).join('');
        var sorts=cols.map(function(c){
          var sv=r[c.key];
          return ' data-sort-'+c.key+'="'+(sv==null?'':String(sv).replace(/"/g,''))+'"';
        }).join('');
        return '<tr'+hl+(r.st?' id="row-'+r.st+'"':'')+' data-q="'+key.replace(/"/g,'')+'" data-st="'+(r.st||'')+'"'+sorts+'>'+cells+'</tr>';
      }).join('');
      if(typeof sortRows==='function') sortRows();
    };
    var find=document.getElementById('tblFind');
    var countEl=document.getElementById('tblCount');
    var sortKey='rank';
    var sortDir=1;
    var BAND_NAMES={all:'',above:'above the U.S.',below:'below the U.S.',top10:'in the top 10',bottom10:'in the bottom 10'};
    function sortRows(){
      var trs=[].slice.call(tb.querySelectorAll('tr'));
      var key=sortKey||'rank';
      trs.sort(function(a,b){
        var av=a.getAttribute('data-sort-'+key);
        var bv=b.getAttribute('data-sort-'+key);
        var aEmpty=av==null||av==='';
        var bEmpty=bv==null||bv==='';
        if(aEmpty&&bEmpty) return 0;
        if(aEmpty) return 1;
        if(bEmpty) return -1;
        var an=Number(av), bn=Number(bv);
        var cmp;
        if(isFinite(an)&&isFinite(bn)&&String(av).trim()!==''&&String(bv).trim()!=='') cmp=an-bn;
        else cmp=String(av).localeCompare(String(bv),undefined,{numeric:true,sensitivity:'base'});
        return cmp*sortDir;
      });
      trs.forEach(function(tr){ tb.appendChild(tr); });
      [].slice.call(document.querySelectorAll('#tblStates thead th[data-key]')).forEach(function(th){
        var k=th.getAttribute('data-key');
        if(k===key) th.setAttribute('aria-sort', sortDir>0?'ascending':'descending');
        else th.removeAttribute('aria-sort');
      });
    }
    fillTableBody();
    [].slice.call(document.querySelectorAll('#tblStates thead th[data-key]')).forEach(function(th){
      th.addEventListener('click', function(){
        var k=th.getAttribute('data-key');
        if(!k) return;
        if(sortKey===k) sortDir=-sortDir;
        else { sortKey=k; sortDir=k==='name'||k==='rank'?1:-1; }
        sortRows();
      });
    });
    fillTableBody();
    applyFind=function(){
      var q=(find&&find.value||'').toLowerCase().replace(/^\\s+|\\s+$/g,'');
      var list=(CHART.geo==='state')?mapActiveStates():activeStates();
      var n=0, shown=0, first=null;
      [].slice.call(tb.querySelectorAll('tr')).forEach(function(tr){
        var st=tr.getAttribute('data-st')||'';
        var inSet=!list || list.indexOf(st)>=0;
        var ok=inSet && (!q || (tr.getAttribute('data-q')||'').indexOf(q)>=0);
        tr.hidden=!ok;
        tr.classList.toggle('is-on', !!(ok && selectedSt && st===selectedSt));
        n++;
        if(ok){ shown++; if(!first) first=tr; }
      });
      var total=list?list.length:n;
      var extra=(region!=='all'?' in '+REGION_NAMES[region]:'')+(band!=='all'?(region!=='all'?' ':' ')+BAND_NAMES[band]:'');
      if(countEl){
        if(q) countEl.textContent=shown+' of '+total+extra;
        else if(extra) countEl.textContent=shown+extra;
        else countEl.textContent=n+' '+(n===1?'row':'rows');
      }
      if(q && shown===1 && first) first.scrollIntoView({block:'nearest'});
    };
    var params=new URLSearchParams(location.search);
    var startQ=params.get('q')||params.get('st')||'';
    if(find && startQ && !find.value) find.value=startQ;
    if(find && !find.value && FIND && FIND.default_q) find.value=FIND.default_q;
    var proofFind=document.getElementById('proofFind');
    if(proofFind){
      if(!proofFind.value && find) proofFind.value=find.value||'';
      proofFind.addEventListener('input', function(){
        if(find) find.value=proofFind.value;
        applyFind();
        writeQuery();
      });
    }
    if(find) find.addEventListener('input', function(){
      if(proofFind) proofFind.value=find.value;
      applyFind();
      writeQuery();
    });
    writeQuery=function(){
      var qv=(find&&find.value||'').replace(/^\\s+|\\s+$/g,'');
      var params=new URLSearchParams();
      if(region && region!=='all') params.set('region', region);
      if(band && band!=='all') params.set('band', band);
      if(pickedSt) params.set('trend', pickedSt);
      if(qv) params.set('q', qv);
      var qs=params.toString();
      history.replaceState(null,'',location.pathname+(qs?('?'+qs):'')+location.hash);
    };
    var card=document.getElementById('findCard');
    var proofCard=document.getElementById('proofCard');
    function norm(s){ return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\\b(city|town|the)\\b/g,' ').replace(/^\\s+|\\s+$/g,'').replace(/\\s+/g,' '); }
    function cardMarkup(row, extra){
      extra=extra||{};
      var facts=extra.facts||[];
      var yoy=row && row.yoy_pct!=null ? ((row.yoy_pct>0?'+':'')+row.yoy_pct+'%') : (extra.yoy!=null?((extra.yoy>0?'+':'')+extra.yoy+'%'):'');
      var rank=(row && row.rank) || extra.rank;
      var n=(row && row.n) || extra.n;
      var val=extra.value || (row?fmtVal(row.v):'');
      var name=extra.name || (row && row.name) || '';
      var metric=(FIND&&FIND.metric)||'Value';
      return '<div class="fc-k">'+metric+'</div>'+
        '<h3>'+name.replace(/</g,'')+'</h3>'+
        '<div class="fc-val">'+val+'</div>'+
        (rank?'<div class="fc-rank">Rank '+rank+(n?(' of '+n):'')+(yoy?(' \\u00b7 '+yoy):'')+'</div>':'')+
        (facts.length?'<ul class="fc-facts">'+facts.map(function(f){return '<li>'+String(f).replace(/</g,'')+'</li>';}).join('')+'</ul>':'')+
        '<div class="fc-src">Share this row: add ?q='+encodeURIComponent(name)+' to the URL.</div>';
    }
    function renderCard(row, extra){
      extra=extra||{};
      var html=cardMarkup(row, extra);
      if(card){ card.hidden=false; card.innerHTML=html; }
      if(proofCard){ proofCard.hidden=false; proofCard.innerHTML=html; }
    }
    function hideCard(){
      if(card){ card.hidden=true; card.innerHTML=''; }
      if(proofCard && !(FIND && FIND.default_q)){ proofCard.hidden=true; proofCard.innerHTML=''; }
    }
    function matchCard(q){
      if(!q || !FIND || !FIND.cards) return null;
      var nq=norm(q);
      var cards=FIND.cards;
      if(cards[nq]) return cards[nq];
      var hits=[];
      Object.keys(cards).forEach(function(k){
        if(k.indexOf(nq)>=0 || nq.indexOf(k)>=0) hits.push(cards[k]);
      });
      if(hits.length===1) return hits[0];
      return null;
    }
    var _apply=applyFind;
    applyFind=function(){
      _apply();
      var q=(find&&find.value||'').replace(/^\\s+|\\s+$/g,'');
      var extra=matchCard(q);
      var shown=[];
      [].slice.call(tb.querySelectorAll('tr')).forEach(function(tr){ if(!tr.hidden) shown.push(tr); });
      if(extra && shown.length===1){
        var key=(shown[0].getAttribute('data-q')||'');
        var row=null;
        var src=(CHART.geo==='state')?mapBaseRows():rows;
        src.forEach(function(r){
          var rk=((r.name||'')+' '+(r.st||'')).toLowerCase();
          if(rk===key) row=r;
        });
        renderCard(row, extra);
      } else if(shown.length===1){
        var key2=(shown[0].getAttribute('data-q')||'');
        var row2=null;
        var src2=(CHART.geo==='state')?mapBaseRows():rows;
        src2.forEach(function(r){
          var rk=((r.name||'')+' '+(r.st||'')).toLowerCase();
          if(rk===key2) row2=r;
        });
        var extra2=row2?matchCard(row2.name):null;
        renderCard(row2, extra2||{});
      } else {
        hideCard();
      }
      if(typeof drawLookupFig==='function') drawLookupFig();
      fillPlaceStrip();
    };
    applyFind();
    applyDeepLink();
  }
EXTRA_TOOL_JS})();
</script>
""".replace("SLUG", slug).replace("CHART_JSON", json.dumps(spec, ensure_ascii=True)).replace("INSIGHTS_JSON", json.dumps(insights + later_insights, ensure_ascii=True)).replace("MAP_VIEWS_JSON", json.dumps(map_views, ensure_ascii=True)).replace("FIND_JSON", json.dumps(find_spec, ensure_ascii=True)).replace("EXTRA_TOOL_JS", extra_tool_js(app, ledger))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} | Pioneer Institute | DataLabs</title>
<meta name="description" content="{esc(standfirst)}">
<link rel="canonical" href="https://datalabsai.netlify.app/{esc(slug)}/">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Pioneer DataLabs">
<meta property="og:title" content="{esc(title)} | Pioneer Institute">
<meta property="og:description" content="{esc(standfirst)}">
<meta property="og:url" content="https://datalabsai.netlify.app/{esc(slug)}/">
<meta property="og:image" content="https://datalabsai.netlify.app/assets/og-image.png">
<script src="/assets/chart.umd.min.js"></script>
<script src="/assets/chart-theme.js"></script>
<script src="/assets/chart-labels.js"></script>
<script src="/assets/us-map.js"></script>
<link rel="stylesheet" href="/assets/us-map.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Bodoni:ital,wght@0,400..700;1,400..700&family=Roboto:wght@300..900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/datalabs.css">
<link rel="stylesheet" href="/assets/suite.css">
<link rel="stylesheet" href="/assets/ask-widget.css">
</head>
<body>
<div class="wrap">
<div class="sitebar">
  <div class="sbleft">
    <a class="piword" href="https://pioneerinstitute.org">Pioneer Institute</a>
    <a class="backlink" href="/">DataLabs catalog</a>
    <a class="nav" href="/#about">About</a>
    <a class="nav" href="/status/">Status</a>
  </div>
</div>
<header>
  <h1>{esc(title)}</h1>
  <div class="standfirst">{esc(standfirst)}</div>
  <div class="byline">Pioneer Institute DataLabs</div>
  <div class="dateline">
<!-- DATA:BEGIN {slug}-dateline -->
    {esc(paper_dateline(as_of_label, revised))}
<!-- DATA:END {slug}-dateline -->
  </div>
</header>
{jump}
{latest_section}
{table_section}{extra_section}
{related_section}
<section id="sources">
  <h2>Data Sources</h2>
  <div class="subhead">Every figure traces to a source below. Ranks and changes are Pioneer calculations.</div>
  <details class="srcfold">
    <summary><span class="car">&#9654;</span><span class="name">Source register: cadence, vintage, and next release</span></summary>
    <div class="fold-body">
      <div class="scroll"><table class="reg">
        <thead><tr><th>Source</th><th>Publisher cadence</th><th>Data vintage</th><th>Next release</th></tr></thead>
        <tbody>
          {src_rows(ledger)}
        </tbody>
      </table></div>
    </div>
  </details>
  <details class="simplify">
    <summary><span class="car">&#9654;</span><span>What this page does not cover</span></summary>
    <div class="dt-body">
      <p class="body-p">{esc(app['exclusions'])}</p>
      {('<p class="body-p">It replaces these Tableau workbooks: ' + replaces + '.</p>') if replaces else ''}
    </div>
  </details>
</section>
<footer>
  <div class="fbrand"><span class="pi">Pioneer Institute</span> &nbsp;&middot;&nbsp; 185 Devonshire Street, Suite 1101, Boston, MA 02110 &nbsp;&middot;&nbsp; <a href="https://pioneerinstitute.org">pioneerinstitute.org</a></div>
  <div class="frow">
<!-- DATA:BEGIN {slug}-footer-meta -->
    <div>{esc(title)} &middot; Data through {esc(as_of_label)} &middot; Revised {esc(revised)}</div>
<!-- DATA:END {slug}-footer-meta -->
    <div>{nsrc} {src_word} in the register</div>
  </div>
  <div class="disclaimer">
    <div><b>About this tool.</b> {esc(title)} is a Pioneer Institute DataLabs research tool. Corrections and data refreshes are logged in the <a href="/changelog/">public changelog</a>. It is a living data tool, not a static report.</div>
    <div><b>Corrections.</b> Write <a href="mailto:jcalabrese@pioneerinstitute.org">jcalabrese@pioneerinstitute.org</a>.</div>
    <div><b>How to cite.</b>
<!-- DATA:BEGIN {slug}-cite -->
{esc(cite)}
<!-- DATA:END {slug}-cite -->
    </div>
    <div><b>Research and educational use only.</b> This tool is provided strictly for research and educational purposes. Figures are compiled in good faith from the public sources named in the register and are accurate to the verification date shown in the masthead. Nothing here is advice.</div>
    <div><b>Verified figures.</b> {"Live figures on this page were rebuilt from the files in the register and checked against a publisher total where one exists." if live else "No figures are published on this page yet. The register is the work plan."}</div>
  </div>
  <div class="flegal">Copyright &copy; 2026 Pioneer Institute. All rights reserved.</div>
</footer>
</div>
<script src="/assets/ask-widget.js"></script>
{js}
</body>
</html>
"""


def main():
    wanted = {a for a in sys.argv[1:] if not a.startswith("-")}
    apps = load_apps()
    n = 0
    missing = []
    for app in apps:
        if wanted and app["id"] not in wanted and app.get("slug") not in wanted:
            continue
        path = ledger_path(app["id"])
        if not path.exists():
            sys.exit(f"FATAL: missing ledger {path}")
        ledger = json.loads(path.read_text(encoding="utf-8"))
        dest = ROOT / app["slug"] / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page_html(app, ledger, apps), encoding="utf-8")
        n += 1
        print(f"render {app['id']} -> {dest.relative_to(ROOT)}")
        if ledger.get("status") == "live" and not insight_figures(app, ledger) and app["id"] not in FINDER_TOOLS | TOWN_TOOLS | HIST_TOOLS | {"DL-07", "DL-33"}:
            missing.append(app["id"])
    if missing:
        sys.exit("FATAL: no insight figures for " + ", ".join(missing))
    print(f"rendered {n} suite pages")


if __name__ == "__main__":
    main()
