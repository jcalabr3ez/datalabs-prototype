#!/usr/bin/env python3
"""Render house-style pages for every suite app from its ledger."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_common import LEDGER_DIR, ROOT, load_apps, ledger_path

def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def src_rows(ledger):
    lines = []
    for sid, s in ledger.get("source_id_map", {}).items():
        lines.append(
            "<tr><td class=\"src\"><a href=\"" + esc(s.get("url", "#"))
            + "\" target=\"_blank\" rel=\"noopener\">" + esc(s.get("name", sid))
            + " (" + esc(sid) + ")</a></td><td>" + esc(s.get("cadence", ""))
            + "</td><td>" + esc(s.get("supports", ""))
            + "</td><td>" + esc(ledger.get("data_month_label") or "pending")
            + "</td><td>" + esc(s.get("cadence", "See publisher"))
            + "</td></tr>"
        )
    return "\n          ".join(lines)


def kpi_html(kpis):
    blocks = []
    for k in kpis:
        blocks.append(
            "      <div class=\"cell\">\n"
            "        <div class=\"cl\">" + esc(k["label"]) + "</div>\n"
            "        <div class=\"cv\">" + esc(k["value"]) + "</div>\n"
            "        <div class=\"cd\">" + k["detail"] + "</div>\n"
            "        <div class=\"cd\" style=\"margin-top:8px\"><b>Why it matters:</b> "
            + esc(k["why"]) + "</div>\n"
            "        <div class=\"csrc\">Source: " + esc(k["src"]) + "</div>\n"
            "      </div>"
        )
    return "\n".join(blocks)


def replaces_list(app, ledger):
    items = ledger.get("replaces") or app.get("replaces") or []
    return ", ".join(items)


def page_html(app, ledger):
    live = ledger.get("status") == "live"
    title = app["title"]
    slug = app["slug"]
    vertical = app["vertical"]
    topic = app["group"]
    standfirst = app["q"]
    as_of_label = ledger.get("data_month_label") or "pending"
    revised = ledger.get("page", {}).get("revised", "")
    version = ledger.get("page", {}).get("version", "0.0")
    metric_label = ledger.get("metric_label") or "Figure"
    unit = ledger.get("unit") or ""
    lead = ledger.get("lead") or (
        "This application is in build. The source register below is the inventory. "
        "Figures will appear here once they are recomputed from those sources."
    )
    proto = (
        "<b>A living data tool, not a static report.</b> Figures trace to source "
        "in the register below, with vintage and next scheduled release. For all "
        "corrections please e-mail "
        "<a href=\"mailto:datalabs@pioneerinstitute.org\">datalabs@pioneerinstitute.org</a>."
        if live else
        "<b>In build.</b> Scope and sources are locked. Figures are not invented "
        "to fill the page. A later refresh will compile the ledger from the "
        "register below. Corrections: "
        "<a href=\"mailto:datalabs@pioneerinstitute.org\">datalabs@pioneerinstitute.org</a>."
    )
    heritage = esc(app.get("heritage") or "")
    replaces = esc(replaces_list(app, ledger))
    nsrc = len(ledger.get("source_id_map") or {})
    src_word = "source" if nsrc == 1 else "sources"
    kpis = kpi_html(ledger.get("kpis") or [])
    has_trend = bool(ledger.get("trend"))
    toggle = ""
    if live:
        toggle = """
<div class="toggle" role="tablist" aria-label="Choose a view">
  <button id="btn-latest" class="on" onclick="showView('latest')">Latest<span class="who">The current ranking</span></button>
  <button id="btn-trend" onclick="showView('trend')">Trend<span class="who">How the series has moved</span></button>
  <button id="btn-table" onclick="showView('table')">Table<span class="who">Every jurisdiction</span></button>
</div>
"""
    latest_section = ""
    if live:
        latest_section = f"""
<div id="view-latest">
  <section style="margin-top:30px">
    <h2>What are the key takeaways?</h2>
    <p class="lede">
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
  <section id="view-rank">
    <h2>How do the states compare?</h2>
    <div class="lede">{esc(metric_label)}. Massachusetts is marked in gold.</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure 1</span>
        <span class="ex-t">{esc(metric_label)} by state</span></div>
      <div class="plot plot-ranks"><canvas id="chRank"></canvas></div>
      <div class="note">Ranks are Pioneer calculations from the published source file (derived). The source line names the file.</div>
      <div class="srcline"><b>Source:</b> see the register (the first source id). <b>Calculation:</b> Pioneer Institute (ranks only).</div>
    </div>
  </section>
</div>
"""
    else:
        latest_section = f"""
<section style="margin-top:30px">
  <h2>What this application will cover</h2>
  <p class="lede">{esc(app['scope'])}</p>
  <p class="body-p">{esc(app['exclusions'])}</p>
  <p class="body-p">It replaces these Tableau workbooks: {replaces}.</p>
</section>
"""
    trend_section = ""
    if live:
        trend_note = (
            "Select a series the ledger carries. Empty months are omitted."
            if has_trend else
            "A multi-year trend is not in this first ledger. The ranking above is the current file."
        )
        trend_section = f"""
<div id="view-trend" hidden>
  <section style="margin-top:30px">
    <h2>How has the series moved?</h2>
    <div class="lede">{trend_note}</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure 2</span>
        <span class="ex-t">Trend</span></div>
      <div class="plot"><canvas id="chTrend"></canvas></div>
      <div class="srcline"><b>Source:</b> see the register. <b>Calculation:</b> Pioneer Institute.</div>
    </div>
  </section>
</div>
"""
    table_section = ""
    if live:
        table_section = f"""
<div id="view-table" hidden>
  <section style="margin-top:30px">
    <h2>Every jurisdiction</h2>
    <div class="lede">{esc(metric_label)}{', ' + esc(unit) if unit else ''}.</div>
    <div class="scroll">
      <table id="tblStates">
        <thead><tr><th>Jurisdiction</th><th class="n">Value</th><th class="n">Rank</th><th class="n">YoY</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="srcline"><b>Source:</b> see the register. Ranks and year-over-year changes are Pioneer calculations (derived).</div>
  </section>
</div>
"""
    js = ""
    if live:
        js = """
<script>
/* DATA:BEGIN SLUG-data */
const DL=null;
/* DATA:END SLUG-data */

(function(){
  var q=new URLSearchParams(location.search);
  if(q.get('embed')==='1'||q.get('embed')==='true') document.body.classList.add('embed');
  var GOLD='#CCB26D', BLUE='#293C5C', INK='#222222', GREY='#666666';
  function showView(id){
    ['latest','trend','table'].forEach(function(v){
      var el=document.getElementById('view-'+v);
      if(el) el.hidden = (v!==id);
      var b=document.getElementById('btn-'+v);
      if(b) b.classList.toggle('on', v===id);
    });
    if(location.hash!=='#view-'+id) history.replaceState(null,'','#view-'+id);
  }
  window.showView=showView;
  function applyHash(){
    var h=(location.hash||'').replace('#view-','');
    if(h==='trend'||h==='table'||h==='latest') showView(h);
  }
  window.addEventListener('hashchange', applyHash);
  applyHash();
  var rows=(DL&&DL.rows)||[];
  var chRank=document.getElementById('chRank');
  if(chRank && rows.length && window.Chart){
    var labels=rows.map(function(r){return r.st;});
    var data=rows.map(function(r){return r.v;});
    var colors=rows.map(function(r){return r.st==='MA'?GOLD:BLUE;});
    new Chart(chRank,{type:'bar',data:{labels:labels,datasets:[{data:data,backgroundColor:colors,barPercentage:.72}]},
      options:{indexAxis:'y',plugins:{legend:{display:false}},
        scales:{x:{ticks:{color:GREY},grid:{color:'#EEF1F4'}},y:{ticks:{color:INK,font:{size:10}},grid:{display:false}}}}});
  }
  var chTrend=document.getElementById('chTrend');
  var trend=(DL&&DL.trend)||{};
  if(chTrend && window.Chart){
    var keys=Object.keys(trend);
    var datasets=keys.map(function(k,i){
      var series=trend[k]||[];
      return {label:k,data:series.map(function(p){return {x:p.m||String(p.y),y:p.v};}),
        borderColor:k==='MA'?GOLD:BLUE,backgroundColor:'transparent',tension:.15,pointRadius:0};
    });
    if(datasets.length){
      new Chart(chTrend,{type:'line',data:{datasets:datasets},
        options:{plugins:{legend:{display:true}},
          scales:{x:{type:'category',ticks:{color:GREY,maxTicksLimit:12}},
                   y:{ticks:{color:GREY},grid:{color:'#EEF1F4'}}}}});
    }
  }
  var tb=document.querySelector('#tblStates tbody');
  if(tb){
    tb.innerHTML=rows.map(function(r){
      var yoy=(r.yoy_pct==null?'':(r.yoy_pct>0?'+':'')+r.yoy_pct+'%');
      var hl=r.st==='MA'?' class="hl-ma"':'';
      var val=(typeof r.v==='number' && Math.abs(r.v)>=1000)?r.v.toLocaleString():r.v;
      return '<tr'+hl+'><td class="m">'+r.name+'</td><td class="n">'+val+'</td><td class="n">'+(r.rank||'')+'</td><td class="n">'+yoy+'</td></tr>';
    }).join('');
  }
})();
</script>
""".replace("SLUG", slug)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} | Pioneer Institute | DataLabs</title>
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="{esc(standfirst)}">
<link rel="canonical" href="https://datalabsai.netlify.app/{esc(slug)}/">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Pioneer DataLabs">
<meta property="og:title" content="{esc(title)} | Pioneer Institute">
<meta property="og:description" content="{esc(standfirst)}">
<meta property="og:url" content="https://datalabsai.netlify.app/{esc(slug)}/">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Bodoni:ital,wght@0,400..700;1,400..700&family=Roboto:wght@300..900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/datalabs.css">
<style>
  :root{{ --bleed:clamp(18px,2.6vw,48px); }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{width:100%}}
  body{{background:#fff;color:var(--ink);font:15px/1.6 var(--sans);-webkit-font-smoothing:antialiased;padding:0}}
  a{{color:var(--navy)}}
  a:hover{{color:var(--gold)}}
  input:focus-visible,button:focus-visible,a:focus-visible,summary:focus-visible,select:focus-visible{{outline:2px solid var(--gold);outline-offset:3px}}
  .wrap{{width:100%;max-width:none;margin:0 auto;background:#fff;border:none;padding:0 var(--bleed)}}
  .wrap>*:not(.sitebar):not(header):not(.proto):not(footer){{max-width:1120px;margin-left:auto;margin-right:auto}}
  .sitebar{{display:flex;align-items:center;justify-content:space-between;gap:18px;background:var(--bar);padding:16px var(--bleed);margin:0 calc(-1 * var(--bleed))}}
  .sitebar img{{height:24px;width:auto;display:block}}
  .sitebar .sbleft{{display:flex;align-items:center;gap:16px}}
  .sitebar .backlink{{font:600 12px/1 var(--sans);color:#C9D2E0;text-decoration:none;border-left:1px solid rgba(255,255,255,.25);padding-left:16px;white-space:nowrap}}
  .sitebar .backlink:hover{{color:var(--goldlt)}}
  .sitebar .tag{{font:600 11px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:#C9D2E0}}
  .sitebar .tag b{{color:var(--goldlt);font-weight:700}}
  @media(max-width:520px){{.sitebar .tag{{display:none}}}}
  header{{position:relative;overflow:hidden;background:linear-gradient(178deg,var(--bar) 0%,var(--hero2) 70%,var(--bar) 100%);margin:0 calc(-1 * var(--bleed));padding:34px var(--bleed) 30px}}
  .dots{{position:absolute;inset:0;opacity:.35;pointer-events:none;background-image:radial-gradient(rgba(139,160,190,.5) 1.1px, transparent 1.1px);background-size:26px 26px}}
  header>*:not(.dots){{position:relative}}
  .org{{font:700 11.5px/1 var(--sans);letter-spacing:.18em;text-transform:uppercase;color:var(--goldlt);margin-bottom:14px}}
  .org .sub{{color:#8DA0B5}}
  h1{{font:700 clamp(29px,3.8vw,44px)/1.1 var(--serif);color:#fff;letter-spacing:-.015em}}
  .standfirst{{font:400 15.5px/1.6 var(--sans);color:#AEBDD2;margin-top:12px;max-width:62em}}
  .dateline{{display:flex;flex-wrap:wrap;margin-top:20px;font:500 10.5px/2 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:#8DA0B5}}
  .dateline span{{padding:0 18px;border-left:1px solid rgba(174,189,210,.3)}}
  .dateline span:first-child{{padding-left:0;border-left:none}}
  .dateline b{{color:var(--goldlt);font-weight:500}}
  .proto{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--hero3);margin:0 calc(-1 * var(--bleed)) 30px;padding:12px var(--bleed);border-top:1px solid rgba(255,255,255,.08)}}
  .proto-tag{{font:800 10px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--goldlt);border:1px solid var(--goldlt);border-radius:3px;padding:4px 9px;flex-shrink:0}}
  .proto-txt{{font:400 13px/1.55 var(--sans);color:#AEBDD2;flex:1;min-width:260px}}
  .proto-txt b{{color:#fff;font-weight:600}}
  .proto-txt a{{color:inherit;text-decoration:underline}}
  .toggle{{display:flex;flex-wrap:wrap;border-bottom:1px solid var(--rule);width:min(1120px,100%);margin-top:22px}}
  .toggle button{{background:none;border:none;text-align:left;cursor:pointer;padding:10px 18px 13px 0;margin-right:14px;margin-bottom:-1px;font:700 13.5px/1.3 var(--sans);color:var(--grey);border-bottom:2px solid transparent}}
  .toggle button.on{{color:var(--ink);border-bottom-color:var(--gold)}}
  .toggle .who{{display:block;font:400 11px/1.35 var(--sans);margin-top:3px;color:var(--faint)}}
  section{{margin-top:56px}}
  h2{{font:500 clamp(22px,2.6vw,28px)/1.25 var(--serif);letter-spacing:-.015em;color:var(--ink);margin-bottom:6px}}
  .lede{{font-size:14.5px;color:var(--grey);margin:10px 0 22px;max-width:72em}}
  .body-p{{font-size:15px;margin-bottom:14px;max-width:72em}}
  .strip{{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}}
  .cell{{padding:22px 20px 22px 0;border-right:1px solid var(--rule-lt)}}
  .cell:last-child{{border-right:0;padding-right:0}}
  .cl{{font:600 10.5px/1.5 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--grey);margin-bottom:10px;min-height:30px}}
  .cv{{font:600 27px/1 var(--serif);color:var(--ink);font-variant-numeric:tabular-nums lining-nums}}
  .cd{{font-size:11.5px;color:var(--g1);margin-top:9px;line-height:1.5}}
  .csrc{{font-size:10px;color:var(--faint);margin-top:9px;padding-top:7px;border-top:1px dotted var(--rule-lt);line-height:1.45}}
  @media(max-width:900px){{.strip{{grid-template-columns:1fr}}.cell{{border-right:0;border-bottom:1px solid var(--rule-lt)}}}}
  .metrics .cell{{text-align:center;padding:20px 16px}}
  .exhibit{{margin-top:30px}}
  .ex-head{{display:flex;gap:14px;align-items:baseline;border-bottom:1px solid var(--rule-dk);padding-bottom:7px;margin-bottom:16px}}
  .ex-n{{font:500 10px/1.5 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--gold);white-space:nowrap}}
  .ex-t{{font:600 14.5px/1.4 var(--sans);flex:1}}
  .plot{{height:clamp(300px,34vh,460px)}}
  .plot-ranks{{height:clamp(720px,92vh,1180px)}}
  .note{{font-size:11.5px;line-height:1.7;color:var(--grey);margin-top:13px;padding-top:10px;border-top:1px solid var(--rule-lt)}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:20px;font-variant-numeric:tabular-nums lining-nums}}
  th{{font:600 10.5px/1.5 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--grey);text-align:left;padding:0 14px 8px 0;border-bottom:1px solid var(--rule-dk);vertical-align:bottom}}
  td{{padding:11px 14px 11px 0;border-bottom:1px solid var(--rule);vertical-align:top}}
  th.n,td.n{{text-align:right;padding-right:0;white-space:nowrap}}
  td.m{{font-weight:600}}
  tr.hl-ma td{{background:var(--wash)}}
  .srcline{{font-size:11px;color:var(--faint);margin-top:12px;line-height:1.55}}
  .srcline a{{color:var(--grey);text-decoration:none;border-bottom:1px solid var(--rule)}}
  .subhead{{font-size:14.5px;line-height:1.6;color:var(--grey);margin:10px 0 22px;max-width:72em}}
  details.srcfold,details.simplify{{border:1px solid var(--rule);border-radius:4px;background:#fff;margin-top:14px}}
  details.srcfold>summary,details.simplify summary{{cursor:pointer;list-style:none;padding:14px 18px;display:flex;align-items:baseline;gap:14px;font:600 14.5px/1.4 var(--sans);color:var(--ink)}}
  details.srcfold>summary::-webkit-details-marker,details.simplify summary::-webkit-details-marker{{display:none}}
  details.srcfold>summary:after,details.simplify summary:after{{content:none}}
  details.srcfold .fold-body,details.simplify .dt-body{{padding:14px 18px 16px}}
  .car{{color:var(--gold);font-size:11px}}
  table.reg{{font-size:11.5px;line-height:1.55}}
  table.reg td{{padding:9px 14px 9px 0;color:var(--g1)}}
  table.reg td.src{{color:var(--ink);font-weight:600}}
  table.reg td.src a{{color:var(--navy);text-decoration:none;border-bottom:1px solid var(--rule)}}
  .scroll{{overflow-x:auto;max-width:100%}}
  [hidden]{{display:none !important}}
  footer{{margin:96px calc(-1 * var(--bleed)) 0;background:var(--bar);border-top:3px solid var(--gold);padding:32px var(--bleed) 26px;font-size:12.5px;line-height:1.8;color:#C9D2E0}}
  footer b{{color:#fff}}
  footer a{{color:#fff;text-decoration:none;border-bottom:1px solid rgba(255,255,255,.25)}}
  .disclaimer{{margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,.1);color:#8DA0B5;line-height:1.75;font-size:12px}}
  .fbrand{{margin-bottom:16px;font-size:12px;line-height:1.7;color:#8DA0B5}}
  .fbrand .pi{{font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#fff}}
  .frow{{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-top:8px;color:#8DA0B5;font-size:12px}}
  body.embed .sitebar,body.embed footer .fbrand{{display:none}}
</style>
</head>
<body>
<div class="wrap">
<div class="sitebar">
  <div class="sbleft">
    <a href="https://pioneerinstitute.org" aria-label="Pioneer Institute"><img src="https://pioneerinstitute.org/wp-content/uploads/2025/11/Pioneer_Negative_SVG.svg" alt="Pioneer Institute"></a>
    <a class="backlink" href="/">&#8592; All of DataLabs</a>
  </div>
  <span class="tag"><b>DataLabs</b> &nbsp;&middot;&nbsp; {esc(title)}</span>
</div>
<header>
  <div class="dots" aria-hidden="true"></div>
  <div class="org">{esc(vertical)} <span class="sub">/ {esc(topic)}{(' &middot; ' + heritage) if heritage else ''}</span></div>
  <h1>{esc(title)}</h1>
  <div class="standfirst">{esc(standfirst)}</div>
  <div class="dateline">
<!-- DATA:BEGIN {slug}-dateline -->
    <span>Data through <b>{esc(as_of_label)}</b></span>
    <span>Revised <b>{esc(revised)}</b></span>
    <span>Version <b>{esc(version)}</b></span>
<!-- DATA:END {slug}-dateline -->
  </div>
</header>
<div class="proto"><span class="proto-tag">Prototype</span><span class="proto-txt">{proto}</span></div>
{toggle}
{latest_section}
{trend_section}
{table_section}
<section id="sources">
  <h2>Data Sources</h2>
  <div class="subhead">Every figure on this page traces to a source below. Derived measures are Pioneer Institute calculations, disclosed as such where they are used.</div>
  <details class="srcfold">
    <summary><span class="car">&#9654;</span><span class="name">Source register: cadence, vintage, and next release</span></summary>
    <div class="fold-body">
      <div class="scroll"><table class="reg">
        <thead><tr><th>Source</th><th>Publisher cadence</th><th>What it supports</th><th>Data vintage</th><th>Next release</th></tr></thead>
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
      <p class="body-p">It replaces these Tableau workbooks: {replaces}. Those URLs stay in the catalog until this page covers the same substance.</p>
    </div>
  </details>
</section>
<footer>
  <div class="fbrand"><span class="pi">Pioneer Institute</span> &nbsp;&middot;&nbsp; 185 Devonshire Street, Suite 1101, Boston, MA 02110 &nbsp;&middot;&nbsp; <a href="https://pioneerinstitute.org">pioneerinstitute.org</a></div>
  <div class="frow">
<!-- DATA:BEGIN {slug}-footer-meta -->
    <div>{esc(title)} &middot; Version {esc(version)} &middot; Data through {esc(as_of_label)} &middot; Revised {esc(revised)}</div>
<!-- DATA:END {slug}-footer-meta -->
    <div>{nsrc} {src_word} in the register</div>
  </div>
  <div class="disclaimer">
    <div><b>About this tool.</b> {esc(title)} is a Pioneer Institute DataLabs research tool. {heritage + '.' if heritage else ''} Corrections and data refreshes are logged. It is a living data tool, not a static report.</div>
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
    apps = load_apps()
    n = 0
    for app in apps:
        path = ledger_path(app["id"])
        if not path.exists():
            sys.exit(f"FATAL: missing ledger {path}")
        ledger = json.loads(path.read_text(encoding="utf-8"))
        dest = ROOT / app["slug"] / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page_html(app, ledger), encoding="utf-8")
        n += 1
        print(f"render {app['id']} -> {dest.relative_to(ROOT)}")
    print(f"rendered {n} suite pages")


if __name__ == "__main__":
    main()
