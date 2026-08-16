/* DataLabs fifty-state choropleth. Paints assets/us-states.svg from a row list.
   Color is five ranked classes so neighboring states stay distinguishable.
   A ranked list and a distribution strip sit with the country so a state's
   place is visible without a click. Massachusetts keeps a gold outline and
   Florida a rust outline. */
(function (root) {
  'use strict';

  var NAVY = '#293C5C';
  var EMPTY = '#EEF1F4';
  var BINS = ['#E4EAF1', '#B7C4D4', '#7D90A8', '#4A6180', '#293C5C'];
  var DIVERGE = ['#8C2F1B', '#C47A5A', '#F3E7CB', '#7A8FA8', '#293C5C'];
  var TPL = null;
  var WAIT = [];

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
        lo: 0, hi: 0, diverging: false, colors: BINS
      };
    }
    var lo = vals[0], hi = vals[vals.length - 1];
    var diverging = lo < 0 && hi > 0;
    var colors = diverging ? DIVERGE : BINS;
    function q(p) {
      var i = (vals.length - 1) * p;
      var a = Math.floor(i), b = Math.ceil(i);
      if (a === b) return vals[a];
      return vals[a] + (vals[b] - vals[a]) * (i - a);
    }
    var br = [q(0.2), q(0.4), q(0.6), q(0.8)];
    function bin(v) {
      var n = num(v);
      if (n == null) return -1;
      for (var i = 0; i < br.length; i++) if (n <= br[i]) return i;
      return 4;
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

  function mount(el, svg) {
    el.classList.add('usmap');
    el.innerHTML =
      '<div class="usmap-frame">' +
        '<div class="usmap-box">' + svg + '<div class="usmap-tip" hidden></div></div>' +
        '<div class="usmap-side">' +
          '<div class="usmap-side-h">Highest to lowest</div>' +
          '<ol class="usmap-ladder"></ol>' +
        '</div>' +
      '</div>' +
      '<div class="usmap-strip-wrap">' +
        '<div class="usmap-strip-h">Where each state sits</div>' +
        '<div class="usmap-strip"></div>' +
        '<div class="usmap-strip-lab"><span>Lowest</span><span>Highest</span></div>' +
      '</div>' +
      '<div class="usmap-now" hidden></div>' +
      '<div class="usmap-legend">' +
        '<div class="usmap-bins"></div>' +
        '<div class="usmap-key"><i></i>Massachusetts<i class="fl"></i>Florida</div>' +
        '<div class="usmap-hint">Hover a state, a row, or a dot to see its rank. Click to open the table.</div>' +
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
    [].forEach.call(el.querySelectorAll('.st, .usmap-lad, .usmap-dot'), function (n) {
      n.classList.toggle('is-hot', !!(st && n.getAttribute('data-st') === st));
    });
  }

  function showNow(el, row) {
    var now = el.querySelector('.usmap-now');
    if (!now) return;
    if (!row) { now.hidden = true; now.innerHTML = ''; return; }
    var fmt = el._dlFmt || String;
    var more = el._dlCompare ? el._dlCompare(row) : '';
    var extra = el._dlExtra ? el._dlExtra(row) : '';
    var bits = [fmt(row.v)];
    if (more) bits.push(more);
    if (extra && extra !== more) bits.push(extra);
    now.hidden = false;
    now.innerHTML = '<b>' + htmlEsc(row.name || row.st) + '</b> ' + htmlEsc(bits.join(' \u00b7 '));
  }

  function bind(el) {
    if (el._dlMapBound) return;
    el._dlMapBound = true;

    function targetOf(ev) {
      return ev.target.closest && ev.target.closest('.st, .usmap-lad, .usmap-dot');
    }

    function rowOf(node) {
      if (!node || node.classList.contains('is-dim') || node.classList.contains('is-empty')) return null;
      return (el._dlLookup || {})[node.getAttribute('data-st')] || null;
    }

    el.addEventListener('mouseover', function (ev) {
      var node = targetOf(ev);
      var row = rowOf(node);
      var tipEl = el.querySelector('.usmap-tip');
      var boxEl = el.querySelector('.usmap-box');
      if (!row) return;
      setHot(el, row.st);
      showNow(el, row);
      if (!tipEl || !boxEl || !node.classList.contains('st')) {
        if (tipEl) tipEl.hidden = true;
        return;
      }
      var more = el._dlCompare ? el._dlCompare(row) : '';
      var extra = el._dlExtra ? el._dlExtra(row) : '';
      tipEl.hidden = false;
      tipEl.innerHTML = '<b>' + htmlEsc(row.name || row.st) + '</b>' +
        htmlEsc((el._dlFmt || String)(row.v)) +
        (more ? '<small>' + htmlEsc(more) + '</small>' : '') +
        (extra && extra !== more ? '<small>' + htmlEsc(extra) + '</small>' : '');
      var b = boxEl.getBoundingClientRect();
      tipEl.style.left = Math.min(Math.max(8, ev.clientX - b.left + 12), b.width - 160) + 'px';
      tipEl.style.top = Math.min(Math.max(8, ev.clientY - b.top + 12), b.height - 8) + 'px';
    });

    el.addEventListener('mousemove', function (ev) {
      var node = targetOf(ev);
      var tipEl = el.querySelector('.usmap-tip');
      var boxEl = el.querySelector('.usmap-box');
      if (!tipEl || !boxEl || !node || !node.classList.contains('st')) return;
      if (tipEl.hidden) return;
      var b = boxEl.getBoundingClientRect();
      tipEl.style.left = Math.min(Math.max(8, ev.clientX - b.left + 12), b.width - 160) + 'px';
      tipEl.style.top = Math.min(Math.max(8, ev.clientY - b.top + 12), b.height - 8) + 'px';
    });

    el.addEventListener('mouseout', function (ev) {
      var next = ev.relatedTarget;
      if (next && el.contains(next) && next.closest && next.closest('.st, .usmap-lad, .usmap-dot')) return;
      setHot(el, el._dlSelected || '');
      showNow(el, null);
      var tipEl = el.querySelector('.usmap-tip');
      if (tipEl) tipEl.hidden = true;
    });

    function select(node) {
      var row = rowOf(node);
      if (row && typeof el._dlOnSelect === 'function') el._dlOnSelect(row);
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

  function paint(el, opts) {
    opts = opts || {};
    var rows = opts.rows || [];
    var lookup = bySt(rows);
    var ranked = rankedRows(rows);
    var sc = scaleOf(rows);
    var fmt = opts.format || function (v) { return v == null ? '' : String(v); };
    var extra = opts.extra || function () { return ''; };
    var active = opts.active || null;
    var selected = opts.selected ? String(opts.selected).toUpperCase() : '';
    var compact = isCompact(el, opts);
    var nodes = el.querySelectorAll('.st');
    el.classList.toggle('is-compact', compact);

    var bins = el.querySelector('.usmap-bins');
    if (bins) {
      var names = sc.diverging
        ? ['Lowest', '', 'Near zero', '', 'Highest']
        : ['Lowest fifth', '', 'Middle', '', 'Highest fifth'];
      bins.innerHTML = sc.colors.map(function (c, i) {
        var lab = names[i] || '';
        return '<span class="usmap-bin"><i style="background:' + c + '"></i>' +
          (lab ? htmlEsc(lab) : '') + '</span>';
      }).join('');
    }

    [].forEach.call(nodes, function (p) {
      var st = p.getAttribute('data-st');
      var row = lookup[st];
      var v = row ? num(row.v) : null;
      p.setAttribute('fill', sc.fill(v));
      p.classList.toggle('is-empty', !row || v == null);
      p.classList.toggle('is-ma', st === 'MA');
      p.classList.toggle('is-fl', st === 'FL');
      p.classList.toggle('is-on', st === selected);
      p.classList.toggle('is-dim', !!(active && active.indexOf(st) < 0));
      p.setAttribute('tabindex', (!row || v == null || (active && active.indexOf(st) < 0)) ? '-1' : '0');
    });

    var ladder = el.querySelector('.usmap-ladder');
    if (ladder) {
      ladder.innerHTML = ranked.map(function (r, i) {
        var st = String(r.st).toUpperCase();
        var rk = r.rank != null && r.rank !== '' ? r.rank : (i + 1);
        var cls = ['usmap-lad'];
        if (st === 'MA') cls.push('is-ma');
        if (st === 'FL') cls.push('is-fl');
        if (st === selected) cls.push('is-on');
        if (active && active.indexOf(st) < 0) cls.push('is-dim');
        return '<li class="' + cls.join(' ') + '" data-st="' + htmlEsc(st) + '" tabindex="' +
          ((active && active.indexOf(st) < 0) ? '-1' : '0') + '">' +
          '<i class="chip" style="background:' + sc.fill(r.v) + '"></i>' +
          '<span class="rk">' + htmlEsc(rk) + '</span>' +
          '<span class="ab">' + htmlEsc(st) + '</span>' +
          '<span class="nm">' + htmlEsc(r.name || st) + '</span>' +
          '<span class="vl">' + htmlEsc(fmt(r.v)) + '</span></li>';
      }).join('');
      var onLad = ladder.querySelector('.usmap-lad.is-on') || ladder.querySelector('.usmap-lad:not(.is-dim)');
      if (onLad && onLad.scrollIntoView) onLad.scrollIntoView({ block: 'nearest' });
    }

    var strip = el.querySelector('.usmap-strip');
    if (strip) {
      var span = (sc.hi - sc.lo) || 1;
      var us = refCompare(opts.ref);
      var html = '';
      if (us != null) {
        var usX = ((us - sc.lo) / span) * 100;
        html += '<div class="usmap-usmark" style="left:' + usX + '%"><i></i><span>U.S.</span></div>';
      }
      html += ranked.map(function (r, i) {
        var st = String(r.st).toUpperCase();
        var x = ((num(r.v) - sc.lo) / span) * 100;
        var y = 50 + ((i % 5) - 2) * 14;
        var cls = ['usmap-dot'];
        if (st === 'MA') cls.push('is-ma');
        if (st === 'FL') cls.push('is-fl');
        if (st === selected) cls.push('is-on');
        if (active && active.indexOf(st) < 0) cls.push('is-dim');
        return '<button type="button" class="' + cls.join(' ') + '" data-st="' + htmlEsc(st) +
          '" style="left:' + x + '%;top:' + y + '%;background:' + sc.fill(r.v) +
          '" aria-label="' + htmlEsc((r.name || st) + ' ' + fmt(r.v)) + '"></button>';
      }).join('');
      strip.innerHTML = html;
    }

    var view = rows.filter(function (r) { return num(r.v) != null; });
    if (active) view = view.filter(function (r) { return active.indexOf(r.st) >= 0; });
    var hi = pick(view, function (r, b) { return !b || num(r.v) > num(b.v); });
    var lo = pick(view, function (r, b) { return !b || num(r.v) < num(b.v); });
    var ma = lookup.MA;
    var fl = lookup.FL;
    function cell(cls, k, r) {
      if (!r) return '';
      var bits = [fmt(r.v)];
      var more = compareLine(r, ranked, opts.ref);
      if (more) bits.push(more);
      return '<div class="' + cls + '"><div class="k">' + htmlEsc(k) + '</div><div class="v">' +
        htmlEsc(r.name || r.st) + ' \u00b7 ' + htmlEsc(bits.join(' \u00b7 ')) + '</div></div>';
    }
    var read = el.querySelector('.usmap-read');
    if (read) {
      var htmlRead = cell('', 'Highest', hi) + cell('', 'Lowest', lo) +
        cell('ma', 'Massachusetts', ma) + cell('fl', 'Florida', fl);
      if (opts.ref && refValue(opts.ref) != null) {
        htmlRead += '<div><div class="k">' + htmlEsc(opts.ref.label || 'United States') +
          '</div><div class="v">' + htmlEsc(fmt(refValue(opts.ref))) + '</div></div>';
      }
      read.innerHTML = htmlRead;
    }

    el._dlFmt = fmt;
    el._dlExtra = extra;
    el._dlCompare = function (r) { return compareLine(r, ranked, opts.ref); };
    el._dlLookup = lookup;
    el._dlOnSelect = opts.onSelect || null;
    el._dlSelected = selected;
    var hint = el.querySelector('.usmap-hint');
    if (hint) {
      hint.textContent = el._dlOnSelect
        ? 'Hover a state, a row, or a dot to see its rank. Click to open the table.'
        : 'Hover a state, a row, or a dot to see its rank against the rest.';
    }
    setHot(el, selected);
    bind(el);
  }

  function dlStateMap(el, opts) {
    if (!el) return;
    if (el._dlMapReady && !el.querySelector('.usmap-ladder')) {
      el._dlMapReady = false;
      el._dlMapBound = false;
    }
    if (el._dlMapReady) { paint(el, opts); return; }
    loadTpl(function (svg) {
      if (!svg) { el.textContent = 'Map unavailable.'; return; }
      mount(el, svg);
      el._dlMapReady = true;
      paint(el, opts);
    });
  }

  root.dlStateMap = dlStateMap;
})(typeof window !== 'undefined' ? window : globalThis);
