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
  ["Is the T back to pre-pandemic ridership?", ["answer"], "DL-12"],
  ["What share of costs do fares cover on the subway?", ["answer"], "DL-12"],
  ["Did the cost of a subway ride in MA go up or down?", ["answer"], "DL-12"],
  ["What does homeowners insurance cost in Miami-Dade?", ["answer"], "DL-10"],
  ["Which states are considering a wealth tax?", ["answer"], "DL-04"],
  ["What is California's top income tax rate?", ["answer"], "DL-04"],
  ["What events should I watch over the next 2 months regarding wealth and high earner taxes?", ["answer"], "DL-04"],
  ["Should I move to Texas to avoid taxes?", ["none"], null],
  ["Will Proposition 40 pass in November?", ["none"], null],
  ["How safe is the MBTA?", ["none", "route"], null],
  ["Where can I find crime data for Boston?", ["route"], null],
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
