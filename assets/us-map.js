/* DataLabs fifty-state map. One hex cartogram for every Figure 1.
   Packed plate: shared edges, hairline navy rules, no label halo.
   Gold outline is Massachusetts. Rust outline is Florida.
   Hover writes a readout under the cartogram, not over the hexes. */
(function (root) {
  'use strict';

  var EMPTY = '#EEF1F4';
  var NAVY5 = ['#C5D0DC', '#8DA0B5', '#5B7390', '#3A516C', '#293C5C'];
  /* Warm bins avoid Florida rust (#C45C26) so the outline stays unique. */
  var DIVERGE5 = ['#8C2F1B', '#D4894A', '#F3E7CB', '#4A6180', '#293C5C'];
  var TPL = null;
  var TOWN_TPL = null;
  var WAIT = [];
  var TOWN_WAIT = [];

  var TILE = {
    AK:[6,0], AL:[5,6], AR:[4,5], AZ:[5,1], CA:[4,0], CO:[4,2], CT:[3,10], DC:[5,9],
    DE:[4,9], FL:[6,8], GA:[5,7], HI:[7,0], IA:[3,4], ID:[2,1], IL:[2,5], IN:[2,6],
    KS:[4,4], KY:[3,6], LA:[5,4], MA:[2,10], MD:[4,8], ME:[0,11], MI:[1,7], MN:[2,4],
    MO:[3,5], MS:[5,5], MT:[2,2], NC:[4,7], ND:[2,3], NE:[4,3], NH:[1,11], NJ:[3,9],
    NM:[5,2], NV:[3,1], NY:[2,9], OH:[2,7], OK:[5,3], OR:[3,0], PA:[2,8], RI:[2,11],
    SC:[5,8], SD:[3,3], TN:[4,6], TX:[6,3], UT:[4,1], VA:[3,8], VT:[1,10], WA:[2,0],
    WI:[1,6], WV:[3,7], WY:[3,2]
  };

  /* Even-q flat-top hexes. Alaska and Hawaii sit at the lower left. */
  var HEX = {
    ME:[11,0],
    WI:[6,1], VT:[10,1], NH:[11,1],
    WA:[1,2], ID:[2,2], MT:[3,2], ND:[4,2], MN:[5,2], IL:[6,2], MI:[7,2], NY:[9,2], MA:[10,2],
    OR:[1,3], NV:[2,3], WY:[3,3], SD:[4,3], IA:[5,3], IN:[6,3], OH:[7,3], PA:[8,3], NJ:[9,3], CT:[10,3], RI:[11,3],
    CA:[1,4], UT:[2,4], CO:[3,4], NE:[4,4], MO:[5,4], KY:[6,4], WV:[7,4], VA:[8,4], MD:[9,4], DE:[10,4],
    AZ:[2,5], NM:[3,5], KS:[4,5], AR:[5,5], TN:[6,5], NC:[7,5], SC:[8,5], DC:[9,5],
    AK:[0,6], OK:[4,6], LA:[5,6], MS:[6,6], AL:[7,6], GA:[8,6],
    HI:[0,7], TX:[4,7], FL:[8,7]
  };

  function loadTpl(cb) {
    if (TPL) { cb(TPL); return; }
    WAIT.push(cb);
    if (WAIT.length > 1) return;
    fetch('/assets/us-states.svg').then(function (r) { return r.text(); }).then(function (t) {
      TPL = t;
      WAIT.forEach(function (fn) { fn(TPL); });
      WAIT = [];
    }).catch(function () {
      WAIT.forEach(function (fn) { fn(''); });
      WAIT = [];
    });
  }

  function loadTowns(cb) {
    if (TOWN_TPL) { cb(TOWN_TPL); return; }
    TOWN_WAIT.push(cb);
    if (TOWN_WAIT.length > 1) return;
    fetch('/assets/ma-towns.svg').then(function (r) { return r.text(); }).then(function (t) {
      TOWN_TPL = t;
      TOWN_WAIT.forEach(function (fn) { fn(TOWN_TPL); });
      TOWN_WAIT = [];
    }).catch(function () {
      TOWN_WAIT.forEach(function (fn) { fn(''); });
      TOWN_WAIT = [];
    });
  }

  function bySt(rows) {
    var m = {};
    (rows || []).forEach(function (r) {
      if (!r || !r.st) return;
      m[String(r.st).toUpperCase()] = r;
    });
    return m;
  }

  function num(v) {
    if (v == null || v === '') return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }

  function htmlEsc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function usableRows(rows) {
    return (rows || []).filter(function (r) { return r && r.st && num(r.v) != null; });
  }

  function rankedRows(rows) {
    var list = usableRows(rows).slice();
    var hasRank = list.every(function (r) { return r.rank != null && r.rank !== ''; });
    list.sort(function (a, b) {
      if (hasRank) {
        var ra = Number(a.rank), rb = Number(b.rank);
        if (ra !== rb) return ra - rb;
      }
      return num(b.v) - num(a.v);
    });
    return list;
  }

  function scaleOf(rows) {
    var vals = [];
    usableRows(rows).forEach(function (r) { vals.push(num(r.v)); });
    vals.sort(function (a, b) { return a - b; });
    if (!vals.length) {
      return {
        fill: function () { return EMPTY; },
        bin: function () { return -1; },
        lo: 0, hi: 0, diverging: false, colors: NAVY5, breaks: []
      };
    }
    var lo = vals[0], hi = vals[vals.length - 1];
    var diverging = lo < 0 && hi > 0;
    var colors = diverging ? DIVERGE5 : NAVY5;
    var n = colors.length;
    function q(p) {
      var i = (vals.length - 1) * p;
      var a = Math.floor(i), b = Math.ceil(i);
      if (a === b) return vals[a];
      return vals[a] + (vals[b] - vals[a]) * (i - a);
    }
    var br = [];
    for (var i = 1; i < n; i++) br.push(q(i / n));
    function bin(v) {
      var x = num(v);
      if (x == null) return -1;
      for (var j = 0; j < br.length; j++) if (x <= br[j]) return j;
      return n - 1;
    }
    return {
      lo: lo, hi: hi, diverging: diverging, colors: colors, breaks: br,
      fill: function (v) {
        var b = bin(v);
        return b < 0 ? EMPTY : colors[b];
      },
      bin: bin
    };
  }

  function refValue(ref) {
    if (!ref) return null;
    if (typeof ref === 'object') return num(ref.value);
    return num(ref);
  }

  function refCompare(ref) {
    if (!ref || typeof ref !== 'object') return refValue(ref);
    if (ref.compare === false) return null;
    return refValue(ref);
  }

  function compareLine(row, ranked, ref) {
    if (!row) return '';
    var n = ranked.length;
    var rank = row.rank != null && row.rank !== '' ? Number(row.rank) : null;
    if (rank == null) {
      for (var i = 0; i < ranked.length; i++) {
        if (ranked[i].st === row.st) { rank = i + 1; break; }
      }
    }
    var bits = [];
    if (rank != null && n) bits.push(rank + ' of ' + n);
    var us = refCompare(ref);
    var v = num(row.v);
    if (us != null && v != null) {
      if (v > us) bits.push('above the U.S.');
      else if (v < us) bits.push('below the U.S.');
      else bits.push('at the U.S.');
    }
    return bits.join(' \u00b7 ');
  }

  function isCompact(el, opts) {
    if (opts && opts.compact) return true;
    return !!(el.closest && el.closest('.insight-grid'));
  }

  function shell(el, inner) {
    el.classList.add('usmap');
    el.innerHTML =
      '<div class="usmap-frame">' +
        '<div class="usmap-box">' + inner + '</div>' +
        '<div class="usmap-pin" hidden>' +
          '<div class="k" data-pin-k>Selected</div>' +
          '<div class="v" data-pin-v></div>' +
        '</div>' +
      '</div>' +
      '<div class="usmap-legend">' +
        '<div class="usmap-bins"></div>' +
        '<div class="usmap-key"><i></i>Massachusetts<span class="cmp-key"><i class="cmp"></i><span data-cmp-lab>Florida</span></span></div>' +
      '</div>' +
      '<div class="usmap-read"></div>';
  }

  function pick(rows, pred) {
    var best = null;
    (rows || []).forEach(function (r) {
      if (!pred(r, best)) return;
      best = r;
    });
    return best;
  }

  function setHot(el, st) {
    [].forEach.call(el.querySelectorAll('.st, .tile, .town'), function (n) {
      n.classList.toggle('is-hot', !!(st && n.getAttribute('data-st') === st));
    });
  }

  function legendHtml(sc, fmt, ref) {
    var colors = sc.colors || [];
    var lo = fmt(sc.lo);
    var hi = fmt(sc.hi);
    var mid = '';
    var us = refCompare(ref);
    if (us != null) mid = fmt(us);
    else if (sc.diverging) mid = '0';
    var stops = colors.map(function (c, i) {
      return (i === 0 ? '' : ',') + c + ' ' + Math.round(i / Math.max(colors.length - 1, 1) * 100) + '%';
    }).join('');
    var labs = '<span>' + htmlEsc(lo) + '</span>';
    labs += '<span>' + htmlEsc(sc.diverging ? 'net loss / net gain' : 'fifths of states') + '</span>';
    labs += '<span>' + htmlEsc(hi) + '</span>';
    var usNote = '';
    if (us != null) {
      usNote = '<div class="usmap-us">' + htmlEsc((ref && ref.label) ? ref.label : 'United States') +
        ' is ' + htmlEsc(mid) + '</div>';
    }
    return '<div class="usmap-ramp"><div class="usmap-ramp-bar" style="background:linear-gradient(90deg,' + stops + ')"></div>' +
      '<div class="usmap-ramp-labs">' + labs + '</div></div>' + usNote;
  }

  function writeRead(el, opts, lookup, ranked, fmt) {
    var rows = opts.rows || [];
    var active = opts.active || null;
    var view = rows.filter(function (r) { return num(r.v) != null; });
    if (active) view = view.filter(function (r) { return active.indexOf(r.st) >= 0; });
    var hi = pick(view, function (r, b) { return !b || num(r.v) > num(b.v); });
    var lo = pick(view, function (r, b) { return !b || num(r.v) < num(b.v); });
    var ma = lookup.MA;
    function cell(cls, k, r) {
      if (!r) return '';
      var bits = [fmt(r.v)];
      var more = compareLine(r, ranked, opts.ref);
      if (more) bits.push(more);
      return '<div class="' + cls + '"><div class="k">' + htmlEsc(k) + '</div><div class="v">' +
        htmlEsc(r.name || r.st) + ' \u00b7 ' + htmlEsc(bits.join(' \u00b7 ')) + '</div></div>';
    }
    var read = el.querySelector('.usmap-read');
    if (!read) return;
    if (!el.classList.contains('townmap')) {
      read.hidden = true;
      read.innerHTML = '';
      return;
    }
    var htmlRead = cell('', 'Highest', hi) + cell('', 'Lowest', lo);
    if (ma && !el.classList.contains('townmap')) htmlRead += cell('ma', 'Massachusetts', ma);
    var cmp = (opts.compareSt || (opts.highlightFlorida ? 'FL' : '') || '').toUpperCase();
    if (cmp && cmp !== 'MA' && lookup[cmp]) {
      htmlRead += cell('fl', lookup[cmp].name || cmp, lookup[cmp]);
    } else if (opts.highlightFlorida) {
      htmlRead += cell('fl', 'Florida', lookup.FL);
    }
    if (opts.ref && refValue(opts.ref) != null) {
      htmlRead += '<div><div class="k">' + htmlEsc(opts.ref.label || 'United States') +
        '</div><div class="v">' + htmlEsc(fmt(refValue(opts.ref))) + '</div></div>';
    }
    read.innerHTML = htmlRead;
  }

  function bind(el) {
    if (el._dlMapBound) return;
    el._dlMapBound = true;

    function targetOf(ev) {
      return ev.target.closest && ev.target.closest('.st, .tile, .town');
    }

    function rowOf(node) {
      if (!node || node.classList.contains('is-dim') || node.classList.contains('is-empty')) return null;
      var st = node.getAttribute('data-st');
      if (st) return (el._dlLookup || {})[st] || null;
      var name = node.getAttribute('data-name') || '';
      return (el._dlByName || {})[normName(name)] || null;
    }

    function setPin(row, kind) {
      var pin = el.querySelector('.usmap-pin');
      var pk = el.querySelector('[data-pin-k]');
      var pv = el.querySelector('[data-pin-v]');
      if (!pin || !pv) return;
      if (!row) {
        pin.hidden = true;
        return;
      }
      var fmt = el._dlFmt || String;
      var more = el._dlCompare ? el._dlCompare(row) : '';
      pin.hidden = false;
      if (pk) pk.textContent = kind || (el._dlSelected && (row.st === el._dlSelected || row.name === el._dlSelected) ? 'Selected' : 'Pinned');
      pv.textContent = (row.name || row.st) + ' \u00b7 ' + fmt(row.v) + (more ? ' \u00b7 ' + more : '');
    }

    function setHover(row) {
      if (row) setPin(row, 'Pinned');
      else {
        var sel = el._dlSelected || '';
        var lookup = el._dlLookup || {};
        var byName = el._dlByName || {};
        var held = lookup[sel] || byName[sel] || null;
        if (held) setPin(held, 'Selected');
        else setPin(null);
      }
    }

    el.addEventListener('mouseover', function (ev) {
      var node = targetOf(ev);
      var row = rowOf(node);
      if (!row) return;
      setHot(el, row.st || node.getAttribute('data-st') || '');
      setHover(row);
    });

    el.addEventListener('mouseout', function (ev) {
      var next = ev.relatedTarget;
      if (next && el.contains(next) && next.closest && next.closest('.st, .tile, .town')) return;
      setHot(el, el._dlSelected || '');
      setHover(null);
    });

    function select(node) {
      var row = rowOf(node);
      if (!row) return;
      var key = row.st || row.name || '';
      var coarse = false;
      try { coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches; } catch (e) {}
      if (coarse && el._dlSelected && el._dlSelected === key) {
        if (typeof el._dlOnSelect === 'function') el._dlOnSelect(row);
        return;
      }
      el._dlSelected = key;
      setHot(el, key);
      setPin(row, 'Selected');
      if (typeof el._dlOnPin === 'function') el._dlOnPin(row);
      if (!coarse && typeof el._dlOnSelect === 'function') el._dlOnSelect(row);
    }

    el.addEventListener('click', function (ev) {
      select(targetOf(ev));
    });
    el.addEventListener('keydown', function (ev) {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      var node = targetOf(ev);
      if (!node) return;
      ev.preventDefault();
      select(node);
    });
  }

  function paintGeo(el, opts) {
    var rows = opts.rows || [];
    var lookup = bySt(rows);
    var ranked = rankedRows(rows);
    var sc = scaleOf(rows);
    var fmt = opts.format || function (v) { return v == null ? '' : String(v); };
    var extra = opts.extra || function () { return ''; };
    var active = opts.active || null;
    var selected = opts.selected ? String(opts.selected).toUpperCase() : '';
    var compact = isCompact(el, opts);
    var cmp = (opts.compareSt || 'FL' || '').toUpperCase();
    var cmpOn = !!(cmp && cmp !== 'MA');
    el.classList.toggle('is-compact', compact);
    el.classList.toggle('fl-on', true);
    el.classList.toggle('cmp-on', cmpOn);

    var bins = el.querySelector('.usmap-bins');
    if (bins) bins.innerHTML = legendHtml(sc, fmt, opts.ref);
    var cmpLab = el.querySelector('[data-cmp-lab]');
    var cmpKey = el.querySelector('.cmp-key');
    if (cmpKey) {
      cmpKey.hidden = false;
      if (cmpLab) cmpLab.textContent = (lookup[cmp] && lookup[cmp].name) || cmp || 'Florida';
    }

    [].forEach.call(el.querySelectorAll('.st'), function (p) {
      var st = p.getAttribute('data-st');
      var row = lookup[st];
      var v = row ? num(row.v) : null;
      p.style.fill = (!row || v == null) ? '' : sc.fill(v);
      p.classList.toggle('is-empty', !row || v == null);
      p.classList.toggle('is-ma', st === 'MA');
      p.classList.toggle('is-fl', st === 'FL' || (cmpOn && st === cmp));
      p.classList.toggle('is-on', st === selected);
      p.classList.toggle('is-dim', !!(active && active.indexOf(st) < 0));
      p.setAttribute('tabindex', (!row || v == null || (active && active.indexOf(st) < 0)) ? '-1' : '0');
    });

    writeRead(el, opts, lookup, ranked, fmt);
    el._dlFmt = fmt;
    el._dlExtra = extra;
    el._dlCompare = function (r) { return compareLine(r, ranked, opts.ref); };
    el._dlLookup = lookup;
    el._dlOnSelect = opts.onSelect || null;
    el._dlOnPin = opts.onPin || null;
    el._dlSelected = selected;
    setHot(el, selected);
    bind(el);
    var pinRow = selected ? lookup[selected] : lookup.MA;
    var pin = el.querySelector('.usmap-pin');
    var pv = el.querySelector('[data-pin-v]');
    var pk = el.querySelector('[data-pin-k]');
    if (pin && pv && pinRow) {
      pin.hidden = false;
      if (pk) pk.textContent = selected ? 'Selected' : 'Massachusetts';
      var more = compareLine(pinRow, ranked, opts.ref);
      pv.textContent = (pinRow.name || pinRow.st) + ' \u00b7 ' + fmt(pinRow.v) + (more ? ' \u00b7 ' + more : '');
    }
  }

  function tileGridHtml() {
    var maxR = 0, maxC = 0;
    Object.keys(TILE).forEach(function (st) {
      if (TILE[st][0] > maxR) maxR = TILE[st][0];
      if (TILE[st][1] > maxC) maxC = TILE[st][1];
    });
    var cells = [];
    for (var r = 0; r <= maxR; r++) {
      for (var c = 0; c <= maxC; c++) cells.push({ r: r, c: c, st: '' });
    }
    Object.keys(TILE).forEach(function (st) {
      var pos = TILE[st];
      cells[pos[0] * (maxC + 1) + pos[1]].st = st;
    });
    var html = '<div class="tilegrid" style="grid-template-columns:repeat(' + (maxC + 1) + ',minmax(0,1fr))">';
    cells.forEach(function (cell) {
      if (!cell.st) {
        html += '<div class="tile tile-empty" aria-hidden="true"></div>';
        return;
      }
      html += '<button type="button" class="tile st" data-st="' + cell.st + '">' +
        '<b>' + cell.st + '</b><span class="r"></span></button>';
    });
    html += '</div>';
    return html;
  }

  function paintTile(el, opts) {
    var rows = opts.rows || [];
    var lookup = bySt(rows);
    var ranked = rankedRows(rows);
    var sc = scaleOf(rows);
    var fmt = opts.format || function (v) { return v == null ? '' : String(v); };
    var extra = opts.extra || function () { return ''; };
    var active = opts.active || null;
    var selected = opts.selected ? String(opts.selected).toUpperCase() : '';
    var cmp = (opts.compareSt || 'FL' || '').toUpperCase();
    var cmpOn = !!(cmp && cmp !== 'MA');
    el.classList.add('is-tile');
    el.classList.toggle('fl-on', true);
    el.classList.toggle('cmp-on', cmpOn);

    var bins = el.querySelector('.usmap-bins');
    if (bins) bins.innerHTML = legendHtml(sc, fmt, opts.ref);
    var cmpLab = el.querySelector('[data-cmp-lab]');
    var cmpKey = el.querySelector('.cmp-key');
    if (cmpKey) {
      cmpKey.hidden = false;
      if (cmpLab) cmpLab.textContent = (lookup[cmp] && lookup[cmp].name) || cmp || 'Florida';
    }

    [].forEach.call(el.querySelectorAll('.tile.st'), function (p) {
      var st = p.getAttribute('data-st');
      var row = lookup[st];
      var v = row ? num(row.v) : null;
      p.style.background = (!row || v == null) ? EMPTY : sc.fill(v);
      p.classList.toggle('is-empty', !row || v == null);
      p.classList.toggle('is-ma', st === 'MA');
      p.classList.toggle('is-fl', st === 'FL' || (cmpOn && st === cmp));
      p.classList.toggle('is-on', st === selected);
      p.classList.toggle('is-dim', !!(active && active.indexOf(st) < 0));
      var span = p.querySelector('.r');
      if (span) span.textContent = (!row || v == null) ? '' : fmt(v);
      p.setAttribute('tabindex', (!row || v == null || (active && active.indexOf(st) < 0)) ? '-1' : '0');
    });

    writeRead(el, opts, lookup, ranked, fmt);
    el._dlFmt = fmt;
    el._dlExtra = extra;
    el._dlCompare = function (r) { return compareLine(r, ranked, opts.ref); };
    el._dlLookup = lookup;
    el._dlOnSelect = opts.onSelect || null;
    el._dlOnPin = opts.onPin || null;
    el._dlSelected = selected;
    setHot(el, selected);
    bind(el);
    var pinRowT = selected ? lookup[selected] : lookup.MA;
    var pinT = el.querySelector('.usmap-pin');
    var pvT = el.querySelector('[data-pin-v]');
    var pkT = el.querySelector('[data-pin-k]');
    if (pinT && pvT && pinRowT) {
      pinT.hidden = false;
      if (pkT) pkT.textContent = selected ? 'Selected' : 'Massachusetts';
      var moreT = compareLine(pinRowT, ranked, opts.ref);
      pvT.textContent = (pinRowT.name || pinRowT.st) + ' \u00b7 ' + fmt(pinRowT.v) + (moreT ? ' \u00b7 ' + moreT : '');
    }
  }

  function hexCenter(q, r, size) {
    return {
      x: size * 1.5 * q,
      y: size * Math.sqrt(3) * (r + (q % 2) * 0.5)
    };
  }

  function hexPoints(cx, cy, size) {
    var pts = [];
    for (var i = 0; i < 6; i++) {
      var a = Math.PI / 180 * (60 * i);
      pts.push((cx + size * Math.cos(a)).toFixed(2) + ',' + (cy + size * Math.sin(a)).toFixed(2));
    }
    return pts.join(' ');
  }

  function hexGridSvg() {
    /* Packed plate: one size for grid and draw so hexes share edges.
       viewBox must cover vertices, not centers. ME and RI sit on the
       east edge; a pad smaller than size clips those points. */
    var size = 24;
    var margin = 8;
    var halfH = size * Math.sqrt(3) / 2;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    var placed = [];
    Object.keys(HEX).forEach(function (st) {
      var qr = HEX[st];
      var c = hexCenter(qr[0], qr[1], size);
      placed.push({ st: st, x: c.x, y: c.y });
      if (c.x < minX) minX = c.x;
      if (c.y < minY) minY = c.y;
      if (c.x > maxX) maxX = c.x;
      if (c.y > maxY) maxY = c.y;
    });
    var vbX = minX - size - margin;
    var vbY = minY - halfH - margin;
    var vbW = (maxX - minX) + (size + margin) * 2;
    var vbH = (maxY - minY) + (halfH + margin) * 2;
    var html = '<svg class="usmap-svg hexgrid" viewBox="' +
      vbX.toFixed(1) + ' ' + vbY.toFixed(1) + ' ' + vbW.toFixed(1) + ' ' + vbH.toFixed(1) +
      '" role="img" aria-label="United States hex cartogram">';
    placed.forEach(function (p) {
      html += '<g class="st" data-st="' + p.st + '" tabindex="0">' +
        '<polygon points="' + hexPoints(p.x, p.y, size) + '"></polygon>' +
        '<text class="st-lab" x="' + p.x.toFixed(2) + '" y="' + p.y.toFixed(2) + '">' + p.st + '</text>' +
        '</g>';
    });
    html += '</svg>';
    return html;
  }

  function isDarkFill(c) {
    if (!c || c.charAt(0) !== '#') return false;
    var hex = c.length === 4
      ? c[1] + c[1] + c[2] + c[2] + c[3] + c[3]
      : c.slice(1);
    var n = parseInt(hex, 16);
    if (!isFinite(n)) return false;
    var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    return (0.299 * r + 0.587 * g + 0.114 * b) < 150;
  }

  function paintHex(el, opts) {
    var rows = opts.rows || [];
    var lookup = bySt(rows);
    var ranked = rankedRows(rows);
    var sc = scaleOf(rows);
    var fmt = opts.format || function (v) { return v == null ? '' : String(v); };
    var extra = opts.extra || function () { return ''; };
    var active = opts.active || null;
    var selected = opts.selected ? String(opts.selected).toUpperCase() : '';
    var compact = isCompact(el, opts);
    var roleOn = opts.roleOutlines !== false;
    var cmp = roleOn ? (opts.compareSt || 'FL' || '').toUpperCase() : '';
    var cmpOn = !!(cmp && cmp !== 'MA');
    el.classList.add('is-hex');
    el.classList.remove('is-tile');
    el.classList.toggle('is-compact', compact);
    el.classList.toggle('cmp-on', cmpOn);

    var bins = el.querySelector('.usmap-bins');
    if (bins && opts.legend !== false) bins.innerHTML = legendHtml(sc, fmt, opts.ref);
    else if (bins) bins.innerHTML = '';
    var cmpLab = el.querySelector('[data-cmp-lab]');
    var cmpKey = el.querySelector('.cmp-key');
    el.classList.toggle('fl-on', roleOn);
    el.classList.toggle('no-role', !roleOn);
    if (cmpKey) {
      cmpKey.hidden = !roleOn;
      if (cmpLab && roleOn) cmpLab.textContent = (lookup[cmp] && lookup[cmp].name) || cmp || 'Florida';
    }
    var keyEl = el.querySelector('.usmap-key');
    if (opts.legend === false) {
      if (bins) bins.innerHTML = '';
      if (keyEl) keyEl.hidden = true;
    } else if (keyEl) {
      keyEl.hidden = !roleOn;
    }

    [].forEach.call(el.querySelectorAll('.st'), function (g) {
      var st = g.getAttribute('data-st');
      var row = lookup[st];
      var v = row ? num(row.v) : null;
      var poly = g.querySelector('polygon') || g;
      var b = (v == null) ? -1 : sc.bin(v);
      var fill = '';
      if (row && typeof opts.colors === 'function') fill = opts.colors(row) || '';
      else if (row && v != null) fill = sc.fill(v);
      poly.style.fill = fill;
      g.classList.toggle('is-empty', !row || (typeof opts.colors !== 'function' && v == null));
      g.classList.toggle('is-ma', roleOn && st === 'MA');
      g.classList.toggle('is-fl', roleOn && (st === 'FL' || (cmpOn && st === cmp)));
      g.classList.toggle('is-on', st === selected);
      g.classList.toggle('is-dim', !!(active && active.indexOf(st) < 0));
      var dark = false;
      if (typeof opts.darkLabels === 'function') dark = !!(row && opts.darkLabels(row));
      else if (fill) dark = isDarkFill(fill);
      else dark = sc.diverging ? (b === 0 || b === 1 || b >= 3) : b >= 2;
      g.classList.toggle('is-dark', dark);
      var empty = !row || (typeof opts.colors !== 'function' && v == null);
      g.setAttribute('tabindex', (empty || (active && active.indexOf(st) < 0)) ? '-1' : '0');
    });

    writeRead(el, opts, lookup, ranked, fmt);
    el._dlFmt = fmt;
    el._dlExtra = extra;
    el._dlCompare = function (r) { return compareLine(r, ranked, opts.ref); };
    el._dlLookup = lookup;
    el._dlOnSelect = opts.onSelect || null;
    el._dlOnPin = opts.onPin || null;
    el._dlSelected = selected;
    setHot(el, selected);
    bind(el);
    var pinRow = selected ? lookup[selected] : (roleOn ? lookup.MA : null);
    var pin = el.querySelector('.usmap-pin');
    var pv = el.querySelector('[data-pin-v]');
    var pk = el.querySelector('[data-pin-k]');
    if (pin && pv && pinRow) {
      pin.hidden = false;
      if (pk) pk.textContent = selected ? 'Selected' : 'Massachusetts';
      var more = compareLine(pinRow, ranked, opts.ref);
      pv.textContent = (pinRow.name || pinRow.st) + ' · ' + fmt(pinRow.v) + (more ? ' · ' + more : '');
    } else if (pin) {
      pin.hidden = true;
    }
  }

  function dlStateMap(el, opts) {
    if (!el) return;
    opts = opts || {};
    if (el.querySelector('.tilegrid') || (el.querySelector('.usmap-svg') && !el.querySelector('.hexgrid'))) {
      el._dlTileReady = false;
      el._dlMapReady = false;
      el._dlHexReady = false;
      el._dlMapBound = false;
    }
    if (!el._dlHexReady) {
      shell(el, hexGridSvg());
      el._dlHexReady = true;
      el._dlMapBound = false;
    }
    paintHex(el, opts);
  }

  function normName(s) {
    return String(s || '').toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .replace(/\b(city|town|the|cdp)\b/g, ' ')
      .replace(/^\s+|\s+$/g, '')
      .replace(/\s+/g, ' ');
  }

  function byName(rows) {
    var m = {};
    (rows || []).forEach(function (r) {
      var k = normName(r.name || r.st || '');
      if (k) m[k] = r;
    });
    return m;
  }

  function paintTowns(el, opts) {
    var rows = opts.rows || [];
    var lookup = byName(rows);
    var sc = scaleOf(rows.map(function (r) {
      return { st: r.st || r.name, name: r.name, v: r.v, rank: r.rank };
    }));
    var fmt = opts.format || function (v) { return v == null ? '' : String(v); };
    var selected = opts.selected ? normName(opts.selected) : '';
    el.classList.add('townmap');
    var bins = el.querySelector('.usmap-bins');
    if (bins) bins.innerHTML = legendHtml(sc, fmt);
    [].forEach.call(el.querySelectorAll('.town'), function (p) {
      var k = normName(p.getAttribute('data-name') || '');
      var row = lookup[k];
      var v = row ? num(row.v) : null;
      p.style.fill = (!row || v == null) ? '' : sc.fill(v);
      p.classList.toggle('is-empty', !row || v == null);
      p.classList.toggle('is-on', k === selected);
      p.setAttribute('data-st', row && row.st ? row.st : k);
      p.setAttribute('tabindex', (!row || v == null) ? '-1' : '0');
    });
    var ranked = rankedRows(rows.map(function (r) {
      return { st: r.st || r.name, name: r.name, v: r.v, rank: r.rank };
    }));
    el._dlFmt = fmt;
    el._dlCompare = function (r) { return compareLine(r, ranked, opts.ref); };
    el._dlLookup = bySt(ranked);
    el._dlByName = lookup;
    el._dlOnSelect = opts.onSelect || null;
    el._dlSelected = selected;
    writeRead(el, {
      rows: ranked,
      ref: opts.ref,
      highlightFlorida: false
    }, el._dlLookup, ranked, fmt);
    bind(el);
  }

  function dlTownMap(el, opts) {
    if (!el) return;
    opts = opts || {};
    if (el._dlTownReady) { paintTowns(el, opts); return; }
    loadTowns(function (svg) {
      if (!svg) { el.textContent = 'Town map unavailable.'; return; }
      shell(el, svg);
      var key = el.querySelector('.usmap-key');
      if (key) key.innerHTML = '';
      el._dlTownReady = true;
      paintTowns(el, opts);
    });
  }

  root.dlStateMap = dlStateMap;
  root.dlTownMap = dlTownMap;
})(typeof window !== 'undefined' ? window : globalThis);
