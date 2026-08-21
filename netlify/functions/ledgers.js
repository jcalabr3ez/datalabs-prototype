// Explicit lazy loaders so the Netlify bundler keeps every ledger file
// and Node does not parse them until a trigger hit (or a core rebuild).
const cache = {};

const LOAD = {
  'DL-01': function () { return require('./dl01-answers.json'); },
  'DL-02': function () { return require('./dl02-answers.json'); },
  'DL-03': function () { return require('./dl03-answers.json'); },
  'DL-04': function () { return require('./dl04-answers.json'); },
  'DL-05': function () { return require('./dl05-answers.json'); },
  'DL-06': function () { return require('./dl06-answers.json'); },
  'DL-07': function () { return require('./dl07-answers.json'); },
  'DL-08': function () { return require('./dl08-answers.json'); },
  'DL-09': function () { return require('./dl09-answers.json'); },
  'DL-10': function () { return require('./dl10-answers.json'); },
  'DL-11': function () { return require('./dl11-answers.json'); },
  'DL-12': function () { return require('./dl12-answers.json'); },
  'DL-13': function () { return require('./dl13-answers.json'); },
  'DL-14': function () { return require('./dl14-answers.json'); },
  'DL-15': function () { return require('./dl15-answers.json'); },
  'DL-16': function () { return require('./dl16-answers.json'); },
  'DL-17': function () { return require('./dl17-answers.json'); },
  'DL-19': function () { return require('./dl19-answers.json'); },
  'DL-20': function () { return require('./dl20-answers.json'); },
  'DL-21': function () { return require('./dl21-answers.json'); },
  'DL-22': function () { return require('./dl22-answers.json'); },
  'DL-23': function () { return require('./dl23-answers.json'); },
  'DL-24': function () { return require('./dl24-answers.json'); },
  'DL-25': function () { return require('./dl25-answers.json'); },
  'DL-26': function () { return require('./dl26-answers.json'); },
  'DL-27': function () { return require('./dl27-answers.json'); },
  'DL-28': function () { return require('./dl28-answers.json'); },
  'DL-29': function () { return require('./dl29-answers.json'); },
  'DL-30': function () { return require('./dl30-answers.json'); },
  'DL-31': function () { return require('./dl31-answers.json'); },
  'DL-32': function () { return require('./dl32-answers.json'); },
  'DL-33': function () { return require('./dl33-answers.json'); },
  'DL-34': function () { return require('./dl34-answers.json'); }
};

function loadLedger(id) {
  if (!LOAD[id]) throw new Error('unknown ledger ' + id);
  if (!cache[id]) cache[id] = LOAD[id]();
  return cache[id];
}

module.exports = { loadLedger, LOAD };
