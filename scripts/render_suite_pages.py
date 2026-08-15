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
        "    <p class=\"lede\">Additional figures from the published files on this page. "
        "Series that are not in those files are not drawn.</p>\n"
        "    <div class=\"insight-grid\">\n"
        + "\n".join(blocks)
        + "\n    </div>\n"
        "  </section>\n"
    )


def chart_spec(app, ledger):
    """Titles, units, and highlight for the shared suite charts."""
    tid = app["id"]
    unit = ledger.get("unit") or ""
    label = ledger.get("metric_label") or "Figure"
    n_rows = len(ledger.get("rows") or [])
    named = {
        "DL-10": ("hospital", 25, None),
        "DL-22": ("transit agency", 25, "Massachusetts Bay Transportation Authority"),
        "DL-25": ("city or town", 25, "Boston city"),
        "DL-26": ("city or town", 25, "Boston city"),
        "DL-27": ("department", 25, "Boston Police Department"),
        "DL-28": ("tax type", n_rows or 22, "Total Taxes"),
        "DL-30": ("department", 25, None),
    }
    if tid in named:
        geo, n_chart, highlight = named[tid]
        n_chart = min(n_chart, n_rows) if n_rows else n_chart
    else:
        geo, n_chart, highlight = "state", min(51, n_rows) if n_rows else 51, "MA"
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
    replaces = esc(replaces_list(app, ledger))
    nsrc = len(ledger.get("source_id_map") or {})
    src_word = "source" if nsrc == 1 else "sources"
    kpis = kpi_html(ledger.get("kpis") or [])
    spec = chart_spec(app, ledger) if live else {}
    insights = insight_figures(app, ledger) if live else []
    has_trend = bool(spec.get("has_trend"))
    toggle = ""
    if live:
        toggle = """
<div class="toggle" role="tablist" aria-label="Choose a view">
  <button id="btn-latest" class="on" onclick="showView('latest')">Latest<span class="who">The current ranking</span></button>
  <button id="btn-trend" onclick="showView('trend')">Trend<span class="who">How the series has moved</span></button>
  <button id="btn-table" onclick="showView('table')">Table<span class="who">Every row</span></button>
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
{insight_html(insights)}
  <section id="view-rank">
    <h2>How do they compare?</h2>
    <div class="lede">{esc(spec.get("lede") or metric_label)}</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure 1</span>
        <span class="ex-t">{esc(spec.get("title") or metric_label)}</span></div>
      <div class="plot {'plot-ranks' if spec.get('n_chart', 51) >= 40 else 'plot-mid'}"><canvas id="chRank"></canvas></div>
      <div class="note">Hover a bar for the full name and figure. Ranks are Pioneer calculations from the published source file (derived).</div>
      <div class="srcline"><b>Source:</b> see the register (the first source id). <b>Calculation:</b> Pioneer Institute (ranks only). <b>Unit:</b> {esc(unit or 'see the register')}.</div>
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
        if has_trend:
            trend_section = f"""
<div id="view-trend" hidden>
  <section style="margin-top:30px">
    <h2>How has the series moved?</h2>
    <div class="lede">{esc(spec.get("trend_title"))}. Empty periods are omitted.</div>
    <div class="exhibit">
      <div class="ex-head"><span class="ex-n">Figure 2</span>
        <span class="ex-t">{esc(spec.get("trend_title") or "Trend")}</span></div>
      <div class="plot"><canvas id="chTrend"></canvas></div>
      <div class="srcline"><b>Source:</b> see the register. <b>Unit:</b> {esc(unit or "see the register")}. <b>Calculation:</b> Pioneer Institute.</div>
    </div>
  </section>
</div>
"""
        else:
            trend_section = """
<div id="view-trend" hidden>
  <section style="margin-top:30px">
    <h2>How has the series moved?</h2>
    <div class="lede">A multi-year trend is not in this ledger. Use Latest for the current ranking and Table for every row.</div>
  </section>
</div>
"""
    table_section = ""
    if live:
        table_section = f"""
<div id="view-table" hidden>
  <section style="margin-top:30px">
    <h2>{esc(spec.get("table_noun") or "Every row")}</h2>
    <div class="lede">{esc(metric_label)}{', ' + esc(unit) if unit else ''}.</div>
    <div class="scroll">
      <table id="tblStates">
        <thead><tr><th>{esc(spec.get("col_name") or "Name")}</th><th class="n">{esc(unit or "Value")}</th><th class="n">Rank</th><th class="n">YoY</th></tr></thead>
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
const CHART=CHART_JSON;
const INSIGHTS=INSIGHTS_JSON;

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
  var rows=(DL&&DL.rows)||[];
  var nChart=CHART.n_chart||51;
  var chartRows=rows.slice(0,nChart);
  var chRank=document.getElementById('chRank');
  if(chRank && chartRows.length && window.Chart){
    var labels=chartRows.map(rowLabel);
    var data=chartRows.map(function(r){return r.v;});
    var colors=chartRows.map(function(r){return isHL(r)?GOLD:BLUE;});
    new Chart(chRank,{type:'bar',
      data:{labels:labels,datasets:[{data:data,backgroundColor:colors,barPercentage:.72}]},
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        layout:{padding:{right:16,top:4}},
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
        }}});
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
        plugins:{legend:{display:true,position:'top',align:'end',labels:{boxWidth:10,font:{size:11}}},
          tooltip:{callbacks:{label:function(c){var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' '+unit:''); return ' '+c.dataset.label+': '+fmtVal(c.parsed.y)+extra;}}}},
        scales:{
          x:{type:'category',ticks:{color:GREY,maxTicksLimit:12,
            callback:function(v){return String(this.getLabelForValue(v));}}},
          y:{title:{display:!!axisUnit,text:axisUnit,color:GREY,font:{size:11}},
            ticks:{color:GREY,callback:function(v){return fmtVal(v,true);}},grid:{color:'#EEF1F4'}}
        }}});
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
    var opts={
      responsive:true,maintainAspectRatio:false,
      layout:{padding:{top:4,right:8}},
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
    if(fig.type==='line'){
      new Chart(el,{type:'line',
        data:{labels:fig.labels,datasets:fig.series.map(function(s){
          return {label:s.label||fig.title,data:s.data,borderColor:s.color||GOLD,
            backgroundColor:'transparent',tension:.15,pointRadius:2,pointHoverRadius:5,borderWidth:2.2,spanGaps:true};
        })},
        options:Object.assign({},opts,{indexAxis:'x'})});
      return;
    }
    if(fig.type==='grouped'){
      new Chart(el,{type:'bar',
        data:{labels:fig.labels,datasets:fig.series.map(function(s){
          return {label:s.label,data:s.data,backgroundColor:s.color||NAVY,barPercentage:.72};
        })},
        options:Object.assign({},opts,{indexAxis:'x'})});
      return;
    }
    var s0=fig.series[0]||{};
    new Chart(el,{type:'bar',
      data:{labels:fig.labels,datasets:[{data:s0.data,backgroundColor:s0.colors||NAVY,barPercentage:.72}]},
      options:Object.assign({},opts,{indexAxis:'y'})});
  });
  var tb=document.querySelector('#tblStates tbody');
  if(tb){
    tb.innerHTML=rows.map(function(r){
      var yoy=(r.yoy_pct==null?'':(r.yoy_pct>0?'+':'')+r.yoy_pct+'%');
      var hl=isHL(r)?' class="hl-ma"':'';
      return '<tr'+hl+'><td class="m">'+r.name+'</td><td class="n">'+fmtVal(r.v)+'</td><td class="n">'+(r.rank||'')+'</td><td class="n">'+yoy+'</td></tr>';
    }).join('');
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
  .plot-sm{{height:clamp(240px,28vh,360px)}}
  .plot-mid{{height:clamp(480px,62vh,780px)}}
  .plot-ranks{{height:clamp(720px,92vh,1180px)}}
  .insight-grid{{display:grid;grid-template-columns:1fr 1fr;gap:28px 36px;margin-top:8px}}
  .insight-grid .exhibit.span2{{grid-column:1/-1}}
  .insight-grid .lede{{margin:8px 0 12px;font-size:13.5px}}
  @media(max-width:900px){{.insight-grid{{grid-template-columns:1fr}}}}
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
    <div><b>About this tool.</b> {esc(title)} is a Pioneer Institute DataLabs research tool. Corrections and data refreshes are logged. It is a living data tool, not a static report.</div>
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
        dest.write_text(page_html(app, ledger), encoding="utf-8")
        n += 1
        print(f"render {app['id']} -> {dest.relative_to(ROOT)}")
        if ledger.get("status") == "live" and not insight_figures(app, ledger):
            missing.append(app["id"])
    if missing:
        sys.exit("FATAL: no insight figures for " + ", ".join(missing))
    print(f"rendered {n} suite pages")


if __name__ == "__main__":
    main()
