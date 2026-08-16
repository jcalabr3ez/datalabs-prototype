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

  root.dlCollectNums = collectNums;
  root.dlValueScale = valueScale;
  root.dlApplyScale = applyScale;

  if (!root.Chart) return;
  var Chart = root.Chart;
  var SANS = 'Roboto, system-ui, sans-serif';
  var INK = '#1A1A1A';
  var GREY = '#58575A';
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
  Chart.defaults.plugins.legend.labels.boxHeight = 2;
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
