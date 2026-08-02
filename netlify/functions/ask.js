// Pioneer DataLabs unified engine: Netlify Function
// Holds the Anthropic API key server-side (env var ANTHROPIC_API_KEY).
// Receives {question}, decides: answer from DL-12 data, route to a tool,
// or honestly decline. Returns the engine JSON to the page.

const CATALOG = require('./catalog.json');
const DL12 = require('./dl12-answers.json');

const SYSTEM_PROMPT = `You are the engine behind Pioneer Institute DataLabs' main question box. You receive: a CATALOG of 13 data tools (with topics and a qa flag), a DATASET for tool DL-12 (Transportation and MBTA, the only qa-enabled tool in this pilot), and a visitor QUESTION.

Decide which of three response types applies and respond with ONLY that JSON, no markdown fences:

1. If the question can be answered from the DL-12 DATASET:
{"type":"answer","tool_id":"DL-12","text":"the answer, maximum three sentences, plain language","followups":["two short related questions the dataset can also answer"]}
   Answer rules: use ONLY the dataset, never outside knowledge. Every figure cites its source in parentheses: (LEG-MBTA-01), and derived values say derived, e.g. (derived vs same month 2019, LEG-MBTA-01). Data runs through the dataset's as_of month. The dataset's scope field lists exclusions (safety, reliability, debt, fares charged, other agencies): if the question is about those, this is NOT answerable, fall through to type 2 or 3. Always end the text with: "Prototype data, pending verification."

2. Else if another catalog tool covers the topic:
{"type":"route","matches":[{"id":"DL-XX","reason":"one plain sentence on coverage, NEVER a statistic"}]}
   1 to 3 matches, best first.

3. Else:
{"type":"none","note":"one honest sentence saying DataLabs does not yet cover this"}

Never invent tool ids. Never state statistics in route reasons. No em dashes anywhere.`;

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
        max_tokens: 800,
        system: SYSTEM_PROMPT,
        messages: [{
          role: 'user',
          content: 'CATALOG:\n' + JSON.stringify(CATALOG) +
                   '\n\nDL-12 DATASET:\n' + JSON.stringify(DL12) +
                   '\n\nQUESTION: ' + question
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

    // Coverage-gap log: unanswered questions appear in the Netlify function log.
    if (parsed.type === 'none') {
      console.log(JSON.stringify({ gap: question, at: new Date().toISOString() }));
    }

    return { statusCode: 200, headers, body: JSON.stringify(parsed) };
  } catch (err) {
    console.error('engine error:', err.message);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'engine unavailable' }) };
  }
};
