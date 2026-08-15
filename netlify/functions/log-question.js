// Built-in question log. ask.js POSTs here when QUESTION_LOG_URL is unset,
// and still POSTs to that webhook when it is set. Fire-and-forget from ask.js.
// GET returns counts only. With QUESTION_LOG_KEY, GET returns recent rows
// (the demand evidence for NEW-TOOL-CHECKLIST.md). Never breaks the ask box.

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
};

function json(status, body) {
  return {
    statusCode: status,
    headers: Object.assign({ 'Content-Type': 'application/json' }, CORS),
    body: JSON.stringify(body)
  };
}

function cleanEntry(raw) {
  const src = raw && typeof raw === 'object' ? raw : {};
  return {
    at: String(src.at || new Date().toISOString()).slice(0, 40),
    q: String(src.q || '').slice(0, 2000),
    type: String(src.type || '').slice(0, 20),
    tool: String(src.tool || '').slice(0, 80),
    note: String(src.note || '').slice(0, 2000)
  };
}

function emptyStore() {
  return { recent: [], counts: { answer: 0, route: 0, none: 0, other: 0, total: 0 } };
}

async function loadStore() {
  try {
    const { getStore } = require('@netlify/blobs');
    const store = getStore('question-log');
    const raw = await store.get('log.json', { type: 'json' });
    if (raw && Array.isArray(raw.recent)) return raw;
  } catch (e) {
    console.error('question-log blob read:', e.message);
  }
  return emptyStore();
}

async function saveStore(data) {
  const { getStore } = require('@netlify/blobs');
  const store = getStore('question-log');
  await store.setJSON('log.json', data);
}

function authorized(event) {
  const key = process.env.QUESTION_LOG_KEY;
  if (!key) return false;
  const header = (event.headers && (event.headers.authorization || event.headers.Authorization)) || '';
  const q = event.queryStringParameters || {};
  return header === 'Bearer ' + key || q.key === key;
}

exports.handler = async function (event) {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS, body: '' };
  }

  if (event.httpMethod === 'POST') {
    let body = {};
    try { body = JSON.parse(event.body || '{}'); } catch (e) { body = {}; }
    const entry = cleanEntry(body);
    if (!entry.q) return json(400, { error: 'missing q' });
    console.log(JSON.stringify({ kind: 'question', at: entry.at, type: entry.type, tool: entry.tool, q: entry.q }));
    try {
      const data = await loadStore();
      data.recent.unshift(entry);
      data.recent = data.recent.slice(0, 500);
      const bucket = Object.prototype.hasOwnProperty.call(data.counts, entry.type) ? entry.type : 'other';
      data.counts[bucket] = (data.counts[bucket] || 0) + 1;
      data.counts.total = (data.counts.total || 0) + 1;
      await saveStore(data);
    } catch (e) {
      console.error('question-log blob write:', e.message);
    }
    return { statusCode: 204, headers: CORS, body: '' };
  }

  if (event.httpMethod === 'GET') {
    const data = await loadStore();
    if (authorized(event)) {
      return json(200, { counts: data.counts, recent: data.recent });
    }
    return json(200, { counts: data.counts });
  }

  return json(405, { error: 'method not allowed' });
};
