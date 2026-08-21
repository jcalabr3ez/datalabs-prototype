// Guard suite page weight. The ask engine already budgets coreSlice.
// Pages must not embed full monthly cubes or ZIP-scale rows.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_BUDGET = 120000;
const EXCEPTIONS = {};

function payloadBytes(html) {
  const begin = html.indexOf("const DL=");
  if (begin < 0) return 0;
  const end = html.indexOf(";", begin);
  if (end < 0) return html.length - begin;
  return Buffer.byteLength(html.slice(begin, end + 1));
}

let failures = 0;
const rows = [];
for (const dir of fs.readdirSync(ROOT)) {
  const page = path.join(ROOT, dir, "index.html");
  if (!fs.existsSync(page)) continue;
  const html = fs.readFileSync(page, "utf8");
  if (!html.includes("DATA:BEGIN") || !html.includes("const DL=")) continue;
  if (!html.includes("suite-runtime.js") && !html.includes("const CHART=")) continue;
  const rel = dir + "/index.html";
  if (html.includes("suite-runtime.js") && !html.includes("window.DL=DL")) {
    failures++;
    console.log("FAIL  " + rel + " suite runtime cannot see const DL (missing window.DL=DL)");
  }
  const n = payloadBytes(html);
  if (!n) continue;
  const budget = EXCEPTIONS[rel] || DEFAULT_BUDGET;
  rows.push({ rel, n, budget });
  if (n > budget) {
    failures++;
    console.log("FAIL  " + rel + " const DL= " + n + " B exceeds " + budget);
  } else {
    console.log("ok    " + rel + " const DL= " + n + " B (budget " + budget + ")");
  }
}

rows.sort((a, b) => b.n - a.n);
if (!rows.length) {
  console.error("no suite page payloads found");
  process.exit(1);
}
console.log("heaviest " + rows[0].rel + " " + rows[0].n + " B");
if (failures) {
  console.log(failures + " page payload failures");
  process.exit(1);
}
console.log("page payload: ok");
