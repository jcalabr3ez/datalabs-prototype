/* Pioneer DataLabs chart theme. Load after Chart.js on every page that
   draws a figure. Pages may still set colors and formatters; this file
   sets the furniture: Roboto, square bars, straight lines, hairline
   grids, ink tooltips. Gold stays a highlight, not a default series.

   Chart.js bar charts default to beginAtZero. That is right for counts
   and shares that already sit near zero. It flattens indexes, scores,
   rates, and prices. dlValueScale keeps a zero baseline only when the
   series reaches near zero or the caller asks for one. */
(function (root) {
  'use strict';

  function collectNums(values) {
    var out = [];
    function push(v) {
      if (v == null || v === '') return;
      if (Array.isArray(v)) {
        v.forEach(push);
        return;
      }
      if (typeof v === 'object') {
        if (v.x != null) push(v.x);
        if (v.y != null) push(v.y);
        if (v.v != null) push(v.v);
        return;
      }
      var n = Number(v);
      if (isFinite(n)) out.push(n);
    }
    (values || []).forEach(push);
    return out;
  }

  function valueScale(values, opts) {
    opts = opts || {};
    var nums = collectNums(values);
    var grace = opts.grace || '12%';
    if (!nums.length) return { beginAtZero: !!opts.forceZero, grace: grace };
    var lo = Math.min.apply(null, nums);
    var hi = Math.max.apply(null, nums);
    if (lo === hi) {
      if (lo === 0 || opts.forceZero) return { beginAtZero: true, grace: grace };
      var pad = Math.abs(lo) * 0.12 || 1;
      var min = lo - pad;
      var max = hi + pad;
      if (lo > 0 && min < 0) min = lo * 0.88;
      if (hi < 0 && max > 0) max = hi * 0.88;
      return { beginAtZero: false, min: min, max: max };
    }
    var mag = Math.max(Math.abs(lo), Math.abs(hi));
    var crosses = lo < 0 && hi > 0;
    if (crosses) return { beginAtZero: false, grace: grace };
    if (opts.forceZero) return { beginAtZero: true, grace: grace };
    var nearZero = (lo >= 0 && lo <= mag * 0.2) || (hi <= 0 && hi >= -mag * 0.2);
    if (nearZero) return { beginAtZero: true, grace: grace };
    return { beginAtZero: false, grace: grace };
  }

  function applyScale(target, values, opts) {
    target = target || {};
    opts = opts || {};
    var fit = valueScale(values, opts);
    target.beginAtZero = !!fit.beginAtZero;
    if (fit.min != null && target.min == null) target.min = fit.min;
    if (fit.max != null && target.max == null) target.max = fit.max;
    if (fit.grace != null && target.grace == null) target.grace = fit.grace;
    return target;
  }

  var INK = '#1A1A1A';
  var GOLD = '#CCB26D';
  var RUST = '#C45C26';
  var NAVY = '#293C5C';
  var STEEL = '#A9B8C8';
  var GREY = '#58575A';
  var POS = '#177245';
  var NEG = '#8C2F1B';
  var SANS = 'Roboto, system-ui, sans-serif';

  function roleKey(raw) {
    var s = String(raw == null ? '' : raw).replace(/^\s+|\s+$/g, '');
    var up = s.toUpperCase();
    if (up === 'US' || up === 'U.S.' || /^UNITED STATES/i.test(s)) return 'US';
    if (up === 'MA' || /^MASSACHUSETTS/i.test(s)) return 'MA';
    if (up === 'FL' || /^FLORIDA/i.test(s)) return 'FL';
    return s;
  }

  function roleColor(raw, opts) {
    opts = opts || {};
    var key = roleKey(raw);
    if (key === 'US') return INK;
    if (key === 'MA') return GOLD;
    if (key === 'FL') return RUST;
    var extra = opts.extra != null ? String(opts.extra) : '';
    if (extra && (key === extra || String(raw) === extra || roleKey(raw) === roleKey(extra))) return NAVY;
    if (opts.highlight && (key === opts.highlight || String(raw) === opts.highlight)) return NAVY;
    if (opts.rest) return opts.rest;
    return STEEL;
  }

  function rightPad(labels, minPx) {
    var longest = 0;
    var i;
    var probe = null;
    try {
      probe = document.createElement('canvas').getContext('2d');
      if (probe) probe.font = '500 11px ' + SANS;
    } catch (e) { probe = null; }
    for (i = 0; i < (labels || []).length; i++) {
      var t = String(labels[i] == null ? '' : labels[i]);
      var w = probe ? probe.measureText(t).width : t.length * 6.6;
      if (w > longest) longest = w;
    }
    var pad = Math.ceil(longest + 18);
    if (pad < (minPx || 72)) pad = minPx || 72;
    if (pad > 220) pad = 220;
    return pad;
  }

  function markReserve(chart, id, box) {
    if (root.dlMarkReserve) root.dlMarkReserve(chart, id, box);
  }

  function refLineY(val, color, label) {
    return {
      id: 'dl-rly',
      beforeDatasetsDraw: function (c) {
        if (val == null || !c.scales || !c.scales.y) return;
        var py = c.scales.y.getPixelForValue(val);
        var left = c.chartArea.left;
        var ctx = c.ctx;
        ctx.save();
        ctx.font = '700 10px ' + SANS;
        var w = ctx.measureText(label || '').width;
        ctx.restore();
        markReserve(c, 'dl-rly', { x1: left, y1: py - 16, x2: left + w + 12, y2: py });
      },
      afterDatasetsDraw: function (c) {
        if (val == null || !c.scales || !c.scales.y || !c.chartArea) return;
        var ctx = c.ctx;
        var left = c.chartArea.left;
        var right = c.chartArea.right;
        var py = c.scales.y.getPixelForValue(val);
        ctx.save();
        ctx.strokeStyle = color || GOLD;
        ctx.setLineDash([4, 3]);
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(left, py);
        ctx.lineTo(right, py);
        ctx.stroke();
        ctx.setLineDash([]);
        if (label) {
          ctx.fillStyle = color || GOLD;
          ctx.font = '700 10px ' + SANS;
          ctx.textAlign = 'left';
          ctx.fillText(label, left + 6, py - 7);
        }
        ctx.restore();
      }
    };
  }

  function refLineX(val, color, label) {
    return {
      id: 'dl-rlx',
      beforeDatasetsDraw: function (c) {
        if (val == null || !c.scales || !c.scales.x) return;
        var px = c.scales.x.getPixelForValue(val);
        var top = c.chartArea.top;
        var ctx = c.ctx;
        ctx.save();
        ctx.font = '700 10px ' + SANS;
        var w = ctx.measureText(label || '').width;
        ctx.restore();
        markReserve(c, 'dl-rlx', { x1: px - w / 2 - 2, y1: top - 16, x2: px + w / 2 + 2, y2: top + 2 });
      },
      afterDatasetsDraw: function (c) {
        if (val == null || !c.scales || !c.scales.x || !c.chartArea) return;
        var ctx = c.ctx;
        var top = c.chartArea.top;
        var bottom = c.chartArea.bottom;
        var px = c.scales.x.getPixelForValue(val);
        ctx.save();
        ctx.strokeStyle = color || GOLD;
        ctx.setLineDash([4, 3]);
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(px, top);
        ctx.lineTo(px, bottom);
        ctx.stroke();
        ctx.setLineDash([]);
        if (label) {
          ctx.fillStyle = color || GOLD;
          ctx.font = '700 10px ' + SANS;
          ctx.textAlign = 'center';
          ctx.fillText(label, px, top - 6);
        }
        ctx.restore();
      }
    };
  }

  function endDot(opts) {
    opts = opts || {};
    return {
      id: 'dl-enddot',
      afterDatasetsDraw: function (c) {
        var want = opts.datasetIndex;
        var di;
        for (di = 0; di < (c.data.datasets || []).length; di++) {
          if (want != null && di !== want) continue;
          var ds = c.data.datasets[di];
          var key = ds && (ds.key || ds.label);
          if (opts.key && roleKey(key) !== roleKey(opts.key) && key !== opts.key) continue;
          if (opts.prefer && roleKey(key) !== roleKey(opts.prefer) && di !== 0 && want == null && !opts.key) continue;
          var meta = c.getDatasetMeta(di);
          if (!meta || meta.hidden || !meta.data || !meta.data.length) continue;
          var pt = null;
          var i;
          for (i = meta.data.length - 1; i >= 0; i--) {
            var raw = ds.data[i];
            if (raw == null || raw === '') continue;
            pt = meta.data[i];
            break;
          }
          if (!pt) continue;
          var fill = opts.color || (ds && (ds.borderColor || ds.backgroundColor)) || GOLD;
          if (opts.prefer && roleKey(key) === roleKey(opts.prefer)) fill = GOLD;
          var ctx = c.ctx;
          ctx.save();
          ctx.fillStyle = fill;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, opts.radius || 3.5, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
          if (opts.prefer && roleKey(key) === roleKey(opts.prefer)) return;
          if (want != null || opts.key) return;
        }
      }
    };
  }

  function paintCaption(ctx, w, title, unit, source, scale) {
    var y = 22 * scale;
    ctx.fillStyle = INK;
    ctx.font = '600 ' + (13 * scale) + 'px ' + SANS;
    ctx.textAlign = 'left';
    ctx.fillText(title || '', 16 * scale, y);
    y += 16 * scale;
    ctx.fillStyle = GREY;
    ctx.font = '400 ' + (11 * scale) + 'px ' + SANS;
    if (unit) {
      ctx.fillText(unit, 16 * scale, y);
      y += 14 * scale;
    }
    if (source) {
      var src = String(source).replace(/\s+/g, ' ');
      if (src.length > 140) src = src.slice(0, 137) + '\u2026';
      ctx.fillText(src, 16 * scale, y);
    }
  }

  function exhibitMeta(ex) {
    var titleEl = ex.querySelector('.ex-t');
    var srcEl = ex.querySelector('.srcline');
    var nEl = ex.querySelector('.ex-n');
    var unit = '';
    var src = srcEl ? (srcEl.textContent || '').replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '') : '';
    var m = src.match(/Unit:\s*([^.]*)/i);
    if (m) unit = m[1].replace(/^\s+|\s+$/g, '');
    return {
      title: ((nEl ? nEl.textContent + ' \u00b7 ' : '') + (titleEl ? titleEl.textContent : '')).replace(/^\s+|\s+$/g, ''),
      unit: unit,
      source: src
    };
  }

  function canvasToBlob(canvas, cb) {
    if (canvas.toBlob) {
      canvas.toBlob(function (b) { cb(b); }, 'image/png');
      return;
    }
    try {
      var url = canvas.toDataURL('image/png');
      var bin = atob(url.split(',')[1]);
      var arr = new Uint8Array(bin.length);
      var i;
      for (i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      cb(new Blob([arr], { type: 'image/png' }));
    } catch (e) { cb(null); }
  }

  function copyBlob(blob, btn) {
    function done(ok) {
      if (!btn) return;
      var prev = btn.textContent;
      btn.textContent = ok ? 'Copied' : 'Copy failed';
      setTimeout(function () { btn.textContent = prev || 'Copy figure'; }, 1600);
    }
    if (!blob) { done(false); return; }
    if (navigator.clipboard && window.ClipboardItem) {
      navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]).then(function () {
        done(true);
      }).catch(function () {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'datalabs-figure.png';
        a.click();
        done(true);
      });
    } else {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'datalabs-figure.png';
      a.click();
      done(true);
    }
  }

  function copyFigure(exhibit) {
    if (!exhibit) return;
    var meta = exhibitMeta(exhibit);
    var plotCanvas = exhibit.querySelector('canvas');
    var svg = exhibit.querySelector('.usmap-svg, .tilegrid, svg');
    var scale = 2;
    var head = 56 * scale;
    var foot = 28 * scale;
    var srcW;
    var srcH;
    var drawSrc;

    function finish(srcCanvas) {
      if (!srcCanvas) return;
      var out = document.createElement('canvas');
      out.width = srcCanvas.width;
      out.height = srcCanvas.height + head + foot;
      var ctx = out.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, out.width, out.height);
      paintCaption(ctx, out.width, meta.title, meta.unit, meta.source, scale);
      ctx.drawImage(srcCanvas, 0, head);
      canvasToBlob(out, function (blob) {
        copyBlob(blob, exhibit.querySelector('.fig-copy'));
      });
    }

    if (plotCanvas && plotCanvas.width) {
      finish(plotCanvas);
      return;
    }
    if (svg && svg.tagName && svg.tagName.toLowerCase() === 'svg') {
      srcW = svg.clientWidth || 640;
      srcH = svg.clientHeight || 360;
      var xml = new XMLSerializer().serializeToString(svg);
      var img = new Image();
      img.onload = function () {
        var c = document.createElement('canvas');
        c.width = srcW * scale;
        c.height = srcH * scale;
        var cx = c.getContext('2d');
        cx.fillStyle = '#fff';
        cx.fillRect(0, 0, c.width, c.height);
        cx.drawImage(img, 0, 0, c.width, c.height);
        finish(c);
      };
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xml);
      return;
    }
    var box = exhibit.querySelector('.usmap-box, .plot, .plot-map') || exhibit;
    srcW = box.clientWidth || 640;
    srcH = box.clientHeight || 360;
    if (root.html2canvas) {
      root.html2canvas(box, { scale: scale, backgroundColor: '#fff' }).then(finish);
      return;
    }
    var fallback = document.createElement('canvas');
    fallback.width = srcW * scale;
    fallback.height = Math.max(120, 80) * scale;
    var fx = fallback.getContext('2d');
    fx.fillStyle = '#fff';
    fx.fillRect(0, 0, fallback.width, fallback.height);
    fx.fillStyle = GREY;
    fx.font = '400 ' + (12 * scale) + 'px ' + SANS;
    fx.fillText('Open the live chart on the page to copy the figure.', 16 * scale, 40 * scale);
    finish(fallback);
  }

  function wireCopyFigures(rootEl) {
    var scope = rootEl || document;
    [].forEach.call(scope.querySelectorAll('.exhibit'), function (ex) {
      if (ex.querySelector('.fig-copy')) return;
      var head = ex.querySelector('.ex-head');
      if (!head) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'fig-copy';
      btn.textContent = 'Copy figure';
      btn.addEventListener('click', function () { copyFigure(ex); });
      head.appendChild(btn);
    });
  }

  function highlightExhibit(hash) {
    var raw = String(hash || '').replace(/^#/, '');
    if (!raw) return;
    var view = raw.split('&')[0];
    if (view.indexOf('st=') === 0) return;
    var id = view.indexOf('view-') === 0 ? view : (view.indexOf('insight-') === 0 ? view : 'view-' + view);
    var el = document.getElementById(view) || document.getElementById(id) || document.getElementById('insight-' + view);
    if (!el) return;
    var exhibit = el.classList.contains('exhibit') ? el : (el.querySelector('.exhibit') || el);
    [].forEach.call(document.querySelectorAll('.exhibit.hl'), function (n) { n.classList.remove('hl'); });
    exhibit.classList.add('hl');
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setTimeout(function () { exhibit.classList.remove('hl'); }, 4000);
  }

  root.dlCollectNums = collectNums;
  root.dlValueScale = valueScale;
  root.dlApplyScale = applyScale;
  root.dlRoleColor = roleColor;
  root.dlRoleKey = roleKey;
  root.dlRightPad = rightPad;
  root.dlRefLineY = refLineY;
  root.dlRefLineX = refLineX;
  root.dlEndDot = endDot;
  root.dlCopyFigure = copyFigure;
  root.dlWireCopyFigures = wireCopyFigures;
  root.dlHighlightExhibit = highlightExhibit;
  root.DL_INK = INK;
  root.DL_GOLD = GOLD;
  root.DL_RUST = RUST;
  root.DL_NAVY = NAVY;
  root.DL_STEEL = STEEL;
  root.DL_POS = POS;
  root.DL_NEG = NEG;

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { wireCopyFigures(); });
    } else {
      wireCopyFigures();
    }
  }

  if (!root.Chart) return;
  var Chart = root.Chart;
  var GRID = 'rgba(26,26,26,.08)';

  Chart.defaults.font.family = SANS;
  Chart.defaults.font.size = 11;
  Chart.defaults.font.weight = '400';
  Chart.defaults.color = GREY;
  Chart.defaults.animation = false;
  Chart.defaults.responsive = true;
  Chart.defaults.maintainAspectRatio = false;

  Chart.defaults.elements.bar.borderRadius = 0;
  Chart.defaults.elements.bar.borderWidth = 0;
  Chart.defaults.elements.bar.borderSkipped = false;
  Chart.defaults.elements.line.tension = 0;
  Chart.defaults.elements.line.borderWidth = 1.75;
  Chart.defaults.elements.line.borderCapStyle = 'butt';
  Chart.defaults.elements.point.radius = 0;
  Chart.defaults.elements.point.hoverRadius = 3;
  Chart.defaults.elements.point.hitRadius = 10;

  Chart.defaults.datasets.bar.borderRadius = 0;
  Chart.defaults.datasets.bar.borderWidth = 0;
  Chart.defaults.datasets.bar.barPercentage = 0.64;
  Chart.defaults.datasets.bar.categoryPercentage = 0.78;
  Chart.defaults.datasets.line.tension = 0;
  Chart.defaults.datasets.line.borderWidth = 1.75;
  Chart.defaults.datasets.line.pointRadius = 0;
  Chart.defaults.datasets.line.pointHoverRadius = 3;

  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.boxHeight = 8;
  Chart.defaults.plugins.legend.labels.font = { family: SANS, size: 11, weight: '400' };
  Chart.defaults.plugins.legend.labels.color = INK;
  Chart.defaults.plugins.legend.labels.padding = 12;

  Chart.defaults.plugins.tooltip.backgroundColor = INK;
  Chart.defaults.plugins.tooltip.titleColor = '#fff';
  Chart.defaults.plugins.tooltip.bodyColor = '#fff';
  Chart.defaults.plugins.tooltip.cornerRadius = 0;
  Chart.defaults.plugins.tooltip.displayColors = false;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.titleFont = { family: SANS, size: 11, weight: '600' };
  Chart.defaults.plugins.tooltip.bodyFont = { family: SANS, size: 12, weight: '400' };

  if (Chart.defaults.scale) {
    Chart.defaults.scale.grid.color = GRID;
    Chart.defaults.scale.grid.drawTicks = false;
    Chart.defaults.scale.ticks.color = GREY;
    Chart.defaults.scale.ticks.padding = 8;
    Chart.defaults.scale.ticks.font = { family: SANS, size: 11 };
    if (Chart.defaults.scale.border) Chart.defaults.scale.border.display = false;
  }

  // Bar charts otherwise inherit Chart.js beginAtZero: true.
  if (Chart.overrides && Chart.overrides.bar && Chart.overrides.bar.scales &&
      Chart.overrides.bar.scales._value_) {
    Chart.overrides.bar.scales._value_.beginAtZero = false;
  }
})(typeof window !== 'undefined' ? window : globalThis);
