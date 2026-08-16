/* Pioneer DataLabs chart theme. Load after Chart.js on every page that
   draws a figure. Pages may still set colors and formatters; this file
   sets the furniture: Roboto, square bars, straight lines, hairline
   grids, ink tooltips. Gold stays a highlight, not a default series. */
(function (root) {
  'use strict';
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
})(typeof window !== 'undefined' ? window : globalThis);
