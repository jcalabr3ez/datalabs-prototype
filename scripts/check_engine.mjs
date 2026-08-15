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

check(tools.length >= 4, "at least the four live flagships are registered");

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

const crime = ask.selectDatasets("Where can I find crime data for Boston?", []);
check(crime.hits.length === 0, "crime/Boston is a catalog-route question (no AI-tool hit)");
check(Object.keys(crime.full).length === 0, "no-hit questions ship no DATASETS_FULL upgrades");
for (const t of tools) {
  const core = JSON.stringify(t.coreSlice(t.dataset));
  check(JSON.stringify(crime.cores[t.id]) === core, t.id + " ships coreSlice on a no-hit question");
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
