// Pioneer DataLabs unified engine: Netlify Function, v2.
// Two-stage, manifest-driven. Stage 1 (router, Haiku): the catalog plus each
// tool's scope decide answer / route / decline; no datasets are shipped.
// Stage 2 (answer, Sonnet): only the routed tool's dataset and rules are sent,
// under a per-tool JSON schema enforced by structured outputs. Both stages use
// prompt caching on their static system blocks, carry the visitor's recent
// exchanges, and never parse free-form model text.
// Holds the Anthropic API key server-side (env var ANTHROPIC_API_KEY).

const BUNDLED_CATALOG = require('./catalog.json'); // fallback only
const TOOLS = require('./tools.js');

const ROUTER_MODEL = 'claude-haiku-4-5';
// Sonnet 5: adaptive thinking is ON when the thinking param is omitted, and
// max_tokens caps thinking plus the answer, so the answer call carries a
// generous cap and effort medium (comparable to Sonnet 4.6 at high) to keep
// latency inside the function budget. effort is NOT sent on the Haiku router,
// which rejects it.
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

// ---------- schemas (structured outputs) ----------

const TOOL_IDS = TOOLS.map(function (t) { return t.id; });

const ROUTE_SCHEMA = {
  type: 'object',
  properties: {
    decision: { enum: ['answer', 'route', 'none'], description: 'answer = one of the AI-enabled datasets can answer this; route = another catalog tool covers the topic; none = DataLabs does not cover it' },
    tool_id: { enum: TOOL_IDS.concat(['none']), description: 'when decision is answer, the tool whose dataset answers it; otherwise none' },
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
          dashboards: { type: 'array', items: { type: 'string' }, description: 'up to 2 EXACT titles copied verbatim from that tool\'s legacy list; empty if none fits' }
        },
        required: ['id', 'reason', 'dashboards'],
        additionalProperties: false
      }
    },
    note: { type: 'string', description: 'when decision is none: one honest sentence saying DataLabs does not yet cover this; empty otherwise' }
  },
  required: ['decision', 'tool_id', 'see_also', 'matches', 'note'],
  additionalProperties: false
};

function answerSchema(tool) {
  const props = {
    answerable: { type: 'boolean', description: 'false ONLY if this dataset cannot actually support the question or the question is out of scope; then text is one honest sentence saying so' },
    text: { type: 'string', description: 'the headline answer, maximum three sentences, plain language' },
    detail: { type: 'string', description: 'two to four MORE sentences that go one level deeper: the trend behind the number, how it compares, and one driver or caveat the dataset supports; never restate the headline; empty when answerable is false' },
    highlight: { anyOf: [{ type: 'string' }, { type: 'null' }], description: tool.highlight.describe },
    followups: { type: 'array', items: { type: 'string' }, description: 'two short related questions the dataset CAN answer. When answerable is false these matter most: offer the two nearest questions the dataset does support' }
  };
  const req = ['answerable', 'text', 'detail', 'highlight', 'followups'];
  if (tool.charts) {
    props.chart = { enum: tool.charts.concat(['none']), description: 'you never output numbers for the chart; you only SELECT which pre-built view best illustrates the answer' };
    req.push('chart');
  }
  if (tool.views) {
    props.view = { enum: tool.views, description: 'which page view best frames the answer' };
    req.push('view');
  }
  return { type: 'object', properties: props, required: req, additionalProperties: false };
}

// ---------- prompts ----------

const ROUTER_RULES = 'You are the router for Pioneer Institute DataLabs\' question box. You receive a CATALOG of topic categories (each listing its dashboards by exact title in legacy arrays), the scope of each AI-enabled dataset, and a visitor question, possibly with recent exchanges for context.\n\nDecide exactly one of:\n- answer: one of the AI-enabled datasets below can answer the question from its own data. An exclusion removes ONLY exactly what it names; never stretch it to a related topic the same scope lists as covered (for example, a dataset that covers farebox recovery and cost per trip still answers those even though it excludes the fare prices riders pay). An excluded question is NOT an answer for that tool.\n- route: a different catalog tool covers the topic. Fill matches with 1 to 3 tools, best first; dashboards must be EXACT titles from that tool\'s legacy arrays, or an empty array.\n- none: DataLabs does not cover it (including everything every dataset excludes, like personal advice or predictions). Write one honest sentence in note.\n\nPrefer answer over route: whenever an AI-enabled dataset\'s scope covers the question, choose answer for that dataset; only choose route when no dataset covers the topic but a catalog tool does. A plain current-fact lookup that a dataset holds (for example one state\'s current top income tax rate) is an answer, not a route.\n\nWhen decision is answer, also list up to 2 OTHER relevant tools in see_also (never the answering tool itself).\nNever invent tool or category ids; use ids exactly as they appear. Never state statistics in reasons. No em dashes anywhere.\n\nAI-enabled datasets:\n' + TOOLS.map(function (t) { return '- ' + t.id + ': ' + t.routerScope; }).join('\n');

const GLOBAL_ANSWER_RULES = 'You are the answer engine behind Pioneer Institute DataLabs\' question box. You receive one DATASET and a visitor question, possibly with recent exchanges for context.\n\nUse ONLY the dataset, never outside knowledge. Every figure cites its source as the tool rules specify. Plain language, no bullet points, no markdown. detail must add substance beyond the headline, never restate it. If the question cannot actually be supported by this dataset, set answerable to false; then text is one or two honest sentences saying what is not covered AND what the dataset does track instead, and followups offer the two nearest questions the dataset CAN answer; never improvise or estimate. No em dashes anywhere; use commas, colons, or middots.\n\n';

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
    const catalog = await getCatalog();
    const messages = buildMessages(history, question);

    // Stage 1: route. Static rules first, catalog last with the cache marker,
    // so the whole prefix caches until the catalog refreshes.
    const route = await callModel(ROUTER_MODEL, [
      { type: 'text', text: ROUTER_RULES },
      { type: 'text', text: 'CATALOG:\n' + JSON.stringify(catalog), cache_control: { type: 'ephemeral' } }
    ], messages, ROUTE_SCHEMA, 700);

    const catalogIds = new Set();
    (Array.isArray(catalog) ? catalog : []).forEach(function (t) { if (t && t.id) catalogIds.add(t.id); });

    let parsed;
    const tool = TOOLS.find(function (t) { return t.id === route.tool_id; });

    if (route.decision === 'answer' && tool) {
      // Stage 2: answer from the one routed dataset.
      const ans = await callModel(ANSWER_MODEL, [
        { type: 'text', text: GLOBAL_ANSWER_RULES + tool.rules },
        { type: 'text', text: 'DATASET:\n' + JSON.stringify(tool.modelSlice(tool.dataset)), cache_control: { type: 'ephemeral' } }
      ], messages, answerSchema(tool), 6000, ANSWER_EFFORT);

      if (ans.answerable === false) {
        // Rich decline: the honest note plus the nearest answerable questions.
        parsed = { type: 'none', note: ans.text || 'The dataset cannot support that question.', followups: (ans.followups || []).slice(0, 2) };
      } else {
        parsed = { type: 'answer', tool_id: tool.id, text: ans.text, detail: ans.detail || '', highlight: ans.highlight, followups: (ans.followups || []).slice(0, 2) };
        // Manifest-driven validation and enrichment.
        if (tool.charts) parsed.chart = tool.charts.includes(ans.chart) ? ans.chart : 'none';
        if (tool.views) parsed.view = tool.views.includes(ans.view) ? ans.view : tool.viewDefault;
        let hl = typeof parsed.highlight === 'string' ? parsed.highlight.trim() : null;
        if (hl && tool.highlight.uppercase) hl = hl.toUpperCase();
        const valid = tool.dataset[tool.highlight.key] || {};
        parsed.highlight = (hl && Object.prototype.hasOwnProperty.call(valid, hl)) ? hl : null;
        parsed.link = tool.link(parsed);
        parsed.src = tool.src(tool.dataset, parsed);
        // Cross-tool pointers from the router, validated against the catalog.
        const seeAlso = (route.see_also || [])
          .filter(function (s) { return s && s.id !== tool.id && catalogIds.has(s.id); })
          .slice(0, 2)
          .map(function (s) {
            const c = catalog.find(function (t) { return t.id === s.id; }) || {};
            return { id: s.id, title: c.t || s.id, url: c.url || null, reason: s.reason || '' };
          });
        if (seeAlso.length) parsed.see_also = seeAlso;
      }
    } else if (route.decision === 'route' && (route.matches || []).length) {
      parsed = { type: 'route', matches: route.matches.filter(function (m) { return m && catalogIds.has(m.id); }).slice(0, 3) };
      if (!parsed.matches.length) parsed = { type: 'none', note: route.note || 'DataLabs does not yet cover this.' };
    } else {
      parsed = { type: 'none', note: route.note || 'DataLabs does not yet cover this.' };
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
