// Pioneer DataLabs unified engine: Netlify Function, v4.
// Single-stage, manifest-driven. There is no router: one Sonnet 5 call sees
// the catalog plus the AI-enabled datasets and decides answer / route /
// decline in the same pass, under one JSON schema enforced by structured
// outputs. A two-stage router (scopes first, ledger second) was tried and
// removed: routing without the ledger is where every eval misdecline lived.
// Scaling to many tools is done by shrinking the payload, not by splitting
// the decision. Every tool can ship a small coreSlice; a trigger hit
// upgrades that tool to a slim modelSlice (51-state rows and district
// summaries, not ZIP files or raw state cubes). Questions that name a
// place, a Census region, or a vertical drop cores that cannot apply.
// Housing questions include housing units and units permitted, not only
// the bigram housing permit. A named Census region also ships those
// published state rows. The five flagships and every trigger hit still
// ship. Prompt caching covers the static rules and cores, then the
// bundled catalog, so a hit pattern never invalidates the cached prefix.
// The visitor's recent exchanges ride along, and no free-form model
// text is ever parsed.
// Holds the Anthropic API key server-side (env var ANTHROPIC_API_KEY).

const BUNDLED_CATALOG = require('./catalog.json');
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

var FLAGSHIP = { 'DL-01': 1, 'DL-02': 1, 'DL-03': 1, 'DL-04': 1, 'DL-05': 1 };

var TOOL_META = {};
(BUNDLED_CATALOG || []).forEach(function (row) {
  if (row && row.id && String(row.id).indexOf('DL-') === 0) {
    TOOL_META[row.id] = {
      g: (row.g && row.g[0]) || 'US',
      group: row.group || ''
    };
  }
});

var STATE_NAMES = [
  'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
  'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
  'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine',
  'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi',
  'missouri', 'montana', 'nebraska', 'nevada', 'new hampshire', 'new jersey',
  'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
  'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina',
  'south dakota', 'tennessee', 'texas', 'utah', 'vermont', 'virginia',
  'washington', 'west virginia', 'wisconsin', 'wyoming', 'district of columbia'
];

var VERTICALS = [
  { group: 'Education', re: /\bnaep\b|\benrollment\b|\bschool\b|\bschools\b|\bcollege\b|\bcharter\b|\bpupil\b|\bmcas\b|\bstudent\b|\bfaculty\b|\btuition\b|\bkindergarten\b|\bk-12\b|\bk12\b/ },
  { group: 'Healthcare', re: /\bhospital\b|\bmedicaid\b|\bhealthcare\b|\bhealth care\b|\bout-of-pocket\b|\bmhis\b|\bunderinsured\b/ },
  { group: '340B', re: /\b340b\b/ },
  { group: 'Economy & Jobs', re: /\bunemployment\b|\bgdp\b|\bbusiness application\b|\bbusiness formation\b|\bmigration\b|\bcost of living\b|\blabor force\b|\blabor-force\b|\bjobless\b|\bui claims\b|\bparticipation rate\b/ },
  { group: 'Housing', re: /\bhousing permit|\bbuilding permit|\bhousing units\b|\bunits authorized\b|\bunits permitted\b|\bpermit-issuing\b|\bhousing production\b|\bcase-shiller\b|\bcase shiller\b|\bhouse price\b/ },
  { group: 'Taxation', re: /\btaxpayer\b|\bagi\b|\btax collection\b|\bwealth tax\b|\bincome tax\b|\bsurtax\b/ },
  { group: 'Transportation & Infrastructure', re: /\btransit\b|\bridership\b|\bvmt\b|\bvehicle-miles\b|\bmbta\b|\bthe t\b/ },
  { group: 'Energy', re: /\belectricity\b|\bkilowatthour\b|\bkwh\b|\bemissions\b|\bco2\b/ },
  { group: 'Your City & Town', re: /\btown\b|\bcity and town\b|\bmunicipal\b|\blexington\b|\bmedian household\b/ },
  { group: 'Crime & Justice', re: /\bprison\b|\bimprison\b|\binmate\b/ },
  { group: 'State Government & Spending', re: /\blegislature\b|\bpayroll\b|\bspeaker\b|\bsenate president\b|\bvendor\b/ },
  { group: 'Public Pensions', re: /\bpension\b|\bfunded ratio\b|\bperac\b|\bretiree\b/ }
];

// Same Census region lists as the fifty-state page chips in suite-runtime.js.
// "north east" is the nine-state Northeast, not New England.
var CENSUS_REGIONS = [
  { id: 'northeast', label: 'Census Northeast', re: /\bnorth[\s-]?east\b/, sts: ['CT', 'ME', 'MA', 'NH', 'RI', 'VT', 'NJ', 'NY', 'PA'] },
  { id: 'new_england', label: 'New England', re: /\bnew england\b/, sts: ['CT', 'ME', 'MA', 'NH', 'RI', 'VT'] },
  { id: 'midwest', label: 'Census Midwest', re: /\bmid[\s-]?west\b/, sts: ['IL', 'IN', 'MI', 'OH', 'WI', 'IA', 'KS', 'MN', 'MO', 'NE', 'ND', 'SD'] },
  { id: 'south', label: 'Census South', re: /\bthe south\b|\bsouthern states\b|\bcensus south\b/, sts: ['DE', 'FL', 'GA', 'MD', 'NC', 'SC', 'VA', 'DC', 'WV', 'AL', 'KY', 'MS', 'TN', 'AR', 'LA', 'OK', 'TX'] },
  { id: 'west', label: 'Census West', re: /\bthe west\b|\bwestern states\b|\bcensus west\b/, sts: ['AZ', 'CO', 'ID', 'MT', 'NV', 'NM', 'UT', 'WY', 'AK', 'CA', 'HI', 'OR', 'WA'] }
];

function questionRegion(blob) {
  var t = String(blob || '').toLowerCase();
  for (var i = 0; i < CENSUS_REGIONS.length; i++) {
    if (CENSUS_REGIONS[i].re.test(t)) return CENSUS_REGIONS[i];
  }
  return null;
}

function questionPlace(blob) {
  var q = String(blob || '');
  var t = q.toLowerCase();
  var fl = /\bflorida\b|\bmiami\b|\bmiami-dade\b|\bdade county\b/.test(t);
  var ma = /\bmassachusetts\b|\bcommonwealth\b|\bthe t\b|\bmbta\b/.test(t);
  var boston = /\bboston\b/.test(t);
  var us = /\bunited states\b|\bu\.s\.a?\b|\bnational\b|\bfifty states\b|\bwhich state\b|\bevery state\b|\ball 50\b|\ball fifty\b/.test(t);
  var region = questionRegion(t);
  if (region) us = true;
  var other = false;
  STATE_NAMES.forEach(function (name) {
    if (name === 'florida' || name === 'massachusetts') return;
    if (t.indexOf(name) !== -1) other = true;
  });
  var codes = q.match(/\b[A-Z]{2}\b/g) || [];
  codes.forEach(function (c) {
    if (c === 'MA') ma = true;
    else if (c === 'FL') fl = true;
    else if (c === 'US' || c === 'DC') us = true;
    else other = true;
  });
  if (boston) ma = true;
  return {
    fl: fl, ma: ma, boston: boston, us: us, other: other,
    any: !!(fl || ma || boston || us || other),
    region: region
  };
}

function questionVerticals(blob) {
  var t = String(blob || '').toLowerCase();
  var groups = [];
  VERTICALS.forEach(function (v) {
    if (v.re.test(t)) groups.push(v.group);
  });
  return groups;
}

function keepCore(id, place, groups, hitSet) {
  if (hitSet[id] || FLAGSHIP[id]) return true;
  var meta = TOOL_META[id] || {};
  if (groups.length && groups.indexOf(meta.group) < 0) return false;
  if (place.any) {
    if (meta.g === 'FL' && !place.fl) return false;
    if (meta.g === 'Boston' && !place.boston && !place.ma) return false;
    if (meta.g === 'MA' && !place.ma && !place.boston) return false;
  }
  return true;
}

function regionFocus(region, hits) {
  if (!region) return null;
  var out = { id: region.id, label: region.label, states: region.sts };
  for (var i = 0; i < hits.length; i++) {
    var t = hits[i];
    var slice = t.modelSlice();
    var rows = (slice.rows || []).filter(function (r) {
      return r && region.sts.indexOf(r.st) >= 0;
    });
    if (!rows.length) continue;
    out.tool_id = t.id;
    out.metric_label = slice.metric_label || t.label;
    out.as_of = slice.data_month_label || slice.as_of;
    out.rows = rows.map(function (r) {
      return { st: r.st, name: r.name, v: r.v, rank: r.rank, yoy_pct: r.yoy_pct };
    });
    break;
  }
  return out;
}

function selectDatasets(question, history) {
  const blob = questionBlob(question, history);
  const hits = toolsMatching(blob);
  const hitSet = {};
  hits.forEach(function (t) { hitSet[t.id] = 1; });
  const place = questionPlace(blob);
  const groups = questionVerticals(blob);
  const cores = {};
  const full = {};
  TOOLS.forEach(function (t) {
    if (keepCore(t.id, place, groups, hitSet)) cores[t.id] = t.coreSlice();
  });
  hits.forEach(function (t) { full[t.id] = t.modelSlice(); });
  return {
    cores: cores,
    full: full,
    hits: hits.map(function (t) { return t.id; }),
    region: regionFocus(place.region, hits)
  };
}

// Sonnet 5: adaptive thinking is ON when the thinking param is omitted, and
// max_tokens caps thinking plus the answer, so the call carries a generous cap
// and effort medium (comparable to Sonnet 4.6 at high) to keep latency inside
// the function budget.
const ANSWER_MODEL = 'claude-sonnet-5';
const ANSWER_EFFORT = 'medium';

function catalogForModel(raw) {
  // Bundled catalog only. A live fetch can change bytes and miss the
  // second prompt-cache breakpoint. Route and see_also need id, title,
  // coverage line, and url, not the rest of the catalog row.
  return (Array.isArray(raw) ? raw : []).filter(function (t) {
    return t && /^DL-\d+/.test(String(t.id || ''));
  }).map(function (t) {
    return { id: t.id, t: t.t, q: t.q, url: t.url, st: t.st, g: t.g };
  });
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

const ENGINE_RULES = 'You are the engine behind Pioneer Institute DataLabs\' question box. You receive a CATALOG of native DataLabs applications (ids DL-01 through DL-34), DATASETS_CORE (the answering core of every AI-enabled tool), optional DATASETS_FULL (the complete ledger for the tools most likely to answer; when an id appears in both, prefer FULL), and a visitor question, possibly with recent exchanges for context.\n\nDecide exactly one of:\n- answer: one of the DATASETS answers the question from its own data. Set tool_id and answer from ONLY that dataset, never outside knowledge. An exclusion removes ONLY exactly what it names; never stretch it to a related topic the same scope lists as covered (for example, a dataset that covers farebox recovery and cost per trip still answers those even though it excludes the fare prices riders pay). A plain current-fact lookup that a dataset holds (for example one state\'s current top income tax rate) is an answer, not a route.\n- route: no dataset covers it but a different catalog application covers the topic. Fill matches with 1 to 3 DL-xx ids, best first; leave dashboards empty.\n- none: DataLabs does not cover it (including everything every dataset excludes, like personal advice or predictions). Write one or two honest sentences in note and offer in followups the two nearest questions the datasets CAN answer.\n\nPrefer answer over route: whenever a dataset covers the question, choose answer for that dataset; only choose route when no dataset covers the topic but a catalog application does.\n\nWhen a CENSUS_REGION block is present, compare those published state rows. Do not invent a regional total. Set highlight to null unless the question also names one state.\n\nWhen decision is answer: every figure cites its source as the answering tool\'s rules specify. Plain language, no bullet points, no markdown. detail must add substance beyond the headline, never restate it. Set chart and view only as the answering tool\'s rules describe; when the answering tool has no charts or no views, set them to none. Also list up to 2 OTHER relevant tools in see_also (never the answering tool itself). Never improvise or estimate beyond the dataset.\n\nWhere a tool\'s rules say to set answerable to false, that means decision none: put the honest sentences in note and the offered questions in followups.\n\nNever invent tool ids; use DL-xx ids exactly as they appear. Topic headings are not tools. Never state statistics in reasons. No em dashes anywhere; use commas, colons, or middots.\n\nDataset scopes:\n' + TOOLS.map(function (t) { return '- ' + t.id + ': ' + t.scope; }).join('\n') + '\n\nPer-tool answer rules:\n\n' + TOOLS.map(function (t) { return t.rules; }).join('\n\n');

// ---------- model call ----------

async function callModel(model, systemBlocks, messages, schema, maxTokens, effort) {
  const outputConfig = { format: { type: 'json_schema', schema: schema } };
  if (effort) outputConfig.effort = effort;
  const body = JSON.stringify({
    model: model,
    max_tokens: maxTokens,
    system: systemBlocks,
    messages: messages,
    output_config: outputConfig
  });
  let lastErr = 'model call failed';
  for (let attempt = 0; attempt < 2; attempt++) {
    const apiRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: body
    });
    const data = await apiRes.json();
    if (!apiRes.ok) {
      const kind = (data && data.error && data.error.type) || apiRes.status;
      console.error('Anthropic API error (' + model + '):', JSON.stringify(data).slice(0, 500));
      lastErr = 'model call failed: ' + kind;
      if (attempt === 0 && (apiRes.status === 429 || apiRes.status === 529 || kind === 'overloaded_error')) {
        await new Promise(function (res) { setTimeout(res, 800); });
        continue;
      }
      throw new Error(lastErr);
    }
    const text = (data.content || []).filter(function (b) { return b.type === 'text'; })
      .map(function (b) { return b.text; }).join('');
    try {
      return JSON.parse(text);
    } catch (e) {
      console.error('engine JSON parse failed:', String(text).slice(0, 200));
      throw new Error('model output was not JSON');
    }
  }
  throw new Error(lastErr);
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
    const catalog = catalogForModel(BUNDLED_CATALOG);
    const messages = buildMessages(history, question);

    // One call. Rules, then every core (static per deploy) behind its own
    // cache breakpoint, then the catalog behind a second, then the full
    // ledgers for trigger hits last so a hit pattern never invalidates the
    // cached prefix. This is how 20 tools stay one call without a router.
    const selected = selectDatasets(question, history);
    const systemBlocks = [
      { type: 'text', text: ENGINE_RULES },
      { type: 'text', text: 'DATASETS_CORE:\n' + JSON.stringify(selected.cores), cache_control: { type: 'ephemeral' } },
      { type: 'text', text: 'CATALOG:\n' + JSON.stringify(catalog), cache_control: { type: 'ephemeral' } },
      { type: 'text', text: 'DATASETS_FULL (prefer over CORE for the same id):\n' + JSON.stringify(selected.full) }
    ];
    if (selected.region) {
      systemBlocks.push({
        type: 'text',
        text: 'CENSUS_REGION (published state rows for the named region; do not invent a regional total):\n' + JSON.stringify(selected.region)
      });
    }
    const out = await callModel(ANSWER_MODEL, systemBlocks, messages, ENGINE_SCHEMA, 10000, ANSWER_EFFORT);

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
      parsed.src = tool.src(null, parsed);
      var regionId = selected.region && selected.region.id;
      if (regionId && /^(northeast|midwest|south|west)$/.test(regionId) && parsed.link) {
        var parts = String(parsed.link).split('#');
        var path = parts[0];
        var hash = parts[1] ? '#' + parts[1] : '';
        var sep = path.indexOf('?') >= 0 ? '&' : '?';
        parsed.link = path + sep + 'region=' + regionId + hash;
      }
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
    await recordQuestion({
      at: new Date().toISOString(),
      q: question,
      type: parsed.type,
      tool: parsed.type === 'answer' ? parsed.tool_id
          : parsed.type === 'route' ? (parsed.matches || []).map(function (m) { return m.id; }).join('|')
          : '',
      note: parsed.type === 'none' ? (parsed.note || '') : ''
    }, event);

    return { statusCode: 200, headers, body: JSON.stringify(parsed) };
  } catch (err) {
    console.error('engine error:', err.message);
    await recordQuestion({
      at: new Date().toISOString(),
      q: question,
      type: 'error',
      tool: '',
      note: 'engine unavailable'
    }, event);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'engine unavailable' }) };
  }
};

// Write the row from the Lambda event. getStore() has no environment in
// this handler style unless connectLambda runs; event.blobs already has
// the URL and token. The optional spreadsheet webhook still uses
// QUESTION_LOG_URL (SETUP.md Step 6). Await that POST before returning
// or the runtime freezes and Power Automate never starts a run.
async function postSpreadsheet(logEntry) {
  const url = process.env.QUESTION_LOG_URL;
  if (!url) {
    console.log(JSON.stringify({ kind: 'question-hook', hook: 'skip' }));
    return 'skip';
  }
  const ctl = new AbortController();
  const timer = setTimeout(function () { ctl.abort(); }, 2000);
  try {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        at: logEntry.at,
        q: logEntry.q,
        type: logEntry.type,
        tool: logEntry.tool,
        note: logEntry.note
      }),
      signal: ctl.signal
    });
    const hook = String(r.status);
    console.log(JSON.stringify({ kind: 'question-hook', hook: hook }));
    return hook;
  } catch (e) {
    const hook = e && e.name === 'AbortError' ? 'timeout' : String((e && e.message) || 'fail');
    console.error('question log webhook failed:', hook);
    return hook;
  } finally {
    clearTimeout(timer);
  }
}

async function recordQuestion(logEntry, event) {
  logEntry.hook = await postSpreadsheet(logEntry);
  try {
    await require('./question-log-store').appendQuestion(logEntry, event);
  } catch (e) {
    console.error('question log store failed:', e.message);
  }
}

exports.selectDatasets = selectDatasets;
exports.toolsMatching = toolsMatching;
exports.matchesTrigger = matchesTrigger;
exports.questionBlob = questionBlob;
exports.questionRegion = questionRegion;
