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
from suite_common import ROOT, catalog_dashboards, commify, load_apps, ledger_path, paper_dateline, usd_prose

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
FINDER_TOOLS = {"DL-10", "DL-25", "DL-26", "DL-34"}
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
    "DL-06": ["DL-07", "DL-09", "DL-34"],
    "DL-34": ["DL-06", "DL-07", "DL-27"],
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
    "bps-schools": "Largest schools",
    "bps-gender": "Gender",
    "bps-race": "Race",
    "bps-grades": "Grades",
    "bps-ppe": "Per-pupil spending",
    "bps-buses": "Bus routes",
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
    "DL-34": {
        "title": "Enrollment, spending, and MCAS",
        "lede": (
            "Fall enrollment, total expenditures per pupil, and Boston "
            "Next Generation MCAS grades 3-8."
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


def _sy_label(year):
    y = int(year)
    return f"{y - 1}-{str(y)[2:]}"


def bps_enroll_ppe_lede(ledger):
    """Published enrollment, PPE, and Boston MCAS endpoints on one lede."""
    sec = ((ledger.get("derived") or {}).get("secondary") or {})
    enroll = (sec.get("bps_enrollment_trend") or {}).get("trend") or []
    ppe = (sec.get("bps_finance_fy2025") or {}).get("trend") or []
    mcas = sec.get("bps_mcas_38") or {}
    ela = mcas.get("ela") or []
    if len(enroll) < 2 or len(ppe) < 2:
        return ""
    e0, e1 = enroll[0], enroll[-1]
    p0, p1 = ppe[0], ppe[-1]
    if e0.get("v") is None or e1.get("v") is None or p0.get("v") is None or p1.get("v") is None:
        return ""
    bits = [
        f"Fall enrollment fell from {commify(e0['v'])} in {_sy_label(e0['y'])} "
        f"to {commify(e1['v'])} in {_sy_label(e1['y'])} (SRC-634-01).",
        f"Total expenditures per pupil rose from {usd_prose(p0['v'])} in FY {int(p0['y'])} "
        f"to {usd_prose(p1['v'])} in FY {int(p1['y'])} (SRC-634-02).",
    ]
    if len(ela) >= 2 and ela[0].get("v") is not None and ela[-1].get("v") is not None:
        math = mcas.get("math") or []
        math_bit = ""
        if len(math) >= 2 and math[0].get("v") is not None and math[-1].get("v") is not None:
            math_bit = (
                f" Math was {math[0]['v']:.0f}% in {int(math[0]['y'])} and "
                f"{math[-1]['v']:.0f}% in {int(math[-1]['y'])}."
            )
        bits.append(
            f"On the Next Generation MCAS, {ela[0]['v']:.0f}% of Boston grades 3-8 "
            f"students met or exceeded in ELA in {int(ela[0]['y'])} and "
            f"{ela[-1]['v']:.0f}% in {int(ela[-1]['y'])}.{math_bit} "
            f"The 2020 test was not administered (SRC-634-04)."
        )
    return " ".join(bits)


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
        "DL-34": ("school", 12, "Boston Latin School"),
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
        if tid == "DL-34":
            scissors = bps_enroll_ppe_lede(ledger)
            if scissors:
                trend_lede = scissors
            trend_unit = (
                "students (left), dollars per pupil (right), and MCAS "
                "meeting or exceeding (far right, percent)"
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
        "school": "This school versus the nearest by enrollment",
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
        "school": "Every school",
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
        "school": "School",
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
    spec = {
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
        "trend_src": (
            "DESE / E2C enrollment (SRC-634-01), district finance, Total Expenditures (SRC-634-02), and Next Generation MCAS grades 3-8 (SRC-634-04). The 2020 MCAS was not administered"
            if tid == "DL-34" else ""
        ),
        "trend_right": (
            {
                "label": "Total expenditures per pupil",
                "unit": "dollars per pupil",
                "format": "usd",
                "points": (
                    ((ledger.get("derived") or {}).get("secondary") or {})
                    .get("bps_finance_fy2025") or {}
                ).get("trend") or [],
            }
            if tid == "DL-34" else None
        ),
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
    if tid == "DL-34":
        mcas = ((ledger.get("derived") or {}).get("secondary") or {}).get("bps_mcas_38") or {}
        ela = mcas.get("ela") or []
        math = mcas.get("math") or []
        if ela:
            spec["trend_academic"] = [
                {
                    "label": "Grades 3-8 ELA meeting or exceeding",
                    "key": "ela",
                    "unit": "percent",
                    "points": ela,
                },
                {
                    "label": "Grades 3-8 math meeting or exceeding",
                    "key": "math",
                    "unit": "percent",
                    "points": math,
                },
            ]
    return spec


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
window.dlSuiteExtra = function (ctx) {
  var DL = ctx.DL, INK = ctx.INK, GOLD = ctx.GOLD, RUST = ctx.RUST;
  var fitScale = ctx.fitScale, dataLabels = ctx.dataLabels, seriesValues = ctx.seriesValues;
  var sec = (DL && DL.derived && DL.derived.secondary) || {};
  var charity = sec.charity_care || {};
  function money(v){
    if(v==null||v==='') return '';
    var n=Number(v), sign=n<0?'\u2212':'', a=Math.abs(n);
    if(a>=1e12) return sign+'$'+(a/1e12).toFixed(2)+' trillion';
    if(a>=1e9) return sign+'$'+(a/1e9).toFixed(2)+' billion';
    if(a>=1e6) return sign+'$'+(a/1e6).toFixed(2)+' million';
    return sign+'$'+Math.round(a).toLocaleString();
  }
  var crows = charity.rows || [];
  var ctr = charity.trend || {};
  var tel = document.getElementById('chCharityTrend');
  if (tel && window.Chart && (ctr.US || ctr.MA || ctr.FL)) {
    var series = [{key:'US',label:'United States',color:INK},{key:'MA',label:'Massachusetts',color:GOLD},{key:'FL',label:'Florida',color:RUST}];
    var years = {};
    series.forEach(function(s){ (ctr[s.key]||[]).forEach(function(p){ years[p.y]=1; }); });
    var labels = Object.keys(years).map(Number).sort(function(a,b){return a-b;});
    var tsets = series.map(function(s){
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
  var ctb = document.querySelector('#tblCharity tbody');
  if (ctb) {
    ctb.innerHTML = crows.map(function(r){
      return '<tr data-q="'+((r.name||'')+' '+(r.st||'')).toLowerCase()+'"><td class="m">'+(r.name||'')+'</td><td class="n">'+(r.v==null?'':Number(r.v).toFixed(2)+'%')+'</td><td class="n">'+money(r.charity)+'</td><td class="n">'+money(r.costs)+'</td><td class="n">'+(r.rank||'')+'</td></tr>';
    }).join('');
    var cf = document.getElementById('charityFind');
    var cc = document.getElementById('charityCount');
    function applyC(){
      var q = (cf && cf.value || '').toLowerCase();
      var shown = 0, n = 0;
      [].slice.call(ctb.querySelectorAll('tr')).forEach(function(tr){
        var ok = !q || (tr.getAttribute('data-q')||'').indexOf(q)>=0;
        tr.hidden = !ok; n++; if (ok) shown++;
      });
      if (cc) cc.textContent = q ? (shown+' of '+n) : (n+' rows');
    }
    if (cf) cf.addEventListener('input', applyC);
    applyC();
  }
  var drows = [];
  var dtb = document.querySelector('#tblDistricts tbody');
  var sel = document.getElementById('distState');
  function bindDistricts(){
    if (!dtb || !sel) return;
    var names = {};
    ((DL && DL.rows) || []).forEach(function(r){ if (r.st) names[r.st] = r.name || r.st; });
    var keys = Object.keys(drows.reduce(function(acc,r){ if (r.st) acc[r.st]=1; return acc; },{})).sort(function(a,b){
      return String(names[a]||a).localeCompare(names[b]||b);
    });
    sel.innerHTML = keys.map(function(s){
      return '<option value="'+s+'"'+(s==='MA'?' selected':'')+'>'+(names[s]||s)+'</option>';
    }).join('');
    function applyD(){
      var st = sel.value || 'MA';
      var q = (document.getElementById('distFind') && document.getElementById('distFind').value || '').toLowerCase();
      var shown = 0, n = 0;
      dtb.innerHTML = drows.filter(function(r){ return r.st===st; }).map(function(r){
        n++;
        var key = ((r.name||'')+' '+(r.st||'')).toLowerCase();
        var hide = q && key.indexOf(q)<0;
        if (!hide) shown++;
        return '<tr'+(hide?' hidden':'')+' data-q="'+key+'"><td class="m">'+(r.name||r.id||'')+'</td><td>'+(r.st||'')+'</td><td class="n">'+(r.v==null?'':Number(r.v).toLocaleString())+'</td></tr>';
      }).join('');
      var dc = document.getElementById('distCount');
      if (dc) dc.textContent = q ? (shown+' of '+n) : (n+' districts');
    }
    sel.addEventListener('change', applyD);
    var df = document.getElementById('distFind');
    if (df) df.addEventListener('input', applyD);
    applyD();
  }
  fetch('/340b/districts.json').then(function(r){ return r.json(); }).then(function(j){
    drows = (j && j.rows) || [];
    bindDistricts();
  }).catch(function(){ bindDistricts(); });
};
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
            noun = (
                "hospital" if app["id"] == "DL-10"
                else "school" if app["id"] == "DL-34"
                else "city or town"
            )
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
                or (spec.get("compare") or "") in ("dots", "map", "town", "hist", "finder")
            )
        )
        if has_compare:
            jump_links.append('<a href="#view-rank">' + esc(compare_h2) + "</a>")
        if has_trend:
            jump_lab = (
                "Enrollment, spending, and MCAS" if app["id"] == "DL-34" else "The trend"
            )
            jump_links.append('<a href="#view-trend">' + esc(jump_lab) + "</a>")
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
      <div class="srcline"><b>Source:</b> {esc(spec.get("trend_src") or fig1_src)}. <b>Unit:</b> {esc(spec.get("trend_unit") or unit or "see the register")}. <b>Calculation:</b> Pioneer Institute.</div>
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
        noun = (
            "hospital" if app["id"] == "DL-10"
            else "school" if app["id"] == "DL-34"
            else "city or town"
        )
        options = []
        for r in ledger.get("rows") or []:
            name = r.get("name")
            if name:
                options.append(f'<option value="{esc(name)}"></option>')
        datalist = (
            f'      <datalist id="proofFindList">{"".join(options)}</datalist>\n'
            if options else ""
        )
        finder_block = (
            '  <section id="view-proof" class="proof-find">\n'
            f"    <h2>Look up a {esc(noun)}</h2>\n"
            '    <div class="findrow">\n'
            f'      <label class="sel-lab" for="proofFind">Type a {esc(noun)}</label>\n'
            '      <input id="proofFind" type="search" list="proofFindList" placeholder="Type a name" autocomplete="off">\n'
            + datalist
            + "    </div>\n"
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
        extra_block = extra_tool_js(app, ledger)
        extra_tag = ("<script>\n" + extra_block + "</script>\n") if extra_block else ""
        js = """
<script>
/* DATA:BEGIN SLUG-data */
const DL=null;
/* DATA:END SLUG-data */
const CHART=CHART_JSON;
const INSIGHTS=INSIGHTS_JSON;
const MAP_VIEWS=MAP_VIEWS_JSON;
const FIND=FIND_JSON;
window.DL=DL;window.CHART=CHART;window.INSIGHTS=INSIGHTS;window.MAP_VIEWS=MAP_VIEWS;window.FIND=FIND;
</script>
EXTRA_BLOCK
""".replace("SLUG", slug).replace("CHART_JSON", json.dumps(spec, ensure_ascii=True)).replace("INSIGHTS_JSON", json.dumps(insights + later_insights, ensure_ascii=True)).replace("MAP_VIEWS_JSON", json.dumps(map_views, ensure_ascii=True)).replace("FIND_JSON", json.dumps(find_spec, ensure_ascii=True)).replace("EXTRA_BLOCK", extra_tag)

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
<script defer src="/assets/chart.umd.min.js"></script>
<script defer src="/assets/chart-theme.js"></script>
<script defer src="/assets/chart-labels.js"></script>
<script defer src="/assets/us-map.js"></script>
<script defer src="/assets/suite-runtime.js"></script>
<link rel="stylesheet" href="/assets/us-map.css">
<link rel="stylesheet" href="/assets/fonts.css">
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
<script defer src="/assets/ask-widget.js"></script>
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
