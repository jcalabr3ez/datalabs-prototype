// Pioneer DataLabs unified engine: Netlify Function
// Holds the Anthropic API key server-side (env var ANTHROPIC_API_KEY).
// Receives {question}, decides: answer from DL-12 data, route to a tool,
// or honestly decline. Returns the engine JSON to the page.

const BUNDLED_CATALOG = require('./catalog.json'); // fallback only
const DL12 = require('./dl12-answers.json');
const FL = require('./fl-answers.json');
const DL04 = require('./dl04-answers.json');

// Model-facing slice of the tax atlas: the analytical core, minus the per-state
// source URL lists (state_sources), which the handler uses to build the source line.
const DL04_MODEL = {
  tool_id: DL04.tool_id, title: DL04.title, as_of: DL04.as_of,
  horizon: DL04.horizon, scope: DL04.scope, views: DL04.views,
  meta: DL04.meta, states: DL04.states
};
const DL04_VIEWS = ['current', 'proposals', 'ballot', 'future', 'events'];

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

const SYSTEM_PROMPT = `You are the engine behind Pioneer Institute DataLabs' main question box. You receive: a CATALOG of topic categories, each listing its dashboards by exact title, plus the DL-12 flagship (qa flag), a DATASET for tool DL-12 (Transportation and MBTA), a DATASET for tool DL-10 (Florida Insurance Watch: county premiums, Citizens series, litigation, takeouts, risk transfer), a DATASET for tool DL-04 (State Tax Atlas: every jurisdiction's enacted income tax rate and surtax, slated changes already in law, active wealth-tax and surtax proposals, citizen-initiative ballot pathways, and Pioneer's Short-Term Risk tier), and a visitor QUESTION.

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

1c. If the question can be answered from the DL-04 DATASET (State Tax Atlas, all 51 jurisdictions):
{"type":"answer","tool_id":"DL-04","text":"the headline answer, maximum three sentences, plain language","detail":"two to four MORE sentences that go one level deeper: the mechanism, how the jurisdiction compares, the slated or proposed change, or the risk rationale the ledger supports","view":"one of: current | proposals | ballot | future | events","highlight":"the exact two-letter jurisdiction code (for example CA, MA, DC) if the question focuses on one jurisdiction, else null","followups":["two short related questions the dataset can also answer"]}
   DL-04 answer rules: use ONLY the DL-04 dataset, never outside knowledge. Answer from the jurisdiction record fields: topRate, currentStatus, futureRisk, ballot, wealthTax, incomeSurtax, currentNote, futureNote, slated (when present), ballotNote, and the proposals array (bill, title, type, sponsor, structure, status). Translate every code to its meta label in prose and never print the raw code: for example currentStatus surtax_active reads as "surtax in effect", futureRisk very_high reads as "very high", ballot open reads as "direct initiative, simple majority". Cite sources the way the atlas does, by naming in parentheses the instrument already in the record: enacted and proposed measures cite their bill, act, or proposition number, e.g. (SB 3125 / Act 24), (Prop 40), (HJRCA 21); a base top rate with no measure cites (Tax Foundation, 2026); Short-Term Risk tiers and composite scores cite (Pioneer model). Values you compute from the records (differences, rankings, counts) say derived, e.g. (derived). Rate and dollar figures are as written in the record; never recompute a bracket or estimate anyone's tax.
   DL-04 view rules: you never output data for the view; you only SELECT which atlas view best frames the answer. current = a jurisdiction's enacted top rate, surtax, or status; proposals = wealth-tax or surtax vehicles in play; ballot = how a measure can reach the ballot, initiative pathways and thresholds; future = the Short-Term Risk tier and outlook through 2028; events = a dated hearing, ruling, or election on the watch list. When the question names one jurisdiction, set highlight to its two-letter code.
   DL-04 scope exclusions (respond as type 3, worded honestly): personal tax or legal advice; whether to move or relocate to change a tax bill; predicting how a ballot measure, election, or court case will turn out, or where rates go next; calculating an individual's tax or a specific bracket; taxes other than personal income, wealth, and surtax (sales, property, corporate, estate) except where a record already notes them; jurisdictions or years outside the dataset.

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
                   '\n\nDL-10 DATASET:\n' + JSON.stringify(FL) +
                   '\n\nDL-04 DATASET:\n' + JSON.stringify(DL04_MODEL) + '\n\nQUESTION: ' + question
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
    // Declines carry the engine's note; they are the research agenda input.
    const logEntry = {
      at: new Date().toISOString(),
      q: question,
      type: parsed.type,
      tool: parsed.type === 'answer' ? parsed.tool_id
          : parsed.type === 'route' ? (parsed.matches || []).map(m => m.id).join('|')
          : '',
      note: parsed.type === 'none' ? (parsed.note || '') : ''
    };
    console.log(JSON.stringify(logEntry));

    // Durable log: webhook to a spreadsheet (Google Apps Script -> Sheet;
    // the script in SETUP.md keeps unanswered questions on their own tab).
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

    // DL-04: validate the selected view, resolve the highlighted jurisdiction, and
    // attach a deep link plus a source line built from the atlas's own source lists.
    if (parsed.type === 'answer' && parsed.tool_id === 'DL-04') {
      const view = DL04_VIEWS.includes(parsed.view) ? parsed.view : 'current';
      parsed.view = view;
      const hl = typeof parsed.highlight === 'string' ? parsed.highlight.toUpperCase() : null;
      parsed.highlight = (hl && DL04.states[hl]) ? hl : null;
      parsed.link = '/tax-atlas/#view-' + view + (parsed.highlight ? '&state=' + parsed.highlight : '');
      const srcs = DL04.default_sources.map(function (x) { return x.label; });
      if (parsed.highlight && DL04.state_sources[parsed.highlight]) {
        DL04.state_sources[parsed.highlight].forEach(function (x) { srcs.push(x.label); });
      }
      parsed.src = 'State Tax Atlas, law and measures as of ' + DL04.as_of + '. Sources: ' + srcs.join('; ') + '.';
      if (typeof parsed.detail !== 'string') parsed.detail = '';
    }

    return { statusCode: 200, headers, body: JSON.stringify(parsed) };
  } catch (err) {
    console.error('engine error:', err.message);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'engine unavailable' }) };
  }
};
