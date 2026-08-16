#!/usr/bin/env python3
"""Render house-style pages for every suite app from its ledger."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from insight_figures import insight_figures
from page_voice import census_place_names, display_lead, short_place_text, voice_for
from suite_common import ROOT, catalog_dashboards, commify, load_apps, ledger_path, paper_dateline

def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def src_rows(ledger):
    lines = []
    for sid, s in ledger.get("source_id_map", {}).items():
        lines.append(
            "<tr><td class=\"src\"><a href=\"" + esc(s.get("url", "#"))
            + "\" target=\"_blank\" rel=\"noopener\">" + esc(s.get("name", sid))
            + " (" + esc(sid) + ")</a></td><td>" + esc(s.get("cadence", ""))
            + "</td><td>" + esc(ledger.get("data_month_label") or "pending")
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


def kpi_html(kpis):
    blocks = []
    srcs = []
    for k in kpis:
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
    if srcs:
        blocks.append(
            "      <div class=\"cell kpi-src\">\n"
            "        <div class=\"csrc\">Source: " + esc("; ".join(srcs)) + "</div>\n"
            "      </div>"
        )
    return "\n".join(blocks)


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


def insight_html(insights):
    if not insights:
        return ""
    blocks = []
    for i, fig in enumerate(insights):
        span = " span2" if fig.get("span") == 2 or len(insights) == 1 else ""
        if fig.get("type") == "map" or fig.get("height") == "map":
            hclass = "plot plot-map"
        elif fig.get("height") == "mid":
            hclass = "plot-mid"
        elif fig.get("height") == "ranks":
            hclass = "plot-ranks"
        elif fig.get("span") == 2 or len(insights) == 1:
            hclass = "plot"
        else:
            hclass = "plot-sm"
        note = figure_limit(fig)
        note_html = (
            "      <div class=\"note\">" + esc(note) + "</div>\n" if note else ""
        )
        blocks.append(
            "    <div class=\"exhibit" + span + "\">\n"
            "      <div class=\"ex-head\"><span class=\"ex-n\">Figure " + str(i + 1) + "</span>\n"
            "        <span class=\"ex-t\">" + esc(fig["title"]) + "</span></div>\n"
            "      <div class=\"" + hclass + "\""
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


RELATED_PAIRS = {
    "DL-06": ["DL-07", "DL-09", "DL-08"],
    "DL-07": ["DL-06", "DL-08", "DL-09"],
    "DL-08": ["DL-07", "DL-06"],
    "DL-09": ["DL-06", "DL-07"],
    "DL-10": ["DL-11", "DL-12"],
    "DL-11": ["DL-10", "DL-12"],
    "DL-12": ["DL-10", "DL-11"],
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
TREND_INDEX_RATIO = 2.5


def trend_compare_mode(ledger):
    """Use percent-from-start when two series cannot share one level axis."""
    series = [(k, v) for k, v in (ledger.get("trend") or {}).items() if v]
    if len(series) < 2:
        return "level"
    maxs = []
    for _k, pts in series:
        vs = [abs(p["v"]) for p in pts if isinstance(p, dict) and p.get("v") is not None]
        if vs:
            maxs.append(max(vs))
    if len(maxs) < 2 or min(maxs) == 0:
        return "level"
    return "pct_from_start" if max(maxs) / min(maxs) >= TREND_INDEX_RATIO else "level"


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
    axis_unit = unit
    if fmt == "usd_millions":
        axis_unit = "chained 2017 dollars" if "chained" in ulow else "dollars"
    if geo == "state" or geo not in label.lower():
        title = label + " by " + geo
    else:
        title = label
    if n_rows and n_chart < n_rows and geo != "state":
        title += f" (largest {n_chart} of {n_rows})"
    lede = ""
    if geo == "state":
        lede = (
            "Every state and the District of Columbia on one map. "
            "Darker navy is a higher value. Use the region chips to fade "
            "the other states and to filter the table. Massachusetts has a "
            "gold outline; Florida a rust outline."
        )
    trend_keys = [k for k, v in (ledger.get("trend") or {}).items() if v]
    has_trend = bool(trend_keys)
    trend_mode = trend_compare_mode(ledger)
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
    if trend_mode == "pct_from_start":
        trend_title = "Change since the first year" + (", " + trend_named if trend_named else "")
        trend_lede = (
            "Each line is the percent change from its first year so "
            + (trend_lede_named or "the series")
            + " can be compared. Hover a point for the raw count."
        )
        trend_unit = "percent change from first year"
    elif set(trend_keys) >= {"US", "MA", "FL"}:
        trend_title = label + ", United States, Massachusetts, and Florida"
        trend_lede = ""
        trend_unit = unit
    elif set(trend_keys) >= {"US", "MA"}:
        trend_title = label + ", United States and Massachusetts"
        trend_lede = ""
        trend_unit = unit
    else:
        trend_title = label + " over time"
        trend_lede = ""
        trend_unit = unit
    compare_title = {
        "state": "Across the fifty states",
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
    }.get(geo, "Every row")
    col_name = {
        "state": "State",
        "hospital": "Hospital",
        "transit agency": "Agency",
        "city or town": "City or town",
        "department": "Department",
        "tax type": "Tax type",
        "legislator": "Legislator",
    }.get(geo, "Name")
    if tid == "DL-11":
        table_columns = [
            {"key": "name", "label": "State", "cls": "m"},
            {"key": "v", "label": "Sites", "align": "n", "fmt": "value"},
            {"key": "pharmacies", "label": "Pharmacies", "align": "n", "fmt": "value"},
            {"key": "rank", "label": "Rank", "align": "n"},
        ]
        table_lede = (
            "Filter by Census region or type a name. Sites are currently "
            "participating 340B IDs. Pharmacies are unique active contract "
            "pharmacy IDs in that state. Massachusetts is marked in gold; Florida in rust."
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
        table_lede = "Type a name to jump to a row."
        table_note = (
            "Amounts are the published CTHRU named-employee lines. Ranks are "
            "Pioneer calculations (derived). Year-over-year change is not on this file."
        )
    else:
        table_columns = [
            {"key": "name", "label": col_name, "cls": "m"},
            {"key": "v", "label": "Value", "align": "n", "fmt": "value"},
            {"key": "rank", "label": "Rank", "align": "n"},
            {"key": "yoy_pct", "label": "YoY", "align": "n", "kind": "yoy"},
        ]
        table_lede = (
            "Filter by Census region or type a name. Massachusetts is marked in gold; Florida in rust."
            if geo == "state"
            else "Type a name to jump to a row."
        )
        table_note = (
            "Ranks and year-over-year changes are Pioneer calculations (derived)."
        )
    if tid == "DL-11":
        compare_title = "Program growth"
        table_noun = "Every state"
    return {
        "geo": geo,
        "format": fmt,
        "highlight": highlight,
        "highlights": (["MA", "FL"] if geo == "state" else ([highlight] if highlight else [])),
        "n_chart": n_chart,
        "unit": unit,
        "axis_unit": axis_unit,
        "label": label,
        "title": title,
        "compare_title": compare_title,
        "lede": lede,
        "has_trend": has_trend,
        "table_noun": table_noun,
        "col_name": col_name,
        "table_columns": table_columns,
        "table_lede": table_lede,
        "table_note": table_note,
        "trend_mode": trend_mode,
        "trend_title": trend_title,
        "trend_lede": trend_lede,
        "trend_unit": trend_unit,
    }


def extra_tool_sections(app, ledger, n_fig, has_trend):
    """Stacked later tools that do not fit the single ranking table."""
    if app["id"] != "DL-11":
        return ""
    sec = ((ledger.get("derived") or {}).get("secondary") or {})
    charity = sec.get("charity_care") or {}
    legis = sec.get("legislative") or {}
    if not charity and not legis:
        return ""
    fig_c = n_fig + (2 if has_trend else 1) + 1
    fig_t = fig_c + 1
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
      <div class="ex-head"><span class="ex-n">Figure {fig_c}</span>
        <span class="ex-t" id="charityTitle">Hospital charity-care share of total costs, 2023</span></div>
      <div class="plot plot-ranks"><canvas id="chCharity"></canvas></div>
      <div class="srcline"><b>Source:</b> CMS Hospital Provider Cost Report PUF (SRC-611-02). Method citation: RAND TL-303 (SRC-611-04). <b>Unit:</b> percent of total costs.</div>
    </div>
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
    var cel=document.getElementById('chCharity');
    if(cel&&window.Chart&&crows.length){
      var plot=cel.parentNode;
      if(plot) plot.style.height=Math.max(280, Math.min(1200, crows.length*20+48))+'px';
      new Chart(cel,{type:'bar',
        data:{labels:crows.map(function(r){return r.st;}),
          datasets:[{data:crows.map(function(r){return r.v;}),
            backgroundColor:crows.map(function(r){
              if(r.st==='MA') return GOLD;
              if(r.st==='FL') return RUST;
              return BLUE;
            })}]},
        options:{indexAxis:'y',plugins:{legend:{display:false},
          tooltip:{callbacks:{label:function(c){return ' '+Number(c.parsed.x).toFixed(2)+'%';}}}},
          scales:{x:{ticks:{callback:function(v){return v+'%';}},title:{display:true,text:'percent of total costs'}},y:{}}},
        plugins:[dataLabels(function(v){return Number(v).toFixed(1)+'%';},'all')]
      });
    }
    var ctr=charity.trend||{};
    var tel=document.getElementById('chCharityTrend');
    if(tel&&window.Chart&&(ctr.US||ctr.MA||ctr.FL)){
      var series=[{key:'US',label:'United States',color:INK},{key:'MA',label:'Massachusetts',color:GOLD},{key:'FL',label:'Florida',color:RUST}];
      var years={};
      series.forEach(function(s){ (ctr[s.key]||[]).forEach(function(p){ years[p.y]=1; }); });
      var labels=Object.keys(years).map(Number).sort(function(a,b){return a-b;});
      new Chart(tel,{type:'line',
        data:{labels:labels,datasets:series.map(function(s){
          var by={}; (ctr[s.key]||[]).forEach(function(p){ by[p.y]=p.v; });
          return {label:s.label,data:labels.map(function(y){return by[y];}),borderColor:s.color,backgroundColor:'transparent',spanGaps:true};
        })},
        options:{plugins:{legend:{display:true},
          tooltip:{callbacks:{label:function(c){return ' '+c.dataset.label+': '+Number(c.parsed.y).toFixed(2)+'%';}}}},
          scales:{y:{ticks:{callback:function(v){return v+'%';}},title:{display:true,text:'percent of total costs'}}}},
        plugins:[dataLabels(function(v){return Number(v).toFixed(1)+'%';},'end')]
      });
    }
    var ctb=document.querySelector('#tblCharity tbody');
    if(ctb){
      ctb.innerHTML=crows.map(function(r){
        var cls=r.st==='MA'?' class="hl-ma"':(r.st==='FL'?' class="hl-fl"':'');
        return '<tr'+cls+' data-q="'+((r.name||'')+' '+(r.st||'')).toLowerCase()+'"><td class="m">'+(r.name||'')+'</td><td class="n">'+(r.v==null?'':Number(r.v).toFixed(2)+'%')+'</td><td class="n">'+money(r.charity)+'</td><td class="n">'+money(r.costs)+'</td><td class="n">'+(r.rank||'')+'</td></tr>';
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
    insights = insight_figures(app, ledger) if live else []
    has_trend = bool(spec.get("has_trend"))
    find_noun = (spec.get("geo") or "name").replace("_", " ")
    jump = ""
    compare_h2 = spec.get("compare_title") or spec.get("title") or "Compared"
    table_h2 = spec.get("table_noun") or "Every row"
    if live:
        jump_links = [
            '<a href="#view-rank">' + esc(compare_h2) + "</a>",
        ]
        if has_trend:
            jump_links.append('<a href="#view-trend">The trend</a>')
        jump_links.append('<a href="#view-table">' + esc(table_h2) + "</a>")
        if app["id"] == "DL-11":
            jump_links.append('<a href="#view-charity">Charity care</a>')
            jump_links.append('<a href="#view-districts">Legislative mapping</a>')
        jump = (
            '<nav class="jump" aria-label="On this page">'
            '<span class="onlab">On this page</span>'
            + "".join(jump_links)
            + "</nav>\n"
        )
    latest_section = ""
    n_fig = len(insights) if live else 0
    if live:
        latest_section = f"""
<section id="finding" style="margin-top:28px">
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
{insight_html(insights)}
  <section id="view-rank">
    <h2>{esc(compare_h2)}</h2>
{('    <div class="lede">' + esc(spec["lede"]) + "</div>\n") if spec.get("lede") else ""}{REGION_BAR if spec.get("geo") == "state" else ""}    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure {n_fig + 1}</span>
        <span class="ex-t" id="rankTitle">{esc(spec.get("title") or metric_label)}</span></div>
      <div class="plot {"plot-map" if spec.get("geo") == "state" else "plot-mid"}"{' id="chRank"' if spec.get("geo") == "state" else ""}>{"" if spec.get("geo") == "state" else '<canvas id="chRank"></canvas>'}</div>
      <div class="srcline"><b>Source:</b> see the register (the first source id). <b>Calculation:</b> Pioneer Institute (ranks only). <b>Unit:</b> {esc(unit or 'see the register')}.</div>
    </div>
  </section>
"""
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
    trend_section = ""
    if live and has_trend:
        trend_section = f"""
<section id="view-trend">
    <h2>{esc(spec.get("trend_title") or "The trend")}</h2>
{('    <div class="lede">' + esc(spec["trend_lede"]) + "</div>\n") if spec.get("trend_lede") else ""}    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure {n_fig + 2}</span>
        <span class="ex-t">{esc(spec.get("trend_title") or "Trend")}</span></div>
      <div class="plot"><canvas id="chTrend"></canvas></div>
      <div class="srcline"><b>Source:</b> see the register. <b>Unit:</b> {esc(spec.get("trend_unit") or unit or "see the register")}. <b>Calculation:</b> Pioneer Institute.</div>
    </div>
  </section>
"""
    table_section = ""
    if live:
        table_cols = spec.get("table_columns") or [
            {"key": "name", "label": spec.get("col_name") or "Name", "cls": "m"},
            {"key": "v", "label": "Value", "align": "n"},
            {"key": "rank", "label": "Rank", "align": "n"},
            {"key": "yoy_pct", "label": "YoY", "align": "n", "kind": "yoy"},
        ]
        th_html = "".join(
            f'<th{(" class=\"n\"" if c.get("align") == "n" else "")}>{esc(c.get("label") or "")}</th>'
            for c in table_cols
        )
        table_lede = esc(spec.get("table_lede") or "Type a name to jump to a row.")
        table_note = spec.get("table_note") or (
            "Ranks and year-over-year changes are Pioneer calculations (derived)."
        )
        table_section = f"""
<section id="view-table">
    <h2>{esc(spec.get("table_noun") or "Every row")}</h2>
    <div class="lede">{table_lede}</div>
{REGION_BAR if spec.get("geo") == "state" else ""}    <div class="findrow">
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
  </section>
"""
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
const FIND=FIND_JSON;

(function(){
  var q=new URLSearchParams(location.search);
  if(q.get('embed')==='1'||q.get('embed')==='true') document.body.classList.add('embed');
  var GOLD='#CCB26D', RUST='#C45C26', BLUE='#293C5C', INK='#1A1A1A', GREY='#58575A';
  function applyHash(){
    var h=(location.hash||'').replace(/^#/,'');
    if(!h) return;
    var el=document.getElementById(h)||document.getElementById('view-'+h);
    if(el) el.scrollIntoView({behavior:'smooth',block:'start'});
  }
  window.addEventListener('hashchange', applyHash);
  window.addEventListener('load', applyHash);
  var fmt=CHART.format||'number';
  var unit=CHART.unit||'';
  var axisUnit=CHART.axis_unit||unit;
  function hlList(){
    if(CHART.highlights && CHART.highlights.length) return CHART.highlights;
    if(CHART.geo==='state') return ['MA','FL'];
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
    if(isMA(r) || r.name==='Boston') return GOLD;
    if(isFL(r) && CHART.geo==='state') return RUST;
    return isHL(r)?GOLD:BLUE;
  }
  function hlClass(r){
    if(isFL(r) && CHART.geo==='state') return 'hl-fl';
    if(isHL(r)) return 'hl-ma';
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
  var rankChart=null;
  var chartRows=[];
  var applyFind=function(){};
  var writeQuery=function(){};
  function regionList(){
    return REGIONS[region]||null;
  }
  function filteredRows(){
    var list=regionList();
    if(!list) return rows.slice();
    return rows.filter(function(r){ return list.indexOf(r.st)>=0; });
  }
  function chartRowsFor(){
    var fr=filteredRows();
    if(CHART.geo!=='state'){
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
    plot.style.height=Math.max(280, Math.min(1200, n*20+48))+'px';
  }
  function rankTitleText(){
    var base=CHART.title||CHART.label||'';
    if(CHART.geo!=='state' || region==='all') return base;
    return (CHART.label||base)+' in '+REGION_NAMES[region];
  }
  function drawRankMap(){
    var el=document.getElementById('chRank');
    if(!el||!window.dlStateMap) return;
    chartRows=chartRowsFor();
    var titleEl=document.getElementById('rankTitle');
    if(titleEl) titleEl.textContent=rankTitleText();
    window.dlStateMap(el,{
      rows:rows,
      format:function(v){return fmtVal(v,true);},
      extra:function(r){return r.rank?('rank '+r.rank):'';},
      active:regionList(),
      onSelect:function(r){
        var tr=document.getElementById('row-'+r.st)||document.querySelector('#tblStates tr[data-st="'+r.st+'"]');
        if(tr) tr.scrollIntoView({behavior:'smooth',block:'center'});
      }
    });
  }
  function drawRank(){
    if(CHART.geo==='state'){ drawRankMap(); return; }
    var el=document.getElementById('chRank');
    if(!el||!window.Chart) return;
    chartRows=chartRowsFor();
    if(!chartRows.length) return;
    sizeRankPlot(chartRows.length);
    var titleEl=document.getElementById('rankTitle');
    if(titleEl) titleEl.textContent=rankTitleText();
    var payload={
      labels:chartRows.map(rowLabel),
      datasets:[{data:chartRows.map(function(r){return r.v;}),backgroundColor:chartRows.map(hlColor)}]
    };
    if(rankChart){
      rankChart.data=payload;
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
          x:{title:{display:!!axisUnit,text:axisUnit,color:GREY,font:{size:11}},
            ticks:{color:GREY,callback:function(v){return fmtVal(v,true);}},grid:{color:'rgba(34,34,34,.08)'},grace:'14%'},
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
  [].slice.call(document.querySelectorAll('.region-bar')).forEach(function(bar){
    if(CHART.geo!=='state') return;
    bar.hidden=false;
    [].slice.call(bar.querySelectorAll('[data-region]')).forEach(function(btn){
      btn.addEventListener('click', function(){ setRegion(btn.getAttribute('data-region')); });
    });
  });
  var startRegion=(q.get('region')||'').toLowerCase();
  if(startRegion && REGIONS.hasOwnProperty(startRegion)) region=startRegion;
  [].slice.call(document.querySelectorAll('[data-region]')).forEach(function(btn){
    btn.classList.toggle('on', btn.getAttribute('data-region')===region);
  });
  drawRank();
  var chTrend=document.getElementById('chTrend');
  var trend=(DL&&DL.trend)||{};
  var keys=Object.keys(trend).filter(function(k){return trend[k]&&trend[k].length;});
  if(chTrend && window.Chart && keys.length){
    var pretty={US:'United States',MA:'Massachusetts',FL:'Florida',Boston:'Boston'};
    var trendMode=CHART.trend_mode||'level';
    function trendColor(k){
      if(k==='MA') return GOLD;
      if(k==='FL') return RUST;
      if(k==='Boston') return BLUE;
      if(k==='US') return INK;
      return BLUE;
    }
    function fmtPct(v){
      if(v==null||v==='') return '';
      var n=Number(v), sign=n<0?'\u2212':(n>0?'+':'');
      return sign+Math.abs(n).toFixed(1)+'%';
    }
    var datasets=keys.map(function(k){
      var series=trend[k]||[];
      var first=null;
      series.forEach(function(p){ if(first==null && p && p.v!=null) first=p.v; });
      return {label:pretty[k]||k, key:k,
        data:series.map(function(p){
          var y=p.v;
          if(trendMode==='pct_from_start' && first) y=((p.v/first)-1)*100;
          return {x:p.m||String(p.y), y:y, raw:p.v};
        }),
        borderColor:trendColor(k),
        backgroundColor:'transparent',
        borderWidth:(k==='MA'||k==='FL')?2:1.75};
    });
    var yTitle=trendMode==='pct_from_start'?(CHART.trend_unit||'percent change from first year'):axisUnit;
    var yFmt=trendMode==='pct_from_start'?fmtPct:function(v){return fmtVal(v,true);};
    new Chart(chTrend,{type:'line',data:{datasets:datasets},
      options:{responsive:true,maintainAspectRatio:false,
        layout:{padding:{top:12,right:96}},
        plugins:{legend:{display:true,position:'top',align:'end'},
          tooltip:{callbacks:{label:function(c){
            if(trendMode==='pct_from_start'){
              var raw=c.raw&&c.raw.raw;
              return ' '+c.dataset.label+': '+fmtPct(c.parsed.y)+(raw==null?'':' \u00b7 '+fmtVal(raw));
            }
            var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' '+unit:'');
            return ' '+c.dataset.label+': '+fmtVal(c.parsed.y)+extra;
          }}}},
        scales:{
          x:{type:'category',ticks:{color:GREY,maxTicksLimit:12,
            callback:function(v){return String(this.getLabelForValue(v));}}},
          y:{title:{display:!!yTitle,text:yTitle,color:GREY,font:{size:11}},
            ticks:{color:GREY,callback:function(v){return yFmt(v);}},grid:{color:'rgba(34,34,34,.08)'}}
        }},
      plugins:[dataLabels(yFmt)]});
  }
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
        return lab.length>(maxLen||28)?lab.slice(0,(maxLen||28)-2)+'\u2026':lab;
      }};
  }
  function valTick(fmt){
    return {color:GREY,font:{size:11,family:'Roboto,sans-serif'},
      callback:function(v){return fmtInsight(fmt,v,true);}};
  }
  function valTitle(unit){
    return unit?{display:true,text:unit,color:GREY,font:{size:11}}:{display:false};
  }
  (INSIGHTS||[]).forEach(function(fig, i){
    var el=document.getElementById('chInsight'+i);
    if(!el||!fig) return;
    if(fig.type==='map' && window.dlStateMap && fig.rows){
      window.dlStateMap(el,{
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
    var scales=horiz?{
      x:{ticks:valTick(ifmt),title:valTitle(iunit),grid:{color:'rgba(34,34,34,.08)'},grace:'14%'},
      y:{ticks:catTick(32),grid:{display:false},border:{display:false}}
    }:{
      x:{ticks:Object.assign({},catTick(16),{color:GREY,autoSkip:fig.labels.length>12,maxTicksLimit:12}),
        grid:{display:false}},
      y:{ticks:valTick(ifmt),title:valTitle(iunit),grid:{color:'rgba(34,34,34,.08)'},border:{display:false},grace:'12%'}
    };
    var nLab=(fig.labels||[]).length;
    var opts={
      responsive:true,maintainAspectRatio:false,
      layout:{padding:{top:fig.type==='grouped'?36:(fig.type==='line'?16:8),right:fig.type==='line'?96:(horiz?72:16)}},
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
    if(fig.type==='line'){
      new Chart(el,{type:'line',
        data:{labels:fig.labels,datasets:fig.series.map(function(s){
          return {label:s.label||fig.title,data:s.data,borderColor:s.color||INK,
            backgroundColor:'transparent',spanGaps:true};
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
    new Chart(el,{type:'bar',
      data:{labels:fig.labels,datasets:[{data:s0.data,backgroundColor:s0.colors||BLUE}]},
      options:Object.assign({},opts,{indexAxis:'y'}),
      plugins:[lbl]});
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
      if(col.key==='v' || col.fmt==='value') return fmtVal(v);
      if(v==null||v==='') return '';
      return String(v).replace(/</g,'');
    }
    tb.innerHTML=rows.map(function(r){
      var cls=hlClass(r);
      var hl=cls?' class="'+cls+'"':'';
      var key=((r.name||'')+' '+(r.st||'')).toLowerCase();
      var cells=cols.map(function(c){
        var cls=c.cls||(c.align==='n'?'n':'');
        return '<td'+(cls?' class="'+cls+'"':'')+'>'+fmtCell(c,r)+'</td>';
      }).join('');
      return '<tr'+hl+(r.st?' id="row-'+r.st+'"':'')+' data-q="'+key.replace(/"/g,'')+'" data-st="'+(r.st||'')+'">'+cells+'</tr>';
    }).join('');
    var find=document.getElementById('tblFind');
    var countEl=document.getElementById('tblCount');
    applyFind=function(){
      var q=(find&&find.value||'').toLowerCase().replace(/^\\s+|\\s+$/g,'');
      var list=regionList();
      var n=0, shown=0, first=null;
      [].slice.call(tb.querySelectorAll('tr')).forEach(function(tr){
        var st=tr.getAttribute('data-st')||'';
        var inRegion=!list || list.indexOf(st)>=0;
        var ok=inRegion && (!q || (tr.getAttribute('data-q')||'').indexOf(q)>=0);
        tr.hidden=!ok;
        n++;
        if(ok){ shown++; if(!first) first=tr; }
      });
      var total=list?filteredRows().length:n;
      if(countEl){
        if(q) countEl.textContent=shown+' of '+total+(region!=='all'?' in '+REGION_NAMES[region]:'');
        else if(region!=='all') countEl.textContent=shown+' '+REGION_NAMES[region];
        else countEl.textContent=n+' '+(n===1?'row':'rows');
      }
      if(q && shown===1 && first) first.scrollIntoView({block:'nearest'});
    };
    var params=new URLSearchParams(location.search);
    var startQ=params.get('q')||params.get('st')||'';
    if(find && startQ && !find.value) find.value=startQ;
    writeQuery=function(){
      var qv=(find&&find.value||'').replace(/^\\s+|\\s+$/g,'');
      var params=new URLSearchParams();
      if(region && region!=='all') params.set('region', region);
      if(qv) params.set('q', qv);
      var qs=params.toString();
      history.replaceState(null,'',location.pathname+(qs?('?'+qs):'')+location.hash);
    };
    var card=document.getElementById('findCard');
    function norm(s){ return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\\b(city|town|the)\\b/g,' ').replace(/^\\s+|\\s+$/g,'').replace(/\\s+/g,' '); }
    function renderCard(row, extra){
      if(!card) return;
      extra=extra||{};
      var facts=extra.facts||[];
      var yoy=row && row.yoy_pct!=null ? ((row.yoy_pct>0?'+':'')+row.yoy_pct+'%') : (extra.yoy!=null?((extra.yoy>0?'+':'')+extra.yoy+'%'):'');
      var rank=(row && row.rank) || extra.rank;
      var n=(row && row.n) || extra.n;
      var val=extra.value || (row?fmtVal(row.v):'');
      var name=extra.name || (row && row.name) || '';
      var metric=(FIND&&FIND.metric)||'Value';
      card.hidden=false;
      card.innerHTML='<div class="fc-k">'+metric+'</div>'+
        '<h3>'+name.replace(/</g,'')+'</h3>'+
        '<div class="fc-val">'+val+'</div>'+
        (rank?'<div class="fc-rank">Rank '+rank+(n?(' of '+n):'')+(yoy?(' \\u00b7 '+yoy):'')+'</div>':'')+
        (facts.length?'<ul class="fc-facts">'+facts.map(function(f){return '<li>'+String(f).replace(/</g,'')+'</li>';}).join('')+'</ul>':'')+
        '<div class="fc-src">Share this row: add ?q='+encodeURIComponent(name)+' to the URL.</div>';
    }
    function hideCard(){ if(card){ card.hidden=true; card.innerHTML=''; } }
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
        rows.forEach(function(r){
          var rk=((r.name||'')+' '+(r.st||'')).toLowerCase();
          if(rk===key) row=r;
        });
        renderCard(row, extra);
      } else if(shown.length===1){
        var key2=(shown[0].getAttribute('data-q')||'');
        var row2=null;
        rows.forEach(function(r){
          var rk=((r.name||'')+' '+(r.st||'')).toLowerCase();
          if(rk===key2) row2=r;
        });
        var extra2=row2?matchCard(row2.name):null;
        renderCard(row2, extra2||{});
      } else {
        hideCard();
      }
    };
    if(find) find.addEventListener('input', function(){ applyFind(); writeQuery(); });
    applyFind();
  }
EXTRA_TOOL_JS})();
</script>
""".replace("SLUG", slug).replace("CHART_JSON", json.dumps(spec, ensure_ascii=True)).replace("INSIGHTS_JSON", json.dumps(insights, ensure_ascii=True)).replace("FIND_JSON", json.dumps(find_spec, ensure_ascii=True)).replace("EXTRA_TOOL_JS", extra_tool_js(app, ledger))
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
{trend_section}
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
      <p class="body-p">It replaces these Tableau workbooks: {replaces}.</p>
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
        if ledger.get("status") == "live" and not insight_figures(app, ledger):
            missing.append(app["id"])
    if missing:
        sys.exit("FATAL: no insight figures for " + ", ".join(missing))
    print(f"rendered {n} suite pages")


if __name__ == "__main__":
    main()
