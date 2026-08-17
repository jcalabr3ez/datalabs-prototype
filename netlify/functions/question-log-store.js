// Shared question-log store. ask.js writes here in-process so a site
// visitor password cannot block the row. log-question.js reads the same
// blob for counts and, with QUESTION_LOG_KEY, recent questions.

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

async function appendQuestion(raw) {
  const entry = cleanEntry(raw);
  if (!entry.q) return { ok: false, error: 'missing q', entry: entry };
  console.log(JSON.stringify({ kind: 'question', at: entry.at, type: entry.type, tool: entry.tool, q: entry.q }));
  try {
    const data = await loadStore();
    data.recent.unshift(entry);
    data.recent = data.recent.slice(0, 500);
    const bucket = Object.prototype.hasOwnProperty.call(data.counts, entry.type) ? entry.type : 'other';
    data.counts[bucket] = (data.counts[bucket] || 0) + 1;
    data.counts.total = (data.counts.total || 0) + 1;
    await saveStore(data);
    return { ok: true, entry: entry, counts: data.counts };
  } catch (e) {
    console.error('question-log blob write:', e.message);
    return { ok: false, error: e.message, entry: entry };
  }
}

module.exports = { cleanEntry, emptyStore, loadStore, appendQuestion };
