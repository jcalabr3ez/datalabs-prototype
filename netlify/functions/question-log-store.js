// Shared question-log store. Ask and log-question use Lambda-style
// handlers, so @netlify/blobs getStore() has no environment unless
// connectLambda(event) runs. This writes the same site store with
// fetch against event.blobs, which Netlify already puts on the event.

const STORE = 'site:question-log';
const KEY = 'log.json';

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

function header(event, name) {
  const h = (event && event.headers) || {};
  const want = String(name).toLowerCase();
  for (const k of Object.keys(h)) {
    if (k.toLowerCase() === want) return h[k];
  }
  return '';
}

function blobsContext(event) {
  try {
    if (event && event.blobs) {
      const data = JSON.parse(Buffer.from(event.blobs, 'base64').toString('utf8'));
      const siteID = header(event, 'x-nf-site-id') || process.env.SITE_ID || process.env.NETLIFY_SITE_ID || '';
      if (data && data.url && data.token && siteID) {
        return { edgeURL: data.url, token: data.token, siteID: siteID };
      }
    }
  } catch (e) {
    console.error('question-log event.blobs:', e.message);
  }
  try {
    if (process.env.NETLIFY_BLOBS_CONTEXT) {
      const ctx = JSON.parse(Buffer.from(process.env.NETLIFY_BLOBS_CONTEXT, 'base64').toString('utf8'));
      if (ctx && (ctx.edgeURL || ctx.apiURL) && ctx.token && ctx.siteID) return ctx;
    }
  } catch (e) {
    console.error('question-log NETLIFY_BLOBS_CONTEXT:', e.message);
  }
  return null;
}

function blobUrl(ctx) {
  const path = '/' + ctx.siteID + '/' + STORE + '/' + KEY;
  if (ctx.edgeURL) return new URL(path, ctx.edgeURL).toString();
  return new URL('/api/v1/blobs' + path, ctx.apiURL || 'https://api.netlify.com').toString();
}

async function blobRequest(ctx, method, body) {
  const headers = { authorization: 'Bearer ' + ctx.token };
  const opts = { method: method, headers: headers };
  if (body !== undefined) {
    headers['content-type'] = 'application/json';
    headers['cache-control'] = 'max-age=0, stale-while-revalidate=60';
    opts.body = JSON.stringify(body);
  }
  return fetch(blobUrl(ctx), opts);
}

async function loadStore(event) {
  const ctx = blobsContext(event);
  if (!ctx) return { data: emptyStore(), error: 'missing blobs context' };
  try {
    const res = await blobRequest(ctx, 'GET');
    if (res.status === 404) return { data: emptyStore(), error: null };
    if (!res.ok) return { data: emptyStore(), error: 'blob read ' + res.status };
    const raw = await res.json();
    if (raw && Array.isArray(raw.recent)) return { data: raw, error: null };
    return { data: emptyStore(), error: null };
  } catch (e) {
    console.error('question-log blob read:', e.message);
    return { data: emptyStore(), error: e.message };
  }
}

async function saveStore(event, data) {
  const ctx = blobsContext(event);
  if (!ctx) throw new Error('missing blobs context');
  const res = await blobRequest(ctx, 'PUT', data);
  if (!res.ok) throw new Error('blob write ' + res.status);
}

async function appendQuestion(raw, event) {
  const entry = cleanEntry(raw);
  if (!entry.q) return { ok: false, error: 'missing q', entry: entry };
  console.log(JSON.stringify({ kind: 'question', at: entry.at, type: entry.type, tool: entry.tool, q: entry.q }));
  try {
    const loaded = await loadStore(event);
    if (loaded.error) throw new Error(loaded.error);
    const data = loaded.data;
    data.recent.unshift(entry);
    data.recent = data.recent.slice(0, 500);
    const bucket = Object.prototype.hasOwnProperty.call(data.counts, entry.type) ? entry.type : 'other';
    data.counts[bucket] = (data.counts[bucket] || 0) + 1;
    data.counts.total = (data.counts.total || 0) + 1;
    await saveStore(event, data);
    return { ok: true, entry: entry, counts: data.counts };
  } catch (e) {
    console.error('question-log blob write:', e.message);
    return { ok: false, error: e.message, entry: entry };
  }
}

module.exports = { cleanEntry, emptyStore, loadStore, appendQuestion };
