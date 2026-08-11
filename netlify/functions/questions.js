// Pioneer DataLabs: list the stored unanswered questions (the coverage gaps).
// GET /.netlify/functions/questions          -> newest first, JSON
// GET /.netlify/functions/questions?key=...  -> required only if QUESTIONS_KEY is set
// Entries are written by ask.js whenever the engine declines a question.

exports.handler = async function (event) {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': 'no-store'
  };

  if (event.httpMethod !== 'GET') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'GET only' }) };
  }

  const required = process.env.QUESTIONS_KEY;
  const given = (event.queryStringParameters || {}).key || '';
  if (required && given !== required) {
    return { statusCode: 401, headers, body: JSON.stringify({ error: 'a valid ?key= is required on this site' }) };
  }

  try {
    const { getStore } = require('@netlify/blobs');
    const store = getStore('unanswered-questions');
    const { blobs } = await store.list();
    // Keys start with the ISO timestamp, so a reverse sort is newest first.
    const keys = blobs.map(b => b.key).sort().reverse().slice(0, 500);
    const items = (await Promise.all(keys.map(async k => {
      try { return await store.get(k, { type: 'json' }); } catch (e) { return null; }
    }))).filter(Boolean);
    return {
      statusCode: 200, headers,
      body: JSON.stringify({ total_stored: blobs.length, showing: items.length, questions: items })
    };
  } catch (e) {
    console.error('questions list failed:', e.message);
    return {
      statusCode: 500, headers,
      body: JSON.stringify({ error: 'The question store is not reachable. If this deploy is new, the store is created the first time a question is declined.' })
    };
  }
};
