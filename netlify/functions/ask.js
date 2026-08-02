// Pioneer DataLabs unified engine: Netlify Function
// Holds the Anthropic API key server-side (env var ANTHROPIC_API_KEY).
// Receives {question}, decides: answer from DL-12 data, route to a tool,
// or honestly decline. Returns the engine JSON to the page.

const BUNDLED_CATALOG = require('./catalog.json'); // fallback only
const DL12 = require('./dl12-answers.json');

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

const SYSTEM_PROMPT = `You are the engine behind Pioneer Institute DataLabs' main question box. You receive: a CATALOG of topic categories, each listing its dashboards by exact title, plus the DL-12 flagship (qa flag), a DATASET for tool DL-12 (Transportation and MBTA, the only qa-enabled tool in this pilot), and a visitor QUESTION.

Decide which of three response types applies and respond with ONLY that JSON, no markdown fences:

1. If the question can be answered from the DL-12 DATASET:
{"type":"answer","tool_id":"DL-12","text":"the answer, maximum three sentences, plain language","chart":"one of: monthly_trend | recovery_by_mode | cost_per_trip | farebox | none","highlight":"a mode code (HR, MB, CR, LR, RB, FB, DR) if the question focuses on one mode, else null","followups":["two short related questions the dataset can also answer"]}
   Chart rules: you never output numbers for the chart; you only SELECT which pre-built view best illustrates the answer. monthly_trend = ridership over time or recovery overall; recovery_by_mode = comparing modes vs 2019; cost_per_trip = cost to provide; farebox = share riders pay; none = no view fits.
   Answer rules: use ONLY the dataset, never outside knowledge. Every figure cites its source in parentheses: ridership figures cite (SRC-301); cost per trip and farebox figures cite (LEG-MBTA-01). Derived values say derived, e.g. (derived vs same month 2019, SRC-301). Data runs through the dataset's as_of month. The dataset's scope field lists exclusions (safety, reliability, debt, fares charged, other agencies): if the question is about those, this is NOT answerable, fall through to type 2 or 3. If and only if the answer uses cost per trip or farebox figures, end the text with: "Cost figures are pending verification." Never call ridership figures prototype or pending; they are verified against FTA NTD.

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
                   '\n\nQUESTION: ' + question
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

    // Coverage-gap log: unanswered questions appear in the Netlify function log.
    if (parsed.type === 'none') {
      console.log(JSON.stringify({ gap: question, at: new Date().toISOString() }));
    }

    return { statusCode: 200, headers, body: JSON.stringify(parsed) };
  } catch (err) {
    console.error('engine error:', err.message);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'engine unavailable' }) };
  }
};
