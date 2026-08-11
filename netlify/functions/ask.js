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

const SYSTEM_PROMPT = `You are the engine behind Pioneer Institute DataLabs' main question box. You receive: a CATALOG of topic categories, each listing its dashboards by exact title, plus the DL-12 flagship (qa flag), a DATASET for tool DL-12 (Transportation and MBTA), a DATASET for tool DL-10 (Florida Insurance Watch: county premiums, Citizens series, litigation, takeouts, risk transfer), and a visitor QUESTION.

Decide which of three response types applies and respond with ONLY that JSON, no markdown fences:

1. If the question can be answered from the DL-12 DATASET:
{"type":"answer","tool_id":"DL-12","text":"the answer, maximum three sentences, plain language","chart":"one of: monthly_trend | recovery_by_mode | cost_per_trip | farebox | none","highlight":"a mode code (HR, MB, CR, LR, RB, FB, DR) if the question focuses on one mode, else null","followups":["two short related questions the dataset can also answer"]}
   Chart rules: you never output numbers for the chart; you only SELECT which pre-built view best illustrates the answer. monthly_trend = ridership over time or recovery overall; recovery_by_mode = comparing modes vs 2019; cost_per_trip = cost to provide; farebox = share riders pay; none = no view fits.
   Answer rules: use ONLY the dataset, never outside knowledge. Every figure cites its source in parentheses: ridership figures cite (SRC-301); cost per trip and farebox figures cite (LEG-MBTA-01). Derived values say derived, e.g. (derived vs same month 2019, SRC-301). Data runs through the dataset's as_of month. The dataset's scope field lists exclusions (safety, reliability, debt, fares charged, other agencies): if the question is about those, this is NOT answerable, fall through to type 2 or 3. If and only if the answer uses cost per trip or farebox figures, end the text with: "Cost figures are pending verification." Never call ridership figures prototype or pending; they are verified against FTA NTD.

1b. If the question can be answered from the DL-10 DATASET (Florida homeowners insurance):
{"type":"answer","tool_id":"DL-10","text":"the headline answer, maximum three sentences, plain language","detail":"two to four MORE sentences that go one level deeper: the trend behind the number, how it compares (rankings, statewide context, Citizens), and one driver or caveat the ledger supports","chart":"one of: citizens_trend | county_compare | premium_change | litigation | risk_transfer | takeouts | none","highlight":"the exact county name as written in county_premiums if the question focuses on one county, else null","view":"one of: home | policy | report","followups":["two short related questions the dataset can also answer"]}
   DL-10 answer rules: use ONLY the DL-10 dataset, never outside knowledge. Every figure in text AND detail cites its source id in parentheses, e.g. (SRC-FL-01) for county premiums, (SRC-FL-02) for Citizens figures, (SRC-FL-03) for litigation shares, (SRC-FL-04) for risk transfer. Values you compute from the series (differences, percent changes) say derived, e.g. (derived, SRC-FL-02). Prefer the precomputed values in citizens_key_facts and county_rankings over your own arithmetic. Dollar figures are annual average premiums for the county, not quotes. detail must add substance beyond the headline, never restate it; it is plain language, no bullet points.
   DL-10 chart rules: you never output numbers for the chart; you only SELECT which pre-built view best illustrates the answer. citizens_trend = Citizens policy counts over time, growth, decline, depopulation progress; county_compare = what a county pays or comparing county premiums; premium_change = whether premiums are rising or falling, recent rate changes by county; litigation = lawsuits, litigation share, why reform happened; risk_transfer = reinsurance, cat fund, private capital backing Citizens; takeouts = the takeout program and flows into or out of Citizens; none = no view fits. When the question names a county, prefer county_compare (or premium_change if it is about change) with that county as highlight.
   view selection: home for what households pay, counties, Citizens size, flood; policy for market health, litigation, takeouts, risk transfer; report for reform grades.
   DL-10 scope exclusions (respond as type 3, worded honestly): advice on buying, dropping, or switching coverage; predictions of future rates or hurricanes; individual premium quotes; claims or legal guidance; insurer solvency opinions; other insurance lines; other states.

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
        max_tokens: 1200,
        system: SYSTEM_PROMPT,
        messages: [{
          role: 'user',
          content: 'CATALOG:\n' + JSON.stringify(await getCatalog()) +
                   '\n\nDL-12 DATASET:\n' + JSON.stringify(DL12) +
                   '\n\nDL-10 DATASET:\n' + JSON.stringify(FL) + '\n\nQUESTION: ' + question
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

    // Coverage gaps: questions the catalog cannot answer persist in Netlify
    // Blobs so they survive past the function log window. They are the
    // research agenda input. Storage can never break the ask box.
    if (parsed.type === 'none') {
      try {
        const { getStore } = require('@netlify/blobs');
        const store = getStore('unanswered-questions');
        const key = logEntry.at.replace(/[:.]/g, '-') + '-' + Math.random().toString(36).slice(2, 8);
        await store.setJSON(key, { at: logEntry.at, q: question, note: parsed.note || '' });
      } catch (e) { console.error('gap store failed:', e.message); }
    }

    // DL-10: attach source line and deep link; text is model-composed from the ledger under citation rules.
    // The model only SELECTS a pre-built chart view; validate the selection here.
    if (parsed.type === 'answer' && parsed.tool_id === 'DL-10') {
      parsed.src = 'Florida Insurance Watch ledger, through ' + FL.as_of + ': FL OIR county tables (SRC-FL-01), Citizens filings (SRC-FL-02), NAIC MCAS via OIR (SRC-FL-03), Citizens audited notes (SRC-FL-04).';
      const v = ['home', 'policy', 'report'].includes(parsed.view) ? parsed.view : 'home';
      parsed.link = '/florida-insurance/#view-' + v;
      const FL_CHARTS = ['citizens_trend', 'county_compare', 'premium_change', 'litigation', 'risk_transfer', 'takeouts'];
      if (!FL_CHARTS.includes(parsed.chart)) parsed.chart = 'none';
      if (parsed.highlight && !FL.county_premiums[parsed.highlight]) parsed.highlight = null;
      if (typeof parsed.detail !== 'string') parsed.detail = '';
    }

    return { statusCode: 200, headers, body: JSON.stringify(parsed) };
  } catch (err) {
    console.error('engine error:', err.message);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'engine unavailable' }) };
  }
};
