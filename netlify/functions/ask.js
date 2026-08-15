// Pioneer DataLabs unified engine: Netlify Function, v4.
// Single-stage, manifest-driven. There is no router: one Sonnet 5 call sees
// the catalog plus the AI-enabled datasets and decides answer / route /
// decline in the same pass, under one JSON schema enforced by structured
// outputs. A two-stage router (scopes first, ledger second) was tried and
// removed: routing without the ledger is where every eval misdecline lived.
// Scaling to many tools is done by shrinking the payload, not by splitting
// the decision. Every tool always ships a small coreSlice; a trigger hit
// upgrades that tool to its full modelSlice. Prompt caching covers the
// static rules on their own breakpoint (the catalog, which refreshes every
// 5 minutes, sits behind a second), the visitor's recent exchanges ride
// along, and no free-form model text is ever parsed.
// Holds the Anthropic API key server-side (env var ANTHROPIC_API_KEY).

const BUNDLED_CATALOG = require('./catalog.json'); // fallback only
const TOOLS = require('./tools.js');

// ---------- payload selection (how 3 tools become 20 without a router) ----------
// A two-stage router that decided from scopes alone failed eval: it declined
// questions the ledgers fully cover. The decision stays single-stage. What
// scales is the payload: every tool always contributes a small coreSlice;
// a trigger hit upgrades that tool to its full modelSlice. A miss cannot
// hide a tool, so a thin trigger list is safe.

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function matchesTrigger(text, trigger) {
  const q = String(text || '').toLowerCase();
  const tr = String(trigger || '').toLowerCase().trim();
  if (!tr) return false;
  if (tr.length <= 2) return new RegExp('\\b' + escapeRe(tr) + '\\b').test(q);
  return q.indexOf(tr) !== -1;
}

function questionBlob(question, history) {
  const prior = (history || []).map(function (h) { return h && h.q ? h.q : ''; }).join(' ');
  return String(question || '') + ' ' + prior;
}

function toolsMatching(text) {
  return TOOLS.filter(function (t) {
    return (t.triggers || []).some(function (tr) { return matchesTrigger(text, tr); });
  });
}

function selectDatasets(question, history) {
  const blob = questionBlob(question, history);
  const hits = toolsMatching(blob);
  const cores = {};
  const full = {};
  TOOLS.forEach(function (t) { cores[t.id] = t.coreSlice(t.dataset); });
  hits.forEach(function (t) { full[t.id] = t.modelSlice(t.dataset); });
  return { cores: cores, full: full, hits: hits.map(function (t) { return t.id; }) };
}

// Sonnet 5: adaptive thinking is ON when the thinking param is omitted, and
// max_tokens caps thinking plus the answer, so the call carries a generous cap
// and effort medium (comparable to Sonnet 4.6 at high) to keep latency inside
// the function budget.
const ANSWER_MODEL = 'claude-sonnet-5';
const ANSWER_EFFORT = 'medium';

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

// ---------- schema (structured outputs) ----------

const TOOL_IDS = TOOLS.map(function (t) { return t.id; });
const ALL_CHARTS = Array.from(new Set(TOOLS.reduce(function (a, t) { return t.charts ? a.concat(t.charts) : a; }, [])));
const ALL_VIEWS = Array.from(new Set(TOOLS.reduce(function (a, t) { return t.views ? a.concat(t.views) : a; }, [])));

// One schema for the whole decision. chart, view, and highlight are validated
// again by the handler against the answering tool's manifest, so a stray value
// can only ever fall back, never break the page.
const ENGINE_SCHEMA = {
  type: 'object',
  properties: {
    decision: { enum: ['answer', 'route', 'none'], description: 'answer = one of the DATASETS answers this from its own data; route = another catalog tool covers the topic; none = DataLabs does not cover it' },
    tool_id: { enum: TOOL_IDS.concat(['none']), description: 'when decision is answer, the tool whose dataset answers it; otherwise none' },
    text: { type: 'string', description: 'when decision is answer: the headline answer, maximum three sentences, plain language; empty otherwise' },
    detail: { type: 'string', description: 'when decision is answer: two to four MORE sentences that go one level deeper: the trend behind the number, how it compares, and one driver or caveat the dataset supports; never restate the headline; empty otherwise' },
    highlight: { anyOf: [{ type: 'string' }, { type: 'null' }], description: 'when the answer focuses on one entity: for DL-03 a mode code (HR, MB, CR, LR, RB, FB, DR); for DL-02 the exact county name as written in county_premiums; for DL-01, DL-04, and the state-ranked suite tools a two-letter jurisdiction code (for example CA, MA, DC, HI); for DL-05 a board id slug (for example state, mtrs, springfield); for municipal or Boston tools the exact entity name in entities; else null' },
    chart: { enum: ALL_CHARTS.concat(['none']), description: 'when decision is answer and the answering tool has charts: which pre-built view best illustrates the answer, per that tool\'s rules; you never output numbers for the chart; none otherwise' },
    view: { enum: ALL_VIEWS.concat(['none']), description: 'when decision is answer and the answering tool has views: which page view best frames the answer, per that tool\'s rules; none otherwise' },
    followups: { type: 'array', items: { type: 'string' }, description: 'when decision is answer: two short related questions the answering dataset CAN answer. When decision is none these matter most: offer the two nearest questions the datasets DO support. Empty when decision is route' },
    see_also: {
      type: 'array',
      description: 'when decision is answer: up to 2 OTHER tools (any catalog id) also relevant to this question, best first; empty if none',
      items: {
        type: 'object',
        properties: { id: { type: 'string' }, reason: { type: 'string', description: 'one plain sentence on coverage, NEVER a statistic' } },
        required: ['id', 'reason'],
        additionalProperties: false
      }
    },
    matches: {
      type: 'array',
      description: 'when decision is route: 1 to 3 catalog tools, best first; empty otherwise',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          reason: { type: 'string', description: 'one plain sentence on coverage, NEVER a statistic' },
          dashboards: { type: 'array', items: { type: 'string' }, description: 'leave empty; the catalog no longer lists partner dashboards' }
        },
        required: ['id', 'reason', 'dashboards'],
        additionalProperties: false
      }
    },
    note: { type: 'string', description: 'when decision is none: one or two honest sentences saying what DataLabs does not cover AND what the nearest dataset does track instead; empty otherwise' }
  },
  required: ['decision', 'tool_id', 'text', 'detail', 'highlight', 'chart', 'view', 'followups', 'see_also', 'matches', 'note'],
  additionalProperties: false
};

// ---------- prompt ----------

const ENGINE_RULES = 'You are the engine behind Pioneer Institute DataLabs\' question box. You receive a CATALOG of native DataLabs applications (ids DL-01 through DL-31), DATASETS_CORE (the answering core of every AI-enabled tool), optional DATASETS_FULL (the complete ledger for the tools most likely to answer; when an id appears in both, prefer FULL), and a visitor question, possibly with recent exchanges for context.\n\nDecide exactly one of:\n- answer: one of the DATASETS answers the question from its own data. Set tool_id and answer from ONLY that dataset, never outside knowledge. An exclusion removes ONLY exactly what it names; never stretch it to a related topic the same scope lists as covered (for example, a dataset that covers farebox recovery and cost per trip still answers those even though it excludes the fare prices riders pay). A plain current-fact lookup that a dataset holds (for example one state\'s current top income tax rate) is an answer, not a route.\n- route: no dataset covers it but a different catalog application covers the topic. Fill matches with 1 to 3 DL-xx ids, best first; leave dashboards empty.\n- none: DataLabs does not cover it (including everything every dataset excludes, like personal advice or predictions). Write one or two honest sentences in note and offer in followups the two nearest questions the datasets CAN answer.\n\nPrefer answer over route: whenever a dataset covers the question, choose answer for that dataset; only choose route when no dataset covers the topic but a catalog application does.\n\nWhen decision is answer: every figure cites its source as the answering tool\'s rules specify. Plain language, no bullet points, no markdown. detail must add substance beyond the headline, never restate it. Set chart and view only as the answering tool\'s rules describe; when the answering tool has no charts or no views, set them to none. Also list up to 2 OTHER relevant tools in see_also (never the answering tool itself). Never improvise or estimate beyond the dataset.\n\nWhere a tool\'s rules say to set answerable to false, that means decision none: put the honest sentences in note and the offered questions in followups.\n\nNever invent tool ids; use DL-xx ids exactly as they appear. Topic headings are not tools. Never state statistics in reasons. No em dashes anywhere; use commas, colons, or middots.\n\nDataset scopes:\n' + TOOLS.map(function (t) { return '- ' + t.id + ': ' + t.scope; }).join('\n') + '\n\nPer-tool answer rules:\n\n' + TOOLS.map(function (t) { return t.rules; }).join('\n\n');

// ---------- model call ----------

async function callModel(model, systemBlocks, messages, schema, maxTokens, effort) {
  const outputConfig = { format: { type: 'json_schema', schema: schema } };
  if (effort) outputConfig.effort = effort;
  const apiRes = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': process.env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: model,
      max_tokens: maxTokens,
      system: systemBlocks,
      messages: messages,
      output_config: outputConfig
    })
  });
  const data = await apiRes.json();
  if (!apiRes.ok) {
    console.error('Anthropic API error (' + model + '):', JSON.stringify(data).slice(0, 500));
    throw new Error('model call failed');
  }
  const text = (data.content || []).filter(function (b) { return b.type === 'text'; })
    .map(function (b) { return b.text; }).join('');
  return JSON.parse(text);
}

// History arrives as [{q, a}] pairs; render as prior turns ahead of the question.
function buildMessages(history, question) {
  const msgs = [];
  (history || []).slice(-2).forEach(function (h) {
    const q = String(h && h.q || '').slice(0, 400).trim();
    const a = String(h && h.a || '').slice(0, 800).trim();
    if (q && a) {
      msgs.push({ role: 'user', content: q });
      msgs.push({ role: 'assistant', content: a });
    }
  });
  msgs.push({ role: 'user', content: question });
  return msgs;
}

// ---------- handler ----------

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

  let question, history;
  try {
    const body = JSON.parse(event.body);
    question = String(body.question || '').slice(0, 400).trim();
    history = Array.isArray(body.history) ? body.history : [];
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'bad request' }) };
  }
  if (!question) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'empty question' }) };
  }

  try {
    const catalog = (await getCatalog()).filter(function (t) {
      return t && /^DL-\d+/.test(String(t.id || ''));
    });
    const messages = buildMessages(history, question);

    // One call. Rules, then every core (static per deploy) behind its own
    // cache breakpoint, then the catalog behind a second, then the full
    // ledgers for trigger hits last so a hit pattern never invalidates the
    // cached prefix. This is how 20 tools stay one call without a router.
    const selected = selectDatasets(question, history);
    const out = await callModel(ANSWER_MODEL, [
      { type: 'text', text: ENGINE_RULES },
      { type: 'text', text: 'DATASETS_CORE:\n' + JSON.stringify(selected.cores), cache_control: { type: 'ephemeral' } },
      { type: 'text', text: 'CATALOG:\n' + JSON.stringify(catalog), cache_control: { type: 'ephemeral' } },
      { type: 'text', text: 'DATASETS_FULL (prefer over CORE for the same id):\n' + JSON.stringify(selected.full) }
    ], messages, ENGINE_SCHEMA, 6000, ANSWER_EFFORT);

    const catalogIds = new Set();
    (Array.isArray(catalog) ? catalog : []).forEach(function (t) { if (t && t.id) catalogIds.add(t.id); });

    let parsed;
    const tool = TOOLS.find(function (t) { return t.id === out.tool_id; });

    if (out.decision === 'answer' && tool) {
      parsed = { type: 'answer', tool_id: tool.id, text: out.text, detail: out.detail || '', highlight: out.highlight, followups: (out.followups || []).slice(0, 2) };
      // Manifest-driven validation and enrichment.
      if (tool.charts) parsed.chart = tool.charts.includes(out.chart) ? out.chart : 'none';
      if (tool.views) parsed.view = tool.views.includes(out.view) ? out.view : tool.viewDefault;
      let hl = typeof parsed.highlight === 'string' ? parsed.highlight.trim() : null;
      if (hl && tool.highlight.uppercase) hl = hl.toUpperCase();
      const valid = tool.dataset[tool.highlight.key] || {};
      parsed.highlight = (hl && Object.prototype.hasOwnProperty.call(valid, hl)) ? hl : null;
      parsed.link = tool.link(parsed);
      parsed.src = tool.src(tool.dataset, parsed);
      // Cross-tool pointers, validated against the catalog.
      const seeAlso = (out.see_also || [])
        .filter(function (s) { return s && s.id !== tool.id && catalogIds.has(s.id); })
        .slice(0, 2)
        .map(function (s) {
          const c = catalog.find(function (t) { return t.id === s.id; }) || {};
          return { id: s.id, title: c.t || s.id, url: c.url || null, reason: s.reason || '' };
        });
      if (seeAlso.length) parsed.see_also = seeAlso;
    } else if (out.decision === 'route' && (out.matches || []).length) {
      parsed = { type: 'route', matches: out.matches.filter(function (m) { return m && catalogIds.has(m.id); }).slice(0, 3) };
      if (!parsed.matches.length) parsed = { type: 'none', note: out.note || 'DataLabs does not yet cover this.' };
    } else {
      // Rich decline: the honest note plus the nearest answerable questions.
      parsed = { type: 'none', note: out.note || 'DataLabs does not yet cover this.', followups: (out.followups || []).slice(0, 2) };
    }

    // Question log: every question, its outcome, and destination.
    // Declines carry the engine's note; they are the research agenda input.
    const logEntry = {
      at: new Date().toISOString(),
      q: question,
      type: parsed.type,
      tool: parsed.type === 'answer' ? parsed.tool_id
          : parsed.type === 'route' ? (parsed.matches || []).map(function (m) { return m.id; }).join('|')
          : '',
      note: parsed.type === 'none' ? (parsed.note || '') : ''
    };
    console.log(JSON.stringify(logEntry));

    // Durable log: webhook to a spreadsheet (see SETUP.md Step 6).
    // Fire-and-forget with a timeout; logging can never break the ask box.
    if (process.env.QUESTION_LOG_URL) {
      try {
        await Promise.race([
          fetch(process.env.QUESTION_LOG_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(logEntry)
          }),
          new Promise(function (res) { setTimeout(res, 1500); })
        ]);
      } catch (e) { console.error('question log webhook failed:', e.message); }
    }

    return { statusCode: 200, headers, body: JSON.stringify(parsed) };
  } catch (err) {
    console.error('engine error:', err.message);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'engine unavailable' }) };
  }
};

exports.selectDatasets = selectDatasets;
exports.toolsMatching = toolsMatching;
exports.matchesTrigger = matchesTrigger;
exports.questionBlob = questionBlob;
