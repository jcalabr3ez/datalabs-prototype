#!/usr/bin/env node
/* Guard the shared axis helper: keep zero for counts and shares that
   already sit near it; drop it for indexes, scores, rates, and prices. */
import fs from 'fs';
import path from 'path';
import vm from 'vm';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const code = fs.readFileSync(path.join(here, '../assets/chart-theme.js'), 'utf8');
const root = {};
vm.runInNewContext(code, { window: root, globalThis: root });

const scale = root.dlValueScale;
if (typeof scale !== 'function') {
  console.error('dlValueScale is missing from chart-theme.js');
  process.exit(1);
}

const cases = [
  { name: 'NAEP scores', values: [208, 220, 237], zero: false },
  { name: 'cost of living index', values: [86, 100, 148], zero: false },
  { name: 'unemployment rate', values: [2.5, 4.1, 5.5], zero: false },
  { name: 'electricity cents', values: [10.4, 16.5, 33.0], zero: false },
  { name: 'funded ratio', values: [58, 82, 96], zero: false },
  { name: 'reliability percent', values: [71, 88, 96], zero: false },
  { name: 'GDP levels', values: [40000, 600000, 3390000], zero: true },
  { name: 'charity-care share', values: [0.8, 2.1, 6.0], zero: true },
  { name: 'legislature pay', values: [18000, 175000], zero: true },
  { name: 'includes zero', values: [0, 5, 12], zero: true },
  { name: 'crosses zero', values: [-20, 15], zero: false },
  { name: 'all-negative cluster', values: [-80, -40, -20], zero: false },
  { name: 'all-negative near zero', values: [-80, -20, -5], zero: true },
  { name: 'forced zero on scores', values: [208, 237], zero: true, opts: { forceZero: true } },
];

let failed = 0;
for (const c of cases) {
  const got = scale(c.values, c.opts || {});
  if (!!got.beginAtZero !== c.zero) {
    console.error(`FAIL ${c.name}: beginAtZero=${got.beginAtZero}, expected ${c.zero}`);
    failed += 1;
  } else {
    console.log(`ok   ${c.name}: beginAtZero=${got.beginAtZero}`);
  }
}

const single = scale([100]);
if (single.beginAtZero || single.min == null || single.max == null || single.min >= 100 || single.max <= 100) {
  console.error('FAIL single index value should pad around the point, not start at 0');
  failed += 1;
} else {
  console.log('ok   single index value pads around 100');
}

if (failed) {
  console.error(`${failed} chart-scale check(s) failed`);
  process.exit(1);
}
console.log('chart-scale: ok');
