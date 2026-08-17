/* DataLabs on-chart value labels. Draws a figure next to a bar or at the
   end of a line, then skips or repositions it when it would overlap another
   label, a series line, a reserved annotation, or the canvas edge. Multi-series
   line ends are stacked in a right-hand column so they do not sit on the
   strokes. A white halo keeps type readable when it must sit near a line.
   Tooltips still carry every value. */
(function (root) {
  'use strict';

  var GAP = 14;
  var HALO = 'rgba(255,255,255,0.92)';
  var INK = '#222222';
  var GOLD = '#CCB26D';
  var RUST = '#C45C26';

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

  function countBars(chart) {
    var n = 0;
    (chart.data.datasets || []).forEach(function (ds) {
      if (!ds || !ds.data) return;
      if (ds.data.length > n) n = ds.data.length;
    });
    return n;
  }

  function pickMode(chart, mode) {
    if (mode === 'none') return 'none';
    if (mode === 'all' || mode === 'end') return mode;
    var isLine = chart.config.type === 'line';
    var n = countBars(chart);
    var nDs = (chart.data.datasets || []).length;
    var horiz = chart.options && chart.options.indexAxis === 'y';
    if (!isLine && n > 8) return 'none';
    if (isLine && (n > 6 || (nDs > 1 && n > 4))) return 'end';
    if (!isLine && !horiz && nDs > 1 && n > 6) return 'end';
    return 'all';
  }

  function callFmt(fmt, v, di, i) {
    try { return fmt(v, di, i); } catch (e) { return fmt(v); }
  }

  function outcode(x, y, b) {
    var c = 0;
    if (x < b.x1) c |= 1;
    if (x > b.x2) c |= 2;
    if (y < b.y1) c |= 4;
    if (y > b.y2) c |= 8;
    return c;
  }

  function segHitsBox(x1, y1, x2, y2, b) {
    var o1 = outcode(x1, y1, b);
    var o2 = outcode(x2, y2, b);
    var guard = 0;
    while (guard++ < 8) {
      if (!(o1 | o2)) return true;
      if (o1 & o2) return false;
      var o = o1 || o2;
      var x, y;
      if (o & 8) { x = x1 + (x2 - x1) * (b.y2 - y1) / (y2 - y1); y = b.y2; }
      else if (o & 4) { x = x1 + (x2 - x1) * (b.y1 - y1) / (y2 - y1); y = b.y1; }
      else if (o & 2) { y = y1 + (y2 - y1) * (b.x2 - x1) / (x2 - x1); x = b.x2; }
      else { y = y1 + (y2 - y1) * (b.x1 - x1) / (x2 - x1); x = b.x1; }
      if (o === o1) { x1 = x; y1 = y; o1 = outcode(x1, y1, b); }
      else { x2 = x; y2 = y; o2 = outcode(x2, y2, b); }
    }
    return false;
  }

  function inflate(b, pad) {
    return { x1: b.x1 - pad, y1: b.y1 - pad, x2: b.x2 + pad, y2: b.y2 + pad };
  }

  function lineHits(box, chart, pad, selfEl) {
    if (chart.config.type !== 'line') return false;
    var fat = inflate(box, pad == null ? 4 : pad);
    var di, i, meta, a, b;
    for (di = 0; di < (chart.data.datasets || []).length; di++) {
      meta = chart.getDatasetMeta(di);
      if (!meta || meta.hidden || !meta.data) continue;
      for (i = 1; i < meta.data.length; i++) {
        a = meta.data[i - 1];
        b = meta.data[i];
        if (!a || !b) continue;
        // The segment that arrives at this point is not an obstacle
        // for the label that belongs to that point.
        if (selfEl && (a === selfEl || b === selfEl)) continue;
        if (segHitsBox(a.x, a.y, b.x, b.y, fat)) return true;
      }
    }
    return false;
  }

  function barRect(el, horiz) {
    if (!el) return null;
    if (horiz) {
      var x0 = Math.min(el.x, el.base != null ? el.base : el.x);
      var x1 = Math.max(el.x, el.base != null ? el.base : el.x);
      return { x1: x0, y1: el.y - el.height / 2, x2: x1, y2: el.y + el.height / 2 };
    }
    var y0 = Math.min(el.y, el.base != null ? el.base : el.y);
    var y1 = Math.max(el.y, el.base != null ? el.base : el.y);
    return { x1: el.x - el.width / 2, y1: y0, x2: el.x + el.width / 2, y2: y1 };
  }

  function otherBarHits(box, chart, selfEl, horiz) {
    var di, i, meta, el, r;
    for (di = 0; di < (chart.data.datasets || []).length; di++) {
      meta = chart.getDatasetMeta(di);
      if (!meta || meta.hidden || !meta.data) continue;
      for (i = 0; i < meta.data.length; i++) {
        el = meta.data[i];
        if (!el || el === selfEl) continue;
        r = barRect(el, horiz);
        if (r && hits(box, r, 1)) return true;
      }
    }
    return false;
  }

  function clashes(b, placed, reserved, chart, selfEl, horiz, allowLine) {
    var p;
    for (p = 0; p < placed.length; p++) if (hits(b, placed[p])) return true;
    for (p = 0; p < reserved.length; p++) if (hits(b, reserved[p], 2)) return true;
    if (!allowLine && chart && lineHits(b, chart, 4, selfEl)) return true;
    if (chart && chart.config.type === 'bar' && otherBarHits(b, chart, selfEl, horiz)) return true;
    return false;
  }

  function colorOf(ds, idx) {
    var c = ds.backgroundColor || ds.borderColor;
    if (Array.isArray(c)) return c[idx];
    return c;
  }

  function isPriority(ds, idx) {
    var c = colorOf(ds, idx);
    return c === GOLD || c === RUST;
  }

  function paint(ctx, text, x, y, align, baseline, fill) {
    ctx.save();
    ctx.textAlign = align;
    ctx.textBaseline = baseline;
    ctx.lineJoin = 'round';
    ctx.miterLimit = 2;
    ctx.lineWidth = 3;
    ctx.strokeStyle = HALO;
    ctx.strokeText(text, x, y);
    ctx.fillStyle = fill;
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  function dlMarkReserve(chart, id, box) {
    if (!chart.$dlReserve) chart.$dlReserve = {};
    if (box) chart.$dlReserve[id] = box;
    else delete chart.$dlReserve[id];
  }

  function stackEnds(cands, ctx, chart, board, reserved) {
    var placed = [];
    var ordered = cands.slice().sort(function (a, b) { return a.el.y - b.el.y; });
    var x0 = 0;
    ordered.forEach(function (c) { if (c.el.x > x0) x0 = c.el.x; });
    x0 += 8;
    var slots = ordered.map(function (c) { return c.el.y; });
    var i;
    for (i = 1; i < slots.length; i++) {
      if (slots[i] - slots[i - 1] < GAP) slots[i] = slots[i - 1] + GAP;
    }
    var last = slots[slots.length - 1];
    var first = slots[0];
    var overflow = last - (board.bottom - 4);
    if (overflow > 0) {
      for (i = 0; i < slots.length; i++) slots[i] -= overflow;
    }
    if (slots[0] < board.top + 4) {
      var lift = (board.top + 4) - slots[0];
      for (i = 0; i < slots.length; i++) slots[i] += lift;
    }
    ordered.forEach(function (c, k) {
      var w = ctx.measureText(c.text).width;
      var h = 11;
      var y = slots[k];
      var tries = [
        { x: x0, y: y, align: 'left', baseline: 'middle' },
        { x: c.el.x + 8, y: y, align: 'left', baseline: 'middle' },
        { x: x0, y: y - 8, align: 'left', baseline: 'middle' },
        { x: x0, y: y + 8, align: 'left', baseline: 'middle' }
      ];
      var chosen = null;
      var t, tr, b;
      for (t = 0; t < tries.length; t++) {
        tr = tries[t];
        b = textBox(tr.x, tr.y, w, h, tr.align, tr.baseline);
        if (!inside(b, board, 1)) continue;
        if (clashes(b, placed, reserved, chart, c.el, false, true)) continue;
        chosen = tr;
        chosen.box = b;
        break;
      }
      if (!chosen) {
        chosen = { x: x0, y: y, align: 'left', baseline: 'middle' };
        chosen.box = textBox(chosen.x, chosen.y, w, h, chosen.align, chosen.baseline);
      }
      if (Math.abs(chosen.y - c.el.y) > 7 || chosen.x - c.el.x > 14) {
        ctx.save();
        ctx.strokeStyle = c.ds.borderColor || INK;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(c.el.x + 2, c.el.y);
        ctx.lineTo(chosen.x - 3, chosen.y);
        ctx.stroke();
        ctx.restore();
      }
      paint(ctx, c.text, chosen.x, chosen.y, chosen.align, chosen.baseline, c.ds.borderColor || INK);
      placed.push(chosen.box);
    });
    return placed;
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
        if (use === 'none') return;
        var reserved = reservedList(chart);
        ctx.save();
        ctx.font = '500 11px Roboto,system-ui,sans-serif';
        var placed = [];
        var cands = [];
        var nBars = countBars(chart);

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
              thick: thick, isLine: isLine, horiz: horiz, pri: isPriority(ds, idx),
              nDs: chart.data.datasets.length
            });
          });
        });

        if (use === 'end' && isLine && cands.length > 1) {
          stackEnds(cands, ctx, chart, board, reserved);
          ctx.restore();
          return;
        }

        cands.sort(function (a, b) {
          if (a.pri !== b.pri) return a.pri ? -1 : 1;
          if (a.di !== b.di) return b.di - a.di;
          return Math.abs(b.nv || 0) - Math.abs(a.nv || 0);
        });

        var leftovers = [];
        cands.forEach(function (c) {
          var w = ctx.measureText(c.text).width;
          var h = 11;
          var el = c.el;
          var lineFill = c.ds.borderColor || INK;
          var tries = [];
          if (c.horiz) {
            var dy = (c.nDs > 1) ? ((c.di % 2) ? 6 : -6) : 0;
            if (c.nv != null && c.nv < 0) {
              tries.push({ x: el.x - 6, y: el.y + dy, align: 'right', baseline: 'middle', fill: INK });
              tries.push({ x: el.x - 6, y: el.y - 9, align: 'right', baseline: 'middle', fill: INK });
              tries.push({ x: el.x - 6, y: el.y + 9, align: 'right', baseline: 'middle', fill: INK });
              tries.push({ x: el.x + 6, y: el.y + dy, align: 'left', baseline: 'middle', fill: INK, inside: true });
            } else {
              tries.push({ x: el.x + 6, y: el.y + dy, align: 'left', baseline: 'middle', fill: INK });
              tries.push({ x: el.x + 6, y: el.y - 9, align: 'left', baseline: 'middle', fill: INK });
              tries.push({ x: el.x + 6, y: el.y + 9, align: 'left', baseline: 'middle', fill: INK });
              tries.push({ x: el.x - 6, y: el.y + dy, align: 'right', baseline: 'middle', fill: INK, inside: true });
            }
          } else if (c.isLine) {
            var odd = c.di % 2;
            tries.push({ x: el.x + 8, y: el.y + (odd ? 8 : -7), align: 'left', baseline: odd ? 'top' : 'bottom', fill: lineFill });
            tries.push({ x: el.x + 8, y: el.y + (odd ? -7 : 8), align: 'left', baseline: odd ? 'bottom' : 'top', fill: lineFill });
            tries.push({ x: el.x - 8, y: el.y - 7, align: 'right', baseline: 'bottom', fill: lineFill });
            tries.push({ x: el.x - 8, y: el.y + 8, align: 'right', baseline: 'top', fill: lineFill });
            tries.push({ x: el.x, y: el.y - 10, align: 'center', baseline: 'bottom', fill: lineFill });
            tries.push({ x: el.x, y: el.y + 10, align: 'center', baseline: 'top', fill: lineFill });
          } else {
            var dx = (c.nDs > 1) ? ((c.di % 2) ? 8 : -8) : 0;
            tries.push({ x: el.x + dx, y: el.y - 6, align: 'center', baseline: 'bottom', fill: INK });
            tries.push({ x: el.x, y: el.y - 16, align: 'center', baseline: 'bottom', fill: INK });
            tries.push({ x: el.x - 12, y: el.y - 6, align: 'center', baseline: 'bottom', fill: INK });
            tries.push({ x: el.x + 12, y: el.y - 6, align: 'center', baseline: 'bottom', fill: INK });
            tries.push({ x: el.x, y: el.y + 6, align: 'center', baseline: 'top', fill: INK, inside: true });
          }

          var chosen = null;
          for (var t = 0; t < tries.length; t++) {
            var tr = tries[t];
            var b = textBox(tr.x, tr.y, w, h, tr.align, tr.baseline);
            var area = tr.inside ? plot : board;
            if (!inside(b, area, tr.inside ? 0 : 1)) continue;
            if (clashes(b, placed, reserved, chart, el, c.horiz, !!tr.inside)) continue;
            chosen = tr;
            chosen.box = b;
            break;
          }
          if (!chosen) {
            leftovers.push(c);
            return;
          }
          paint(ctx, c.text, chosen.x, chosen.y, chosen.align, chosen.baseline, chosen.fill);
          placed.push(chosen.box);
        });
        if (leftovers.length) stackEnds(leftovers, ctx, chart, board, reserved.concat(placed));
        ctx.restore();
      }
    };
  }

  root.dlChartLabels = dlChartLabels;
  root.dlMarkReserve = dlMarkReserve;
  root.dlLabelHits = hits;
  root.dlLabelBox = textBox;
})(typeof window !== 'undefined' ? window : globalThis);
