// Rebuild cores.json and tool-flags.json from the live ledgers.
// Run at inject time. Parses every ledger once on the build machine so
// the ask function can ship cores without parsing 7 MB on cold start.
process.env.DATALABS_COMPUTE_CORES = "1";

import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const FN = path.join(ROOT, "netlify", "functions");

const tools = require("../netlify/functions/tools.js");

function hasTrend(d) {
  const t = d && d.trend;
  if (!t) return false;
  if (Array.isArray(t)) return t.length >= 2;
  return Object.keys(t).some(function (k) {
    return t[k] && t[k].length >= 2;
  });
}

const cores = {};
const flags = {};
for (const t of tools) {
  const d = t.dataset;
  cores[t.id] = t.coreSlice(d);
  flags[t.id] = {
    slug: d.slug || null,
    hasTrend: hasTrend(d),
    scope: t.scope || "",
    title: d.title || "",
    as_of: d.as_of || "",
    data_month_label: d.data_month_label || "",
    vintage_note: d.vintage_note || "",
  };
}

function writeStable(rel, obj) {
  const dest = path.join(FN, rel);
  const body = JSON.stringify(obj);
  const prev = fs.existsSync(dest) ? fs.readFileSync(dest, "utf8") : "";
  if (prev === body) return false;
  fs.writeFileSync(dest, body);
  return true;
}

const coreChanged = writeStable("cores.json", cores);
const flagChanged = writeStable("tool-flags.json", flags);
const coreBytes = Buffer.byteLength(JSON.stringify(cores));
console.log(
  "write_engine_payload: cores " + coreBytes + " B, " +
  Object.keys(cores).length + " tools" +
  (coreChanged || flagChanged ? " (updated)" : " (unchanged)")
);
