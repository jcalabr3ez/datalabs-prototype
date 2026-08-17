// Built-in question log. ask.js writes the same store in-process.
// POST still accepts a row (tests, optional callers). GET returns counts
// only. With QUESTION_LOG_KEY, GET returns recent rows (the demand
// evidence for NEW-TOOL-CHECKLIST.md). Never breaks the ask box.

const store = require('./question-log-store');

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
    const result = await store.appendQuestion(body);
    if (result.error === 'missing q') return json(400, { error: 'missing q' });
    return { statusCode: 204, headers: CORS, body: '' };
  }

  if (event.httpMethod === 'GET') {
    const data = await store.loadStore();
    if (authorized(event)) {
      return json(200, { counts: data.counts, recent: data.recent });
    }
    return json(200, { counts: data.counts });
  }

  return json(405, { error: 'method not allowed' });
};
