/* DataLabs fifty-state choropleth. Paints assets/us-states.svg from a row list.
   Low values are light steel; high values are navy. Massachusetts keeps a gold
   outline and Florida a rust outline so both stay findable on the map. */
(function (root) {
  'use strict';

  var NAVY = '#293C5C';
  var LIGHT = '#E8EDF4';
  var EMPTY = '#EEF1F4';
  var LO_RED = '#8C2F1B';
  var HI_WARM = '#F3E7CB';
  var TPL = null;
  var WAIT = [];

  function hex(n) {
    var s = Math.max(0, Math.min(255, Math.round(n))).toString(16);
    return s.length === 1 ? '0' + s : s;
  }

  function lerp(a, b, u) {
    var pa = [1, 3, 5].map(function (i) { return parseInt(a.slice(i, i + 2), 16); });
    var pb = [1, 3, 5].map(function (i) { return parseInt(b.slice(i, i + 2), 16); });
    return '#' + pa.map(function (v, i) { return hex(v + (pb[i] - v) * u); }).join('');
  }

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

  function scaleOf(rows) {
    var vals = [];
    (rows || []).forEach(function (r) {
      var n = num(r && r.v);
      if (n != null) vals.push(n);
    });
    if (!vals.length) return { fill: function () { return EMPTY; }, lo: 0, hi: 0, mid: 0, diverging: false };
    var lo = Math.min.apply(null, vals);
    var hi = Math.max.apply(null, vals);
    var diverging = lo < 0 && hi > 0;
    var span = hi - lo || 1;
    return {
      lo: lo, hi: hi, mid: diverging ? 0 : (lo + hi) / 2, diverging: diverging,
      fill: function (v) {
        var n = num(v);
        if (n == null) return EMPTY;
        if (diverging) {
          if (n < 0) return lerp(LO_RED, HI_WARM, 1 - Math.min(1, Math.abs(n) / (Math.abs(lo) || 1)));
          return lerp(LIGHT, NAVY, Math.min(1, n / (hi || 1)));
        }
        return lerp(LIGHT, NAVY, (n - lo) / span);
      }
    };
  }

  function htmlEsc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function mount(el, svg) {
    el.classList.add('usmap');
    el.innerHTML =
      '<div class="usmap-box">' + svg + '<div class="usmap-tip" hidden></div></div>' +
      '<div class="usmap-legend">' +
        '<div class="usmap-legbar"></div>' +
        '<div class="usmap-leglab"><span class="usmap-lo"></span><span class="usmap-mid"></span><span class="usmap-hi"></span></div>' +
        '<div class="usmap-key"><i></i>Massachusetts<i class="fl"></i>Florida</div>' +
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

  function paint(el, opts) {
    opts = opts || {};
    var rows = opts.rows || [];
    var lookup = bySt(rows);
    var sc = scaleOf(rows);
    var fmt = opts.format || function (v) { return v == null ? '' : String(v); };
    var extra = opts.extra || function () { return ''; };
    var active = opts.active || null;
    var selected = opts.selected ? String(opts.selected).toUpperCase() : '';
    var nodes = el.querySelectorAll('.st');

    el.querySelector('.usmap-legbar').style.background = sc.diverging
      ? 'linear-gradient(90deg,' + LO_RED + ',' + HI_WARM + ' 50%,' + NAVY + ')'
      : 'linear-gradient(90deg,' + LIGHT + ',' + NAVY + ')';
    el.querySelector('.usmap-lo').textContent = fmt(sc.lo);
    el.querySelector('.usmap-mid').textContent = sc.diverging ? fmt(0) : fmt(sc.mid);
    el.querySelector('.usmap-hi').textContent = fmt(sc.hi);

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

    var usable = rows.filter(function (r) { return num(r.v) != null; });
    if (active) usable = usable.filter(function (r) { return active.indexOf(r.st) >= 0; });
    var hi = pick(usable, function (r, b) { return !b || num(r.v) > num(b.v); });
    var lo = pick(usable, function (r, b) { return !b || num(r.v) < num(b.v); });
    var ma = lookup.MA;
    var fl = lookup.FL;
    function cell(cls, k, r) {
      if (!r) return '';
      var bits = [fmt(r.v)];
      var more = extra(r);
      if (more) bits.push(more);
      return '<div class="' + cls + '"><div class="k">' + htmlEsc(k) + '</div><div class="v">' +
        htmlEsc(r.name || r.st) + ' · ' + htmlEsc(bits.join(' · ')) + '</div></div>';
    }
    var read = el.querySelector('.usmap-read');
    var html = cell('', 'Highest', hi) + cell('', 'Lowest', lo) +
      cell('ma', 'Massachusetts', ma) + cell('fl', 'Florida', fl);
    if (opts.ref && opts.ref.value != null) {
      html += '<div><div class="k">' + htmlEsc(opts.ref.label || 'United States') +
        '</div><div class="v">' + htmlEsc(fmt(opts.ref.value)) + '</div></div>';
    }
    read.innerHTML = html;

    el._dlFmt = fmt;
    el._dlExtra = extra;
    el._dlLookup = lookup;
    el._dlOnSelect = opts.onSelect || null;

    if (!el._dlMapBound) {
      el._dlMapBound = true;
      el.addEventListener('mousemove', function (ev) {
        var p = ev.target.closest && ev.target.closest('.st');
        var tipEl = el.querySelector('.usmap-tip');
        var boxEl = el.querySelector('.usmap-box');
        if (!p || p.classList.contains('is-dim') || p.classList.contains('is-empty')) {
          if (tipEl) tipEl.hidden = true;
          return;
        }
        var st = p.getAttribute('data-st');
        var row = (el._dlLookup || {})[st];
        if (!row || !tipEl || !boxEl) return;
        var more = el._dlExtra ? el._dlExtra(row) : '';
        tipEl.hidden = false;
        tipEl.innerHTML = '<b>' + htmlEsc(row.name || st) + '</b>' + htmlEsc((el._dlFmt || String)(row.v)) +
          (more ? '<small>' + htmlEsc(more) + '</small>' : '');
        var b = boxEl.getBoundingClientRect();
        tipEl.style.left = Math.min(Math.max(8, ev.clientX - b.left + 12), b.width - 160) + 'px';
        tipEl.style.top = Math.min(Math.max(8, ev.clientY - b.top + 12), b.height - 8) + 'px';
      });
      el.addEventListener('mouseleave', function () {
        var tipEl = el.querySelector('.usmap-tip');
        if (tipEl) tipEl.hidden = true;
      });
      el.addEventListener('click', function (ev) {
        var p = ev.target.closest && ev.target.closest('.st');
        if (!p || p.classList.contains('is-dim') || p.classList.contains('is-empty')) return;
        var row = (el._dlLookup || {})[p.getAttribute('data-st')];
        if (row && typeof el._dlOnSelect === 'function') el._dlOnSelect(row);
      });
      el.addEventListener('keydown', function (ev) {
        if (ev.key !== 'Enter' && ev.key !== ' ') return;
        var p = ev.target.closest && ev.target.closest('.st');
        if (!p) return;
        ev.preventDefault();
        var row = (el._dlLookup || {})[p.getAttribute('data-st')];
        if (row && typeof el._dlOnSelect === 'function') el._dlOnSelect(row);
      });
    }
  }

  function dlStateMap(el, opts) {
    if (!el) return;
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
