// Offline shape checks for the question engine's 20-tool payload path.
// No API key. Asserts that candidate selection is recall-safe (golden
// questions hit the answering tool) and that core slices stay small
// enough that twenty of them still fit in one Sonnet call.
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

const tools = require("../netlify/functions/tools.js");
const ask = require("../netlify/functions/ask.js");

const REQUIRED = [
  "id", "label", "scope", "triggers", "dataset", "coreSlice", "modelSlice",
  "highlight", "rules", "link", "src",
];

const GOLDEN_HITS = [
  ["Is the T back to pre-pandemic ridership?", "DL-03"],
  ["What share of costs do fares cover on the subway?", "DL-03"],
  ["Did the cost of a subway ride in MA go up or down?", "DL-03"],
  ["What does homeowners insurance cost in Miami-Dade?", "DL-02"],
  ["Which states are considering a wealth tax?", "DL-01"],
  ["What is California's top income tax rate?", "DL-01"],
  ["What events should I watch over the next 2 months regarding wealth and high earner taxes?", "DL-01"],
  ["Should I move to Texas to avoid taxes?", "DL-01"],
  ["Will Proposition 40 pass in November?", "DL-01"],
  ["How safe is the MBTA?", "DL-03"],
  ["What is the average retail electricity price in the United States?", "DL-04"],
  ["How much does electricity cost in Massachusetts?", "DL-04"],
  ["Which state has the highest electricity prices?", "DL-04"],
  ["What is the funded ratio of the Massachusetts State Retirement Board?", "DL-05"],
  ["How funded is the Mass Teachers retirement system?", "DL-05"],
  ["How much do State and Teacher retirees get paid in Massachusetts?", "DL-05"],
  ["What does Massachusetts spend per pupil?", "DL-06"],
  ["How many students are in vocational technical programs in Massachusetts?", "DL-06"],
  ["How many students are enrolled in public K-12 in the United States?", "DL-07"],
  ["How many students are enrolled in college in Massachusetts?", "DL-08"],
  ["How many students are in charter schools in the United States?", "DL-09"],
  ["How many hospitals are in Massachusetts?", "DL-10"],
  ["Where can I find 340B covered-entity counts?", "DL-11"],
  ["How much does Massachusetts spend on Medicaid?", "DL-12"],
  ["How many new business applications were filed in the United States?", "DL-13"],
  ["What is the Massachusetts establishment birth rate?", "DL-13"],
  ["What is the unemployment rate in Massachusetts?", "DL-14"],
  ["What is Massachusetts real GDP?", "DL-15"],
  ["How many housing units were authorized in Massachusetts?", "DL-16"],
  ["What was domestic migration in Massachusetts?", "DL-17"],
  ["What is the cost of living in Massachusetts compared to the US?", "DL-19"],
  ["Are taxpayers leaving Massachusetts?", "DL-20"],
  ["What is Massachusetts adjusted gross income?", "DL-21"],
  ["Which transit agency has the most riders?", "DL-22"],
  ["How many vehicle-miles were driven in Massachusetts?", "DL-23"],
  ["How much CO2 does Massachusetts emit from energy?", "DL-24"],
  ["What is the population of Boston?", "DL-25"],
  ["Which Massachusetts town grew the most since 2020?", "DL-26"],
  ["How much is Boston city payroll?", "DL-27"],
  ["How much tax did Massachusetts collect last quarter?", "DL-28"],
  ["Which state collected the most tax last quarter?", "DL-29"],
  ["How much is Commonwealth payroll?", "DL-30"],
  ["How many prisoners does Massachusetts hold?", "DL-31"],
  ["What share of Massachusetts students met expectations on MCAS?", "DL-06"],
  ["What is the Massachusetts NAEP grade 4 reading score?", "DL-07"],
  ["Which states improved on NAEP since 2019?", "DL-07"],
  ["What is the national 6-year college graduation rate?", "DL-08"],
  ["How much did Massachusetts Medicaid fraud units recover?", "DL-12"],
  ["How many UI initial claims did Massachusetts file last week?", "DL-14"],
  ["What is Massachusetts manufacturing GDP?", "DL-15"],
  ["What is the Case-Shiller Boston house price index?", "DL-16"],
  ["How urban is Massachusetts under the rural-urban continuum?", "DL-17"],
  ["Which Massachusetts county has the most AGI?", "DL-21"],
  ["What is FTA NTD agency operating cost for the MBTA?", "DL-22"],
  ["How much has FEMA obligated to Massachusetts?", "DL-23"],
  ["How much energy production does Massachusetts have?", "DL-24"],
  ["What towns are population peers of Boston?", "DL-25"],
  ["How much is Massachusetts quasi-public payroll?", "DL-30"],
  ["How much is the Massachusetts House Speaker paid?", "DL-32"],
  ["How much did Massachusetts legislators earn in 2025?", "DL-32"],
];

const CORE_BUDGET = 50000; // bytes of JSON per tool; twenty cores must stay well under context
const CORES_PROJECTED_BUDGET = 500000; // 20 * average core, in bytes

let failures = 0;
function check(ok, msg) {
  if (!ok) {
    failures++;
    console.log("FAIL  " + msg);
  } else {
    console.log("ok    " + msg);
  }
}

check(tools.length >= 31, "five flagships plus the live suite tools are registered (" + tools.length + ")");

for (const t of tools) {
  for (const f of REQUIRED) {
    check(f in t, t.id + " has " + f);
  }
  check(Array.isArray(t.triggers) && t.triggers.length > 0, t.id + " has triggers");
  const core = JSON.stringify(t.coreSlice(t.dataset));
  const full = JSON.stringify(t.modelSlice(t.dataset));
  check(core.length > 200, t.id + " coreSlice is non-empty (" + core.length + " B)");
  check(full.length > 200, t.id + " modelSlice is non-empty (" + full.length + " B)");
  check(core.length <= CORE_BUDGET, t.id + " coreSlice " + core.length + " B is under " + CORE_BUDGET);
  check(core.length <= full.length, t.id + " coreSlice (" + core.length + ") <= modelSlice (" + full.length + ")");
}

for (const [q, tool] of GOLDEN_HITS) {
  const hits = ask.toolsMatching(q).map(function (t) { return t.id; });
  check(hits.includes(tool), "golden hit " + tool + " for: " + q + "  (hits: " + hits.join(",") + ")");
  const selected = ask.selectDatasets(q, []);
  check(selected.hits.includes(tool), "selectDatasets lists " + tool + " as a full-slice hit");
  const manifest = tools.find(function (t) { return t.id === tool; });
  const full = JSON.stringify(manifest.modelSlice(manifest.dataset));
  const core = JSON.stringify(manifest.coreSlice(manifest.dataset));
  check(JSON.stringify(selected.full[tool]) === full, "hit " + tool + " ships the full modelSlice");
  check(JSON.stringify(selected.cores[tool]) === core, "hit " + tool + " still ships its coreSlice");
}

const nohit = ask.selectDatasets("What will the weather be in Boston tomorrow?", []);
check(nohit.hits.length === 0, "weather is a no-hit question (hits: " + nohit.hits.join(",") + ")");
check(Object.keys(nohit.full).length === 0, "no-hit questions ship no DATASETS_FULL upgrades");
for (const t of tools) {
  const core = JSON.stringify(t.coreSlice(t.dataset));
  check(JSON.stringify(nohit.cores[t.id]) === core, t.id + " ships coreSlice on a no-hit question");
}

check(!ask.matchesTrigger("stable", "t"), "single-letter trigger would be whole-word only");
check(ask.matchesTrigger("is the t back", "the t"), "'the t' matches the ridership golden");

const catalog = require("../catalog.json");
function catalogAiIds(node, ids) {
  if (!node) return ids;
  if (Array.isArray(node)) {
    node.forEach(function (n) { catalogAiIds(n, ids); });
    return ids;
  }
  if (typeof node === "object") {
    if (node.ai === true && node.id) ids.push(node.id);
    Object.keys(node).forEach(function (k) { catalogAiIds(node[k], ids); });
  }
  return ids;
}
const catalogIds = catalogAiIds(catalog, []).sort();
const toolIds = tools.map(function (t) { return t.id; }).sort();
check(
  JSON.stringify(catalogIds) === JSON.stringify(toolIds),
  "catalog.json ai:true ids match tools.js (" + catalogIds.join(",") + ")"
);

const cores = tools.reduce(function (n, t) {
  return n + JSON.stringify(t.coreSlice(t.dataset)).length;
}, 0);
const projected20 = Math.round(cores / tools.length * 20);
check(projected20 < CORES_PROJECTED_BUDGET, "twenty average cores project to " + projected20 + " B (budget " + CORES_PROJECTED_BUDGET + ")");
console.log("      current cores total " + cores + " B; 20-tool projection " + projected20 + " B");

if (failures) {
  console.log("\n" + failures + " engine check failures");
  process.exit(1);
}
console.log("\nall engine payload checks pass");
