// Pioneer DataLabs unified engine: Netlify Function
// Holds the Anthropic API key server-side (env var ANTHROPIC_API_KEY).
// Receives {question}, decides: answer from DL-12 data, route to a tool,
// or honestly decline. Returns the engine JSON to the page.

const BUNDLED_CATALOG = require('./catalog.json'); // fallback only
const DL12 = require('./dl12-answers.json');
const FL = require('./fl-answers.json');

let catalogCache = { data: null, at: 0 };
async function getCatalog() {
  // Single source of truth: the site's own catalog.json, cached 5 minutes.
  const now = Date.now();
  if (catalogCache.data && now - catalogCache.at < 300000) return catalogCache.data;
  try {
    const base = process.env.URL || process.env.DEPLOY_URL;
    if (base) {
      const r = await fetch(base + '/catalog.json');
      if (r.ok) {
        catalogCache = { data: await r.json(), at: now };
        return catalogCache.data;
      }
    }
  } catch (e) { console.error('catalog fetch failed, using bundled copy:', e.message); }
  return BUNDLED_CATALOG;
}

const SYSTEM_PROMPT = `You are the engine behind Pioneer Institute DataLabs' main question box. You receive: a CATALOG of topic categories, each listing its dashboards by exact title, plus the DL-12 flagship (qa flag), a DATASET for tool DL-12 (Transportation and MBTA), an FL_ANSWERS block for tool DL-10 (Florida Insurance Watch: verified answer ids with their questions, plus a county list), and a visitor QUESTION.

Decide which of three response types applies and respond with ONLY that JSON, no markdown fences:

1. If the question can be answered from the DL-12 DATASET:
{"type":"answer","tool_id":"DL-12","text":"the answer, maximum three sentences, plain language","chart":"one of: monthly_trend | recovery_by_mode | cost_per_trip | farebox | none","highlight":"a mode code (HR, MB, CR, LR, RB, FB, DR) if the question focuses on one mode, else null","followups":["two short related questions the dataset can also answer"]}
   Chart rules: you never output numbers for the chart; you only SELECT which pre-built view best illustrates the answer. monthly_trend = ridership over time or recovery overall; recovery_by_mode = comparing modes vs 2019; cost_per_trip = cost to provide; farebox = share riders pay; none = no view fits.
   Answer rules: use ONLY the dataset, never outside knowledge. Every figure cites its source in parentheses: ridership figures cite (SRC-301); cost per trip and farebox figures cite (LEG-MBTA-01). Derived values say derived, e.g. (derived vs same month 2019, SRC-301). Data runs through the dataset's as_of month. The dataset's scope field lists exclusions (safety, reliability, debt, fares charged, other agencies): if the question is about those, this is NOT answerable, fall through to type 2 or 3. If and only if the answer uses cost per trip or farebox figures, end the text with: "Cost figures are pending verification." Never call ridership figures prototype or pending; they are verified against FTA NTD.

1b. If the question is about Florida homeowners insurance and matches one of the FL_ANSWERS ids:
{"type":"answer","tool_id":"DL-10","answer_id":"the matching id","county":null}
   If the question asks about a SPECIFIC county's premium or cost and that county appears in the county list:
{"type":"answer","tool_id":"DL-10","answer_id":"FL-COUNTY","county":"Exact county name from the list"}
   DL-10 rules: you NEVER write answer text or numbers for DL-10; you only select. The verified text is attached by the server. Florida scope exclusions (respond as type 3, worded honestly): advice on buying, dropping, or switching coverage; predictions of future rates or hurricanes; individual premium quotes; claims or legal guidance; insurer solvency opinions; other insurance lines; other states' insurance.

2. Else if another catalog tool covers the topic:
{"type":"route","matches":[{"id":"DL-XX","reason":"one plain sentence on coverage, NEVER a statistic","dashboards":["up to 2 EXACT titles copied verbatim from that tool's legacy list that best answer the question"]}]}
   1 to 3 matches, best first. dashboards must be exact titles from the catalog's legacy arrays (they map to working links); use an empty array only if no listed dashboard fits.

3. Else:
{"type":"none","note":"one honest sentence saying DataLabs does not yet cover this"}

Never invent tool or category ids; use ids exactly as they appear in the catalog. Never state statistics in route reasons. No em dashes anywhere.`;

exports.handler = async function (event) {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  };

  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers };
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'POST only' }) };
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'ANTHROPIC_API_KEY is not set in Netlify environment variables' }) };
  }

  let question;
  try {
    question = String(JSON.parse(event.body).question || '').slice(0, 400).trim();
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'bad request' }) };
  }
  if (!question) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'empty question' }) };
  }

  try {
    const apiRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 800,
        system: SYSTEM_PROMPT,
        messages: [{
          role: 'user',
          content: 'CATALOG:\n' + JSON.stringify(await getCatalog()) +
                   '\n\nDL-12 DATASET:\n' + JSON.stringify(DL12) +
                   '\n\nFL_ANSWERS (tool DL-10):\n' + JSON.stringify({ answers: FL.answers.map(a => ({ id: a.id, q: a.q })), counties: Object.keys(FL.counties) }) + '\n\nQUESTION: ' + question
        }]
      })
    });

    const data = await apiRes.json();
    if (!apiRes.ok) {
      console.error('Anthropic API error:', JSON.stringify(data));
      return { statusCode: 502, headers, body: JSON.stringify({ error: 'model call failed' }) };
    }
    const text = (data.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n');
    const parsed = JSON.parse(text.replace(/```json|```/g, '').trim());

    // Question log: every question, its outcome, and destination.
    const logEntry = {
      at: new Date().toISOString(),
      q: question,
      type: parsed.type,
      tool: parsed.type === 'answer' ? parsed.tool_id
          : parsed.type === 'route' ? (parsed.matches || []).map(m => m.id).join('|')
          : ''
    };
    console.log(JSON.stringify(logEntry));

    // Durable log: optional webhook (e.g. Google Apps Script -> Sheet).
    // Set QUESTION_LOG_URL in Netlify environment variables to enable.
    // Fire-and-forget with a timeout; logging can never break the ask box.
    if (process.env.QUESTION_LOG_URL) {
      try {
        await Promise.race([
          fetch(process.env.QUESTION_LOG_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(logEntry)
          }),
          new Promise(res => setTimeout(res, 1500))
        ]);
      } catch (e) { console.error('question log webhook failed:', e.message); }
    }

    // DL-10 answer-selection: the server attaches verified text; the model never writes it.
    if (parsed.type === 'answer' && parsed.tool_id === 'DL-10') {
      if (parsed.answer_id === 'FL-COUNTY' && parsed.county && FL.counties[parsed.county]) {
        const c = FL.counties[parsed.county];
        const d = c.incl_wind_2026_03 - c.incl_wind_2025_09;
        const dir = d < 0 ? 'down $' + Math.abs(d).toLocaleString() + ' from' : (d > 0 ? 'up $' + d.toLocaleString() + ' from' : 'unchanged from');
        parsed.text = 'In ' + parsed.county + ' County, the average homeowners premium including wind coverage was $' +
          c.incl_wind_2026_03.toLocaleString() + ' as of March 2026, ' + dir + ' $' + c.incl_wind_2025_09.toLocaleString() +
          ' in September 2025. Excluding wind, the March 2026 average was $' + c.ex_wind_2026_03.toLocaleString() +
          ' (SRC-FL-01).';
        parsed.view = 'home';
      } else {
        const a2 = FL.answers.find(x => x.id === parsed.answer_id);
        if (a2) { parsed.text = a2.text; parsed.view = a2.view; }
        else { parsed = { type: 'none', note: 'DataLabs does not yet cover that part of the Florida insurance picture.' }; }
      }
      if (parsed.type === 'answer') {
        parsed.src = 'Florida Insurance Watch ledger, through ' + FL.as_of + '. Sources: FL OIR, Citizens, NAIC MCAS (SRC-FL-01, 02, 03).';
        parsed.link = '/florida-insurance/#view-' + (parsed.view || 'home');
        parsed.chart = 'none';
      }
    }

    return { statusCode: 200, headers, body: JSON.stringify(parsed) };
  } catch (err) {
    console.error('engine error:', err.message);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'engine unavailable' }) };
  }
};
