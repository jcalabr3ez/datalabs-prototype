// Golden-question eval for the DataLabs question engine.
// Asserts routing and answer shape, not wording. This is the regression net
// for prompt changes: the "rates are outside the scope" misdecline class is
// exactly what these assertions catch.
//
// Two modes:
//   SITE_URL=https://<site>.netlify.app node scripts/eval_engine.mjs
//     POSTs each question to the LIVE site's ask endpoint. No API key needed
//     anywhere except Netlify, where it already lives. This is how CI runs.
//   node scripts/eval_engine.mjs   (with ANTHROPIC_API_KEY set locally)
//     Runs the ask.js handler in-process against the Anthropic API directly.
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

const SITE_URL = (process.env.SITE_URL || "").replace(/\/+$/, "");
let ask;
if (SITE_URL) {
  ask = async function (body) {
    const r = await fetch(SITE_URL + "/.netlify/functions/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return { statusCode: r.status, body: await r.text() };
  };
  console.log("eval mode: live site endpoint " + SITE_URL + "\n");
} else {
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error("Set SITE_URL (live-endpoint mode) or ANTHROPIC_API_KEY (local mode).");
    process.exit(2);
  }
  delete process.env.URL;       // force the bundled catalog, not a deploy URL
  delete process.env.DEPLOY_URL;
  const { handler } = require("../netlify/functions/ask.js");
  ask = function (body) {
    return handler({ httpMethod: "POST", body: JSON.stringify(body) });
  };
  console.log("eval mode: in-process handler\n");
}

const GOLDEN = [
  // [question, expected types, expected tool when answer, must-have fields]
  ["Is the T back to pre-pandemic ridership?", ["answer"], "DL-03"],
  ["What share of costs do fares cover on the subway?", ["answer"], "DL-03"],
  ["Did the cost of a subway ride in MA go up or down?", ["answer"], "DL-03"],
  ["What does homeowners insurance cost in Miami-Dade?", ["answer"], "DL-02"],
  ["Which states are considering a wealth tax?", ["answer"], "DL-01"],
  ["What is California's top income tax rate?", ["answer"], "DL-01"],
  ["What events should I watch over the next 2 months regarding wealth and high earner taxes?", ["answer"], "DL-01"],
  ["Should I move to Texas to avoid taxes?", ["none"], null],
  ["Will Proposition 40 pass in November?", ["none"], null],
  ["How safe is the MBTA?", ["none", "route"], null],
  ["Where can I find 340B covered-entity counts?", ["answer"], "DL-11"],
  ["What is the average retail electricity price in the United States?", ["answer"], "DL-04"],
  ["How much does electricity cost in Massachusetts?", ["answer"], "DL-04"],
  ["Which state has the highest electricity prices?", ["answer"], "DL-04"],
  ["What will electricity cost next year?", ["none", "route"], null],
  ["What is the funded ratio of the Massachusetts State Retirement Board?", ["answer"], "DL-05"],
  ["How funded is the Mass Teachers retirement system?", ["answer"], "DL-05"],
  ["How much do State and Teacher retirees get paid in Massachusetts?", ["answer"], "DL-05"],
  ["What will my Massachusetts teacher pension be if I retire next year?", ["none", "route"], null],
  ["What does Massachusetts spend per pupil?", ["answer"], "DL-06"],
  ["How many students are enrolled in public K-12 in the United States?", ["answer"], "DL-07"],
  ["Which states improved on NAEP since 2019?", ["answer"], "DL-07"],
  ["How many students are enrolled in college in Massachusetts?", ["answer"], "DL-08"],
  ["How many students are in charter schools in the United States?", ["answer"], "DL-09"],
  ["How many hospitals are in Massachusetts?", ["answer"], "DL-10"],
  ["How much does Massachusetts spend on Medicaid?", ["answer"], "DL-12"],
  ["How many new business applications were filed in the United States?", ["answer"], "DL-13"],
  ["What is the unemployment rate in Massachusetts?", ["answer"], "DL-14"],
  ["What is Massachusetts real GDP?", ["answer"], "DL-15"],
  ["How many housing units were authorized in Massachusetts?", ["answer"], "DL-16"],
  ["What was domestic migration in Massachusetts?", ["answer"], "DL-17"],
  ["What is the cost of living in Massachusetts compared to the US?", ["answer"], "DL-19"],
  ["Are taxpayers leaving Massachusetts?", ["answer"], "DL-20"],
  ["What is Massachusetts adjusted gross income?", ["answer"], "DL-21"],
  ["Which transit agency has the most riders?", ["answer"], "DL-22"],
  ["How many vehicle-miles were driven in Massachusetts?", ["answer"], "DL-23"],
  ["How much CO2 does Massachusetts emit from energy?", ["answer"], "DL-24"],
  ["What is the population of Boston?", ["answer"], "DL-25"],
  ["Which Massachusetts town grew the most since 2020?", ["answer"], "DL-26"],
  ["How much is Boston city payroll?", ["answer"], "DL-27"],
  ["How much tax did Massachusetts collect last quarter?", ["answer"], "DL-28"],
  ["Which state collected the most tax last quarter?", ["answer"], "DL-29"],
  ["How much is Commonwealth payroll?", ["answer"], "DL-30"],
  ["How many prisoners does Massachusetts hold?", ["answer"], "DL-31"],
  ["How much is the Massachusetts House Speaker paid?", ["answer"], "DL-32"],
];

let failures = 0;
for (const [q, types, tool] of GOLDEN) {
  const res = await ask({ question: q });
  let verdict = [];
  let p = {};
  try {
    p = JSON.parse(res.body);
  } catch {
    verdict.push("unparseable body");
  }
  if (res.statusCode !== 200) verdict.push(`status ${res.statusCode}`);
  if (!types.includes(p.type)) verdict.push(`type ${p.type}, wanted ${types.join("|")}`);
  if (tool && p.tool_id !== tool) verdict.push(`tool ${p.tool_id}, wanted ${tool}`);
  if (p.type === "answer") {
    if (!p.src) verdict.push("missing src");
    if (!p.link) verdict.push("missing link");
    if (!p.text || !/\(/.test(p.text)) verdict.push("text lacks a citation");
  }
  const ok = verdict.length === 0;
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${q}`);
  if (!ok) console.log(`      ${verdict.join("; ")}  got: ${JSON.stringify(p).slice(0, 200)}`);
  else console.log(`      -> ${p.type}${p.tool_id ? " " + p.tool_id : ""}${p.link ? " " + p.link : ""}`);
}

console.log(failures ? `\n${failures} failures` : "\nall golden questions pass");
process.exit(failures ? 1 : 0);
