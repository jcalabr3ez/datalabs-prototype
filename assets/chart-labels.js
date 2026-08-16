/* DataLabs on-chart value labels. Draws a figure next to a bar or at the
   end of a line, then skips or repositions it when it would overlap another
   label, a reserved annotation, or the canvas edge. Tooltips still carry
   every value. */
(function (root) {
  'use strict';

  function rawVal(ds, i, horiz) {
    var raw = ds.data[i];
    if (raw == null || raw === '') return null;
    if (typeof raw === 'object' && !Array.isArray(raw)) {
      var v = horiz ? raw.x : raw.y;
      return (v == null || v === '') ? null : v;
    }
    return raw;
  }

  function num(v) {
    if (v == null) return null;
    if (Array.isArray(v)) return (Number(v[0]) + Number(v[1])) / 2;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }

  function hits(a, b, pad) {
    pad = pad == null ? 3 : pad;
    return !(a.x2 + pad < b.x1 || b.x2 + pad < a.x1 || a.y2 + pad < b.y1 || b.y2 + pad < a.y1);
  }

  function inside(b, area, pad) {
    pad = pad == null ? 1 : pad;
    return b.x1 >= area.left - pad && b.x2 <= area.right + pad
      && b.y1 >= area.top - pad && b.y2 <= area.bottom + pad;
  }

  function textBox(x, y, w, h, align, baseline) {
    var x1 = x;
    var y1 = y;
    if (align === 'center') x1 = x - w / 2;
    else if (align === 'right') x1 = x - w;
    if (baseline === 'middle') y1 = y - h / 2;
    else if (baseline === 'bottom') y1 = y - h;
    return { x1: x1, y1: y1, x2: x1 + w, y2: y1 + h };
  }

  function canvasArea(chart) {
    return { left: 0, top: 0, right: chart.width, bottom: chart.height };
  }

  function reservedList(chart) {
    var m = chart.$dlReserve;
    if (!m) return [];
    return Object.keys(m).map(function (k) { return m[k]; }).filter(Boolean);
  }

  function pickMode(chart, mode) {
    if (mode === 'all' || mode === 'end') return mode;
    var isLine = chart.config.type === 'line';
    var n = 0;
    var nDs = 0;
    (chart.data.datasets || []).forEach(function (ds) {
      if (!ds || !ds.data) return;
      nDs += 1;
      if (ds.data.length > n) n = ds.data.length;
    });
    if (isLine && (n > 6 || (nDs > 1 && n > 4))) return 'end';
    return 'all';
  }

  function callFmt(fmt, v, di, i) {
    try { return fmt(v, di, i); } catch (e) { return fmt(v); }
  }

  function clashes(b, placed, reserved) {
    var p;
    for (p = 0; p < placed.length; p++) if (hits(b, placed[p])) return true;
    for (p = 0; p < reserved.length; p++) if (hits(b, reserved[p], 2)) return true;
    return false;
  }

  function dlMarkReserve(chart, id, box) {
    if (!chart.$dlReserve) chart.$dlReserve = {};
    if (box) chart.$dlReserve[id] = box;
    else delete chart.$dlReserve[id];
  }

  function dlChartLabels(fmt, mode) {
    fmt = fmt || function (v) { return String(v); };
    return {
      id: 'dllabels',
      afterDatasetsDraw: function (chart) {
        var ctx = chart.ctx;
        var plot = chart.chartArea;
        if (!plot) return;
        var board = canvasArea(chart);
        var horiz = chart.options.indexAxis === 'y';
        var isLine = chart.config.type === 'line';
        var use = pickMode(chart, mode);
        var reserved = reservedList(chart);
        ctx.save();
        ctx.font = '500 11px Roboto,system-ui,sans-serif';
        var placed = [];
        var cands = [];

        chart.data.datasets.forEach(function (ds, di) {
          var meta = chart.getDatasetMeta(di);
          if (!meta || meta.hidden) return;
          var n = meta.data.length;
          var idxs = [];
          if (use === 'end') {
            for (var i = n - 1; i >= 0; i--) {
              if (rawVal(ds, i, horiz) != null) { idxs.push(i); break; }
            }
          } else {
            for (var j = 0; j < n; j++) idxs.push(j);
          }
          idxs.forEach(function (idx) {
            var el = meta.data[idx];
            if (!el) return;
            var v = rawVal(ds, idx, horiz);
            if (v == null) return;
            var text = callFmt(fmt, v, di, idx);
            if (!text) return;
            var nv = num(v);
            var thick = horiz ? el.height : el.width;
            cands.push({
              el: el, text: String(text), nv: nv, di: di, i: idx, ds: ds,
              thick: thick, isLine: isLine, horiz: horiz
            });
          });
        });

        cands.sort(function (a, b) {
          if (a.di !== b.di) return b.di - a.di;
          return Math.abs(b.nv || 0) - Math.abs(a.nv || 0);
        });

        cands.forEach(function (c) {
          if (!c.isLine && c.thick != null && c.thick < 10) return;
          var w = ctx.measureText(c.text).width;
          var h = 11;
          var el = c.el;
          var ink = '#222222';
          var lineFill = c.ds.borderColor || ink;
          var tries = [];
          if (c.horiz) {
            if (c.nv != null && c.nv < 0) {
              tries.push({ x: el.x - 6, y: el.y, align: 'right', baseline: 'middle', fill: ink });
              tries.push({ x: el.x - 6, y: el.y - 8, align: 'right', baseline: 'middle', fill: ink });
              tries.push({ x: el.x - 6, y: el.y + 8, align: 'right', baseline: 'middle', fill: ink });
              tries.push({ x: el.x + 6, y: el.y, align: 'left', baseline: 'middle', fill: ink, inside: true });
            } else {
              tries.push({ x: el.x + 6, y: el.y, align: 'left', baseline: 'middle', fill: ink });
              tries.push({ x: el.x + 6, y: el.y - 8, align: 'left', baseline: 'middle', fill: ink });
              tries.push({ x: el.x + 6, y: el.y + 8, align: 'left', baseline: 'middle', fill: ink });
              tries.push({ x: el.x - 6, y: el.y, align: 'right', baseline: 'middle', fill: ink, inside: true });
            }
          } else if (c.isLine) {
            var odd = c.di % 2;
            tries.push({ x: el.x + 6, y: el.y + (odd ? 6 : -5), align: 'left', baseline: odd ? 'top' : 'bottom', fill: lineFill });
            tries.push({ x: el.x + 6, y: el.y + (odd ? -5 : 6), align: 'left', baseline: odd ? 'bottom' : 'top', fill: lineFill });
            tries.push({ x: el.x - 6, y: el.y - 5, align: 'right', baseline: 'bottom', fill: lineFill });
            tries.push({ x: el.x - 6, y: el.y + 6, align: 'right', baseline: 'top', fill: lineFill });
            tries.push({ x: el.x, y: el.y - 8, align: 'center', baseline: 'bottom', fill: lineFill });
          } else {
            tries.push({ x: el.x, y: el.y - 5, align: 'center', baseline: 'bottom', fill: ink });
            tries.push({ x: el.x - 10, y: el.y - 5, align: 'center', baseline: 'bottom', fill: ink });
            tries.push({ x: el.x + 10, y: el.y - 5, align: 'center', baseline: 'bottom', fill: ink });
            tries.push({ x: el.x, y: el.y + 5, align: 'center', baseline: 'top', fill: ink, inside: true });
          }

          var chosen = null;
          for (var t = 0; t < tries.length; t++) {
            var tr = tries[t];
            var b = textBox(tr.x, tr.y, w, h, tr.align, tr.baseline);
            var area = tr.inside ? plot : board;
            if (!inside(b, area, tr.inside ? 0 : 1)) continue;
            if (clashes(b, placed, reserved)) continue;
            chosen = tr;
            chosen.box = b;
            break;
          }
          if (!chosen) return;
          if (chosen.inside) {
            ctx.fillStyle = 'rgba(255,255,255,0.9)';
            ctx.fillRect(chosen.box.x1 - 2, chosen.box.y1 - 1, w + 4, h + 2);
          }
          ctx.fillStyle = chosen.fill;
          ctx.textAlign = chosen.align;
          ctx.textBaseline = chosen.baseline;
          ctx.fillText(c.text, chosen.x, chosen.y);
          placed.push(chosen.box);
        });
        ctx.restore();
      }
    };
  }

  root.dlChartLabels = dlChartLabels;
  root.dlMarkReserve = dlMarkReserve;
})(typeof window !== 'undefined' ? window : globalThis);
