#!/usr/bin/env python3
"""Render house-style pages for every suite app from its ledger."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from insight_figures import insight_figures
from suite_common import ROOT, load_apps, ledger_path

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


def insight_html(insights):
    if not insights:
        return ""
    letters = "ABCDEFGH"
    blocks = []
    for i, fig in enumerate(insights):
        letter = letters[i] if i < len(letters) else str(i + 1)
        span = " span2" if fig.get("span") == 2 or len(insights) == 1 else ""
        if fig.get("height") == "mid":
            hclass = "plot-mid"
        elif fig.get("span") == 2 or len(insights) == 1:
            hclass = "plot"
        else:
            hclass = "plot-sm"
        blocks.append(
            "    <div class=\"exhibit" + span + "\">\n"
            "      <div class=\"ex-head\"><span class=\"ex-n\">Figure " + letter + "</span>\n"
            "        <span class=\"ex-t\">" + esc(fig["title"]) + "</span></div>\n"
            "      <div class=\"lede\">" + esc(fig["lede"]) + "</div>\n"
            "      <div class=\"" + hclass + "\"><canvas id=\"chInsight" + str(i) + "\"></canvas></div>\n"
            "      <div class=\"note\">" + esc(fig["note"]) + "</div>\n"
            "      <div class=\"srcline\"><b>Source:</b> " + esc(fig.get("src") or "see the register")
            + ". <b>Unit:</b> " + esc(fig.get("unit") or "see the register") + ".</div>\n"
            "    </div>"
        )
    return (
        "  <section id=\"insights\">\n"
        "    <h2>A closer look</h2>\n"
        "    <p class=\"lede\">More published series on this page.</p>\n"
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
    "DL-10": ["DL-12"],
    "DL-12": ["DL-10"],
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
    "DL-30": ["DL-28", "DL-27"],
    "DL-31": ["DL-26"],
}

FLAGSHIP_LINKS = {
    "DL-01": {"title": "State Tax Atlas", "slug": "tax-atlas"},
    "DL-03": {"title": "Transportation & MBTA", "slug": "mbta"},
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
        '    <p class="lede">Other DataLabs tools on the same desk.</p>\n'
        '    <div class="related">' + links + "</div>\n"
        "  </section>\n"
    )


def chart_spec(app, ledger):
    """Titles, units, and highlight for the shared suite charts."""
    tid = app["id"]
    unit = ledger.get("unit") or ""
    label = ledger.get("metric_label") or "Figure"
    n_rows = len(ledger.get("rows") or [])
    named = {
        "DL-10": ("hospital", 12, None),
        "DL-22": ("transit agency", 12, "Massachusetts Bay Transportation Authority"),
        "DL-25": ("city or town", 12, "Boston city"),
        "DL-26": ("city or town", 12, "Boston city"),
        "DL-27": ("department", 12, "Boston Police Department"),
        "DL-28": ("tax type", n_rows or 12, "Total Taxes"),
        "DL-30": ("department", 12, None),
    }
    if tid in named:
        geo, n_chart, highlight = named[tid]
        n_chart = min(n_chart, n_rows) if n_rows else n_chart
    else:
        geo, n_chart, highlight = "state", min(12, n_rows) if n_rows else 12, "MA"
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
    if n_rows and n_chart < n_rows:
        title += f" (largest {n_chart} of {n_rows})"
    lede = label + "."
    if unit and unit.lower() not in label.lower():
        lede += " Unit: " + unit + "."
    if highlight == "MA":
        lede += " Massachusetts is marked in gold."
    elif highlight:
        lede += " The highlighted bar is " + highlight + "."
    trend_keys = [k for k, v in (ledger.get("trend") or {}).items() if v]
    has_trend = bool(trend_keys)
    table_noun = {
        "state": "Every state",
        "hospital": "Every hospital",
        "transit agency": "Every transit agency",
        "city or town": "Every city or town",
        "department": "Every department",
        "tax type": "Every tax type",
    }.get(geo, "Every row")
    col_name = {
        "state": "State",
        "hospital": "Hospital",
        "transit agency": "Agency",
        "city or town": "City or town",
        "department": "Department",
        "tax type": "Tax type",
    }.get(geo, "Name")
    return {
        "geo": geo,
        "format": fmt,
        "highlight": highlight,
        "n_chart": n_chart,
        "unit": unit,
        "axis_unit": axis_unit,
        "label": label,
        "title": title,
        "lede": lede,
        "has_trend": has_trend,
        "table_noun": table_noun,
        "col_name": col_name,
        "trend_title": (
            label + ", United States and Massachusetts"
            if set(trend_keys) >= {"US", "MA"}
            else label + " over time"
        ),
    }


def page_html(app, ledger, apps=None):
    live = ledger.get("status") == "live"
    title = app["title"]
    slug = app["slug"]
    vertical = app["vertical"]
    topic = app["group"]
    standfirst = app["q"]
    apps = apps or []
    as_of_label = ledger.get("data_month_label") or "pending"
    revised = ledger.get("page", {}).get("revised", "")
    version = ledger.get("page", {}).get("version", "0.0")
    metric_label = ledger.get("metric_label") or "Figure"
    unit = ledger.get("unit") or ""
    lead = ledger.get("lead") or (
        "This application is in build. The source register below is the inventory. "
        "Figures will appear here once they are recomputed from those sources."
    )
    proto_tag = "In build" if not live else "DataLabs"
    proto = (
        "<b>A living data tool.</b> Figures trace to the register below, with vintage "
        "and next scheduled release. For corrections e-mail "
        "<a href=\"mailto:datalabs@pioneerinstitute.org\">datalabs@pioneerinstitute.org</a>."
        if live else
        "<b>Sources are locked. Figures are not published yet.</b> A later refresh "
        "will compile the ledger from the register below. Corrections: "
        "<a href=\"mailto:datalabs@pioneerinstitute.org\">datalabs@pioneerinstitute.org</a>."
    )
    replaces = esc(replaces_list(app, ledger))
    nsrc = len(ledger.get("source_id_map") or {})
    src_word = "source" if nsrc == 1 else "sources"
    kpis = kpi_html(ledger.get("kpis") or [])
    spec = chart_spec(app, ledger) if live else {}
    insights = insight_figures(app, ledger) if live else []
    has_trend = bool(spec.get("has_trend"))
    find_noun = (spec.get("geo") or "name").replace("_", " ")
    jump = ""
    if live:
        jump_links = [
            '<a href="#takeaways">Takeaways</a>',
            '<a href="#view-rank">Compare</a>',
        ]
        if has_trend:
            jump_links.append('<a href="#view-trend">Trend</a>')
        jump_links.append('<a href="#view-table">Table</a>')
        jump = (
            '<nav class="jump" aria-label="On this page">'
            + "".join(jump_links)
            + "</nav>\n"
        )
    latest_section = ""
    if live:
        latest_section = f"""
<section id="takeaways" style="margin-top:30px">
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
{insight_html(insights)}
  <section id="view-rank">
    <h2>{esc(spec.get("title") or metric_label)}</h2>
    <div class="lede">{esc(spec.get("lede") or metric_label)} The full list is in the table below.</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure 1</span>
        <span class="ex-t">{esc(spec.get("title") or metric_label)}</span></div>
      <div class="plot plot-mid"><canvas id="chRank"></canvas></div>
      <div class="note">Ranks are Pioneer calculations from the published source file (derived). Values are labeled on each bar.</div>
      <div class="srcline"><b>Source:</b> see the register (the first source id). <b>Calculation:</b> Pioneer Institute (ranks only). <b>Unit:</b> {esc(unit or 'see the register')}.</div>
    </div>
  </section>
"""
    else:
        latest_section = f"""
<section id="takeaways" style="margin-top:30px">
  <h2>What this application will cover</h2>
  <p class="lede">{esc(app['scope'])}</p>
  <p class="body-p">{esc(app['exclusions'])}</p>
  <p class="body-p">It replaces these Tableau workbooks: {replaces}.</p>
</section>
"""
    trend_section = ""
    if live and has_trend:
        trend_section = f"""
<section id="view-trend">
    <h2>How has the series moved?</h2>
    <div class="lede">{esc(spec.get("trend_title"))}. Empty periods are omitted.</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure 2</span>
        <span class="ex-t">{esc(spec.get("trend_title") or "Trend")}</span></div>
      <div class="plot"><canvas id="chTrend"></canvas></div>
      <div class="srcline"><b>Source:</b> see the register. <b>Unit:</b> {esc(unit or "see the register")}. <b>Calculation:</b> Pioneer Institute.</div>
    </div>
  </section>
"""
    table_section = ""
    if live:
        table_section = f"""
<section id="view-table">
    <h2>{esc(spec.get("table_noun") or "Every row")}</h2>
    <div class="lede">{esc(metric_label)}{', ' + esc(unit) if unit else ''}. Type a name to jump to a row.</div>
    <div class="findrow">
      <label class="sel-lab" for="tblFind">Find a {esc(find_noun)}</label>
      <input id="tblFind" type="search" placeholder="Type a name" autocomplete="off">
      <span id="tblCount" class="findcount"></span>
    </div>
    <div class="scroll">
      <table id="tblStates">
        <thead><tr><th>{esc(spec.get("col_name") or "Name")}</th><th class="n">Value</th><th class="n">Rank</th><th class="n">YoY</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="srcline"><b>Source:</b> see the register. Ranks and year-over-year changes are Pioneer calculations (derived).</div>
  </section>
"""
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

(function(){
  var q=new URLSearchParams(location.search);
  if(q.get('embed')==='1'||q.get('embed')==='true') document.body.classList.add('embed');
  var GOLD='#CCB26D', BLUE='#293C5C', INK='#222222', GREY='#666666';
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
  function isHL(r){
    if(r.st==='MA') return true;
    if(CHART.highlight && (r.name===CHART.highlight || r.st===CHART.highlight)) return true;
    return false;
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
  function rawVal(ds, i, horiz){
    var raw=ds.data[i];
    if(raw==null||raw==='') return null;
    if(typeof raw==='object'){
      var v=horiz?raw.x:raw.y;
      return (v==null||v==='')?null:v;
    }
    return raw;
  }
  function dataLabels(fmt, mode){
    return {id:'dlbl',afterDatasetsDraw:function(chart){
      var ctx=chart.ctx;
      var horiz=chart.options.indexAxis==='y';
      var isLine=chart.config.type==='line';
      ctx.save();
      ctx.font='600 10px Roboto,sans-serif';
      chart.data.datasets.forEach(function(ds, di){
        var meta=chart.getDatasetMeta(di);
        if(!meta||meta.hidden) return;
        var n=meta.data.length, idxs=[];
        if(mode==='end'||(mode!=='all'&&isLine&&n>8)){
          for(var i=n-1;i>=0;i--){ if(rawVal(ds,i,horiz)!=null){ idxs.push(i); break; } }
        } else {
          for(var j=0;j<n;j++) idxs.push(j);
        }
        idxs.forEach(function(i){
          var el=meta.data[i]; if(!el) return;
          var v=rawVal(ds,i,horiz); if(v==null) return;
          var text=fmt(v); if(!text) return;
          ctx.fillStyle=isLine?(ds.borderColor||INK):INK;
          if(horiz){
            ctx.textBaseline='middle';
            if(Number(v)<0){ ctx.textAlign='right'; ctx.fillText(text, el.x-5, el.y); }
            else { ctx.textAlign='left'; ctx.fillText(text, el.x+5, el.y); }
          } else if(isLine){
            ctx.textAlign='left';
            ctx.textBaseline=(mode==='end'||n>8)&&(di%2)?'top':'bottom';
            ctx.fillText(text, el.x+6, el.y+((mode==='end'||n>8)&&(di%2)?5:-4));
          } else {
            ctx.textAlign='center'; ctx.textBaseline='bottom';
            ctx.fillText(text, el.x, el.y-4);
          }
        });
      });
      ctx.restore();
    }};
  }
  var rows=(DL&&DL.rows)||[];
  var nChart=CHART.n_chart||12;
  var chartRows=rows.slice(0,nChart);
  if(CHART.highlight && !chartRows.some(isHL)){
    for(var hi=0;hi<rows.length;hi++){ if(isHL(rows[hi])){ chartRows=chartRows.concat([rows[hi]]); break; } }
  }
  var chRank=document.getElementById('chRank');
  if(chRank && chartRows.length && window.Chart){
    var labels=chartRows.map(rowLabel);
    var data=chartRows.map(function(r){return r.v;});
    var colors=chartRows.map(function(r){return isHL(r)?GOLD:BLUE;});
    new Chart(chRank,{type:'bar',
      data:{labels:labels,datasets:[{data:data,backgroundColor:colors,barPercentage:.72}]},
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        layout:{padding:{right:56,top:4}},
        plugins:{legend:{display:false},
          tooltip:{callbacks:{
            title:function(items){var i=items[0]&&items[0].dataIndex; return (chartRows[i]&&chartRows[i].name)||'';},
            label:function(c){var r=chartRows[c.dataIndex]||{}; var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' \u00b7 '+unit:''); return ' '+fmtVal(c.parsed.x)+' \u00b7 rank '+(r.rank||'')+extra;}
          }}},
        scales:{
          x:{title:{display:!!axisUnit,text:axisUnit,color:GREY,font:{size:11}},
            ticks:{color:GREY,callback:function(v){return fmtVal(v,true);}},grid:{color:'#EEF1F4'}},
          y:{ticks:{color:INK,font:{size:11,family:'Roboto,sans-serif'},autoSkip:false,
            callback:function(v){return String(this.getLabelForValue(v));}},
            grid:{display:false},border:{display:false}}
        }},
      plugins:[dataLabels(function(v){return fmtVal(v,true);},'all')]});
  }
  var chTrend=document.getElementById('chTrend');
  var trend=(DL&&DL.trend)||{};
  var keys=Object.keys(trend).filter(function(k){return trend[k]&&trend[k].length;});
  if(chTrend && window.Chart && keys.length){
    var pretty={US:'United States',MA:'Massachusetts',Boston:'Boston'};
    var datasets=keys.map(function(k){
      var series=trend[k]||[];
      return {label:pretty[k]||k,
        data:series.map(function(p){return {x:p.m||String(p.y),y:p.v};}),
        borderColor:(k==='MA'||k==='Boston')?GOLD:(k==='US'?INK:BLUE),
        backgroundColor:'transparent',tension:.15,pointRadius:2,pointHoverRadius:5,borderWidth:k==='MA'?2.4:2};
    });
    new Chart(chTrend,{type:'line',data:{datasets:datasets},
      options:{responsive:true,maintainAspectRatio:false,
        layout:{padding:{top:8,right:64}},
        plugins:{legend:{display:true,position:'top',align:'end',labels:{boxWidth:10,font:{size:11}}},
          tooltip:{callbacks:{label:function(c){var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' '+unit:''); return ' '+c.dataset.label+': '+fmtVal(c.parsed.y)+extra;}}}},
        scales:{
          x:{type:'category',ticks:{color:GREY,maxTicksLimit:12,
            callback:function(v){return String(this.getLabelForValue(v));}}},
          y:{title:{display:!!axisUnit,text:axisUnit,color:GREY,font:{size:11}},
            ticks:{color:GREY,callback:function(v){return fmtVal(v,true);}},grid:{color:'#EEF1F4'}}
        }},
      plugins:[dataLabels(function(v){return fmtVal(v,true);})]});
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
    if(!el||!window.Chart||!fig||!fig.labels||!fig.series) return;
    var ifmt=fig.format||'number';
    var iunit=fig.unit||(ifmt==='percent'?'percent':((ifmt==='usd'||ifmt==='usd_millions')?'dollars':''));
    var extra=(ifmt==='usd'||ifmt==='usd_millions'||ifmt==='percent')?'':(iunit?' '+iunit:'');
    var horiz=fig.type==='bar';
    var scales=horiz?{
      x:{ticks:valTick(ifmt),title:valTitle(iunit),grid:{color:'#EEF1F4'}},
      y:{ticks:catTick(32),grid:{display:false},border:{display:false}}
    }:{
      x:{ticks:Object.assign({},catTick(16),{color:GREY,autoSkip:fig.labels.length>12,maxTicksLimit:12}),
        grid:{display:false}},
      y:{ticks:valTick(ifmt),title:valTitle(iunit),grid:{color:'#EEF1F4'},border:{display:false}}
    };
    var nLab=(fig.labels||[]).length;
    var opts={
      responsive:true,maintainAspectRatio:false,
      layout:{padding:{top:fig.type==='grouped'?16:6,right:horiz||fig.type==='line'?56:12}},
      plugins:{legend:{display:fig.type==='grouped'||(fig.series.length>1 && fig.series[0].label),
        position:'top',align:'end',labels:{boxWidth:10,font:{size:11}}},
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
          return {label:s.label||fig.title,data:s.data,borderColor:s.color||GOLD,
            backgroundColor:'transparent',tension:.15,pointRadius:2,pointHoverRadius:5,borderWidth:2.2,spanGaps:true};
        })},
        options:Object.assign({},opts,{indexAxis:'x'}),
        plugins:[lbl]});
      return;
    }
    if(fig.type==='grouped'){
      new Chart(el,{type:'bar',
        data:{labels:fig.labels,datasets:fig.series.map(function(s){
          return {label:s.label,data:s.data,backgroundColor:s.color||NAVY,barPercentage:.72};
        })},
        options:Object.assign({},opts,{indexAxis:'x'}),
        plugins:[lbl]});
      return;
    }
    var s0=fig.series[0]||{};
    new Chart(el,{type:'bar',
      data:{labels:fig.labels,datasets:[{data:s0.data,backgroundColor:s0.colors||NAVY,barPercentage:.72}]},
      options:Object.assign({},opts,{indexAxis:'y'}),
      plugins:[lbl]});
  });
  var tb=document.querySelector('#tblStates tbody');
  if(tb){
    tb.innerHTML=rows.map(function(r){
      var yoy=(r.yoy_pct==null?'':(r.yoy_pct>0?'+':'')+r.yoy_pct+'%');
      var hl=isHL(r)?' class="hl-ma"':'';
      var key=((r.name||'')+' '+(r.st||'')).toLowerCase();
      return '<tr'+hl+' data-q="'+key.replace(/"/g,'')+'"><td class="m">'+r.name+'</td><td class="n">'+fmtVal(r.v)+'</td><td class="n">'+(r.rank||'')+'</td><td class="n">'+yoy+'</td></tr>';
    }).join('');
    var find=document.getElementById('tblFind');
    var countEl=document.getElementById('tblCount');
    function applyFind(){
      var q=(find&&find.value||'').toLowerCase().replace(/^\\s+|\\s+$/g,'');
      var n=0, shown=0, first=null;
      [].slice.call(tb.querySelectorAll('tr')).forEach(function(tr){
        var ok=!q || (tr.getAttribute('data-q')||'').indexOf(q)>=0;
        tr.hidden=!ok;
        n++;
        if(ok){ shown++; if(!first) first=tr; }
      });
      if(countEl) countEl.textContent = q ? (shown+' of '+n) : (n+' '+(n===1?'row':'rows'));
      if(q && shown===1 && first) first.scrollIntoView({block:'nearest'});
    }
    var params=new URLSearchParams(location.search);
    var startQ=params.get('q')||params.get('st')||'';
    if(find && startQ && !find.value) find.value=startQ;
    function writeQuery(){
      var q=(find&&find.value||'').replace(/^\\s+|\\s+$/g,'');
      var next=location.pathname+(q?('?q='+encodeURIComponent(q)):'')+location.hash;
      history.replaceState(null,'',next);
    }
    if(find) find.addEventListener('input', function(){ applyFind(); writeQuery(); });
    applyFind();
  }
})();
</script>
""".replace("SLUG", slug).replace("CHART_JSON", json.dumps(spec, ensure_ascii=True)).replace("INSIGHTS_JSON", json.dumps(insights, ensure_ascii=True))
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
    <a href="https://pioneerinstitute.org" aria-label="Pioneer Institute"><img src="https://pioneerinstitute.org/wp-content/uploads/2025/11/Pioneer_Negative_SVG.svg" alt="Pioneer Institute"></a>
    <a class="backlink" href="/">&#8592; All of DataLabs</a>
    <a class="nav" href="/#directory">Catalog</a>
    <a class="nav" href="/#about">About</a>
    <a class="nav" href="/status/">Status</a>
  </div>
  <span class="tag"><b>DataLabs</b> &nbsp;&middot;&nbsp; {esc(title)}</span>
</div>
<header>
  <div class="dots" aria-hidden="true"></div>
  <div class="org">{esc(vertical)} <span class="sub">/ {esc(topic)}</span></div>
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
<div class="proto"><span class="proto-tag">{proto_tag}</span><span class="proto-txt">{proto}</span></div>
{jump}
{latest_section}
{trend_section}
{table_section}
{related_section}
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
      <p class="body-p">It replaces these Tableau workbooks: {replaces}.</p>
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
    <div><b>About this tool.</b> {esc(title)} is a Pioneer Institute DataLabs research tool. Corrections and data refreshes are logged in the <a href="/changelog/">public changelog</a>. It is a living data tool, not a static report.</div>
    <div><b>How to cite.</b> Pioneer Institute DataLabs, {esc(title)}, data through {esc(as_of_label)}. Name the source id next to the figure (for example SRC-13-01). The version and vintage in the masthead belong in the citation.</div>
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
    missing = []
    for app in apps:
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
