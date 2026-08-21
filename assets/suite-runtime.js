/* Shared suite page runtime. Pages set DL, CHART, INSIGHTS, MAP_VIEWS,
   and FIND, then this file draws the map, rank, trend, table, and find
   card. Optional window.dlSuiteExtra(ctx) runs at the end for tool-specific
   exhibits (340B). */
(function () {
  function boot() {
    var DL=window.DL, CHART=window.CHART, INSIGHTS=window.INSIGHTS||[], MAP_VIEWS=window.MAP_VIEWS||[], FIND=window.FIND;
    if (!DL || !CHART) return;

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
    var n=Number(v), sign=n<0?'−':'', a=Math.abs(n);
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
    return s.length>28?s.slice(0,26)+'…':s;
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
    } else if(kind==='school'){
      var cmpS=FIND.compare||{};
      var qS=(document.getElementById('proofFind')&&document.getElementById('proofFind').value)||(document.getElementById('tblFind')&&document.getElementById('tblFind').value)||(FIND&&FIND.default_q)||'';
      var cardS=typeof findCardFor==='function'?findCardFor(qS):null;
      push('ps-ma','Selected', cardS&&cardS.value, cardS&&cardS.name);
      push('ps-us','District', cmpS.district&&cmpS.district.value, cmpS.district&&cmpS.district.name);
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
      meta.textContent=bits.join(' \u00b7 ');
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
    var n=Number(v), a=Math.abs(n), sign=n<0?'−':'';
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
            label:function(c){var p=c.raw||{}; return ' '+fmtVal(p.x)+' · rank '+(p.rank||'');}
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
    return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\b(city|town|the)\b/g,' ').replace(/^\s+|\s+$/g,'').replace(/\s+/g,' ');
  }
  function compactFind(s){
    return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,'');
  }
  function findHitsFor(q){
    if(!FIND || !FIND.cards) return [];
    var nq=normFind(q);
    var cq=compactFind(q);
    if(!nq && !cq) return [];
    var seen={};
    var hits=[];
    function add(rec){
      if(!rec || !rec.name || seen[rec.name]) return;
      seen[rec.name]=1;
      hits.push(rec);
    }
    function keysOf(rec, k){
      var ks=[k, normFind(rec.name), compactFind(rec.name)];
      (rec.aliases||[]).forEach(function(a){
        ks.push(normFind(a));
        ks.push(compactFind(a));
      });
      return ks;
    }
    function walk(pred){
      Object.keys(FIND.cards).forEach(function(k){
        var rec=FIND.cards[k];
        if(pred(keysOf(rec, k), rec)) add(rec);
      });
    }
    walk(function(ks){
      return ks.indexOf(nq)>=0 || (cq && ks.indexOf(cq)>=0);
    });
    if(hits.length) return hits;
    walk(function(ks){
      return ks.some(function(k2){
        if(!k2) return false;
        if(nq && (k2===nq || k2.indexOf(nq+' ')===0 || nq.indexOf(k2+' ')===0)) return true;
        if(cq && cq.length>=3 && k2.indexOf(cq)===0) return true;
        return false;
      });
    });
    if(hits.length) return hits;
    walk(function(ks){
      return ks.some(function(k2){ return nq && k2 && k2.indexOf(nq)>=0; });
    });
    return hits;
  }
  function findCardFor(q){
    var hits=findHitsFor(q);
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
    if(kind==='school'){
      var school=row||(card&&rowByName(card.name));
      if(!school) return false;
      var peer=nearestPeerRow(school);
      var items=[{name:school.name,v:Number(school.v)}];
      if(peer) items.push({name:peer.name,v:Number(peer.v)});
      if(items.length<2) return false;
      return drawLookupBars(items, (school.name||'This school')+' versus the nearest school by enrollment', 'students');
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
    if(CHART.compare==='town' || CHART.compare==='finder' || (FIND && (FIND.kind==='town'||FIND.kind==='hospital'||FIND.kind==='legislator'||FIND.kind==='school'))){
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
            label:function(c){var r=chartRows[c.dataIndex]||{}; var extra=(fmt==='usd'||fmt==='usd_millions'||fmt==='percent'||fmt==='stars')?'':(unit?' · '+unit:''); return ' '+fmtVal(c.parsed.x)+' · rank '+(r.rank||'')+extra;}
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
    pickSel.innerHTML='<option value="">'+coreKeys.map(trendName).join(', ')+'</option>'+
      extraKeys.map(function(st){
        return '<option value="'+st+'"'+(st===pickedSt?' selected':'')+'>'+trendName(st)+'</option>';
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
    return !!(labs && labs.length && /^\d{4}-\d{2}$/.test(String(labs[0])));
  }
  function fmtUsdAxis(v){
    if(v==null||v==='') return '';
    var n=Number(v), sign=n<0?'\u2212':'', a=Math.abs(n);
    if(a>=1e6) return sign+'$'+(a/1e6).toFixed(1)+'M';
    if(a>=1000) return sign+'$'+Math.round(a).toLocaleString();
    return sign+'$'+String(Math.round(a));
  }
  function drawDualHeadline(){
    var right=CHART.trend_right||{};
    var ptsR=sortPts(right.points||[]);
    var leftKey=visibleTrendKeys()[0]||allTrendKeys[0];
    var ptsL=sortPts(trend[leftKey]||[]);
    if(!chTrend||!window.Chart||ptsL.length<2||ptsR.length<2) return false;
    var labelSet={};
    ptsL.forEach(function(p){ var lab=trendKey(p); if(lab) labelSet[lab]=1; });
    ptsR.forEach(function(p){ var lab=trendKey(p); if(lab) labelSet[lab]=1; });
    var labels=Object.keys(labelSet).sort();
    function seriesOf(pts){
      var by={};
      pts.forEach(function(p){ by[trendKey(p)]=p; });
      return labels.map(function(lab){
        var p=by[lab];
        return (!p||p.v==null||!isFinite(Number(p.v)))?null:Number(p.v);
      });
    }
    var left=seriesOf(ptsL);
    var rightVals=seriesOf(ptsR);
    var leftLast=null, rightLast=null;
    for(var i=left.length-1;i>=0;i--){ if(left[i]!=null){ leftLast=left[i]; break; } }
    for(var j=rightVals.length-1;j>=0;j--){ if(rightVals[j]!=null){ rightLast=rightVals[j]; break; } }
    var titleEl=document.getElementById('trendTitle');
    if(titleEl) titleEl.textContent=CHART.trend_title||'Enrollment and spending per pupil';
    var payload={labels:labels,datasets:[
      {label:'Fall enrollment',key:'enroll',data:left,yAxisID:'y',
        borderColor:NAVY,backgroundColor:'transparent',spanGaps:false,
        pointRadius:labels.length>24?0:2,pointHoverRadius:4,borderWidth:2},
      {label:right.label||'Total expenditures per pupil',key:'ppe',data:rightVals,yAxisID:'y1',
        borderColor:RUST,backgroundColor:'transparent',spanGaps:false,
        pointRadius:labels.length>24?0:2,pointHoverRadius:4,borderWidth:2}
    ]};
    var padLabs=[];
    if(leftLast!=null) padLabs.push(fmtVal(leftLast,true));
    if(rightLast!=null) padLabs.push(fmtUsdAxis(rightLast));
    var rightPad=window.dlRightPad?window.dlRightPad(padLabs,96):96;
    var opts={responsive:true,maintainAspectRatio:false,
      layout:{padding:{top:12,right:rightPad}},
      plugins:{legend:{display:true,position:'top',align:'end'},
        tooltip:{callbacks:{
          title:function(items){
            var idx=items[0]&&items[0].dataIndex;
            return (labels[idx]!=null)?String(labels[idx]):'';
          },
          label:function(c){
            var v=c.parsed.y;
            if(c.dataset.key==='ppe') return ' '+c.dataset.label+': '+fmtUsdAxis(v);
            return ' '+c.dataset.label+': '+fmtVal(v)+(unit?' '+unit:'');
          }
        }}},
      scales:{
        x:{type:'category',ticks:{color:GREY,autoSkip:true,maxTicksLimit:12}},
        y:fitScale({position:'left',grace:'10%',
          title:{display:true,text:'students',color:NAVY,font:{size:11}},
          ticks:{color:NAVY,callback:function(v){return fmtVal(v,true);}},
          grid:{color:'rgba(34,34,34,.08)'}}, left),
        y1:fitScale({position:'right',grace:'10%',
          title:{display:true,text:'dollars per pupil',color:RUST,font:{size:11}},
          ticks:{color:RUST,callback:function(v){return fmtUsdAxis(v);}},
          grid:{drawOnChartArea:false}}, rightVals)
      }};
    var plugins=[dataLabels(function(v, di){
      return di===1?fmtUsdAxis(v):fmtVal(v,true);
    }, labels.length>18?'end':'all')];
    if(trendChart){ trendChart.destroy(); trendChart=null; }
    trendChart=new Chart(chTrend,{type:'line',data:payload,options:opts,plugins:plugins});
    return true;
  }
  function drawHeadline(){
    if(CHART.trend_right && CHART.trend_right.points && CHART.trend_right.points.length>=2){
      if(drawDualHeadline()) return;
    }
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
      if(/^\d{4}-\d{2}$/.test(lab)) return lab.slice(-2)==='01'?lab.slice(0,4):'';
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
            return ' '+c.dataset.label+': '+(raw==null?'':fmtVal(raw)+extra)+(raw==null?'':' · index '+fmtIndex(c.parsed.y));
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
    var n=Number(v), sign=n<0?'−':'', a=Math.abs(n);
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
        var a=lab.slice(0,cut), b=lab.slice(cut).replace(/^\s+/, '');
        if(b.length>cap) b=b.slice(0,cap-1)+'…';
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
        return '<option value="'+c.st+'"'+(on?' selected':'')+'>'+c.name+'</option>';
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
        var n=Number(v), sign=n<0?'−':'';
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
      var q=(find&&find.value||'').toLowerCase().replace(/^\s+|\s+$/g,'');
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
      var qv=(find&&find.value||'').replace(/^\s+|\s+$/g,'');
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
    function norm(s){ return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\b(city|town|the)\b/g,' ').replace(/^\s+|\s+$/g,'').replace(/\s+/g,' '); }
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
        (rank?'<div class="fc-rank">Rank '+rank+(n?(' of '+n):'')+(yoy?(' \u00b7 '+yoy):'')+'</div>':'')+
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
      return typeof findCardFor==='function'?findCardFor(q):null;
    }
    function bindPicks(root){
      if(!root) return;
      [].slice.call(root.querySelectorAll('.find-pick')).forEach(function(btn){
        btn.addEventListener('click', function(){
          var name=btn.getAttribute('data-name')||'';
          if(find) find.value=name;
          if(proofFind) proofFind.value=name;
          applyFind();
          writeQuery();
        });
      });
    }
    function renderPick(hits){
      var kind=(FIND&&FIND.kind)||'';
      var noun=kind==='school'?'Schools that match':kind==='hospital'?'Hospitals that match':kind==='town'?'Places that match':'Matches';
      var html='<div class="fc-k">'+noun+'</div><ul class="fc-facts">'+
        hits.slice(0,12).map(function(h){
          var lab=String(h.name||'').replace(/</g,'');
          var val=h.value?(' \u00b7 '+String(h.value).replace(/</g,'')):'';
          return '<li><button type="button" class="find-pick" data-name="'+lab.replace(/"/g,'')+'">'+lab+val+'</button></li>';
        }).join('')+'</ul>';
      if(card){ card.hidden=false; card.innerHTML=html; bindPicks(card); }
      if(proofCard){ proofCard.hidden=false; proofCard.innerHTML=html; bindPicks(proofCard); }
    }
    var _apply=applyFind;
    applyFind=function(){
      _apply();
      var q=(find&&find.value||'').replace(/^\s+|\s+$/g,'');
      var extra=matchCard(q);
      var hits=(typeof findHitsFor==='function'?findHitsFor(q):[]);
      var shown=[];
      [].slice.call(tb.querySelectorAll('tr')).forEach(function(tr){ if(!tr.hidden) shown.push(tr); });
      if(extra){
        var row=typeof rowByName==='function'?rowByName(extra.name):null;
        if(!row){
          var src=(CHART.geo==='state')?mapBaseRows():rows;
          src.forEach(function(r){
            if(norm(r.name)===norm(extra.name)) row=r;
          });
        }
        renderCard(row, extra);
      } else if(hits.length>1){
        renderPick(hits);
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

  if (typeof window.dlSuiteExtra === 'function') {
    window.dlSuiteExtra({
      DL: DL,
      INK: INK,
      GOLD: GOLD,
      RUST: RUST,
      fitScale: fitScale,
      dataLabels: dataLabels,
      seriesValues: seriesValues
    });
  }

  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
