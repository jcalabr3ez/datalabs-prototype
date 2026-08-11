// Golden-question eval for the DataLabs question engine.
// Runs the REAL ask.js handler (both model stages) under Node against the
// live Anthropic API, and asserts routing and answer shape, not wording.
// Needs ANTHROPIC_API_KEY in the environment. Run: node scripts/eval_engine.mjs
//
// This is the regression net for prompt changes: the "rates are outside the
// scope" misdecline class is exactly what these assertions catch.
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

delete process.env.URL;         // force the bundled catalog, not a deploy URL
delete process.env.DEPLOY_URL;
const { handler } = require("../netlify/functions/ask.js");

const GOLDEN = [
  // [question, expected types, expected tool when answer, must-have fields]
  ["Is the T back to pre-pandemic ridership?", ["answer"], "DL-12"],
  ["What share of costs do fares cover on the subway?", ["answer"], "DL-12"],
  ["What does homeowners insurance cost in Miami-Dade?", ["answer"], "DL-10"],
  ["Which states are considering a wealth tax?", ["answer"], "DL-04"],
  ["What is California's top income tax rate?", ["answer"], "DL-04"],
  ["Should I move to Texas to avoid taxes?", ["none"], null],
  ["Will Proposition 40 pass in November?", ["none"], null],
  ["How safe is the MBTA?", ["none", "route"], null],
  ["Where can I find crime data for Boston?", ["route"], null],
];

let failures = 0;
for (const [q, types, tool] of GOLDEN) {
  const res = await handler({ httpMethod: "POST", body: JSON.stringify({ question: q }) });
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
