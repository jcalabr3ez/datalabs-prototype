// Pioneer DataLabs question engine: per-tool manifests.
// Adding an AI-enabled tool = drop its dataset JSON in this directory, add one
// entry here, and flip "ai": true in catalog.json. ask.js iterates this list;
// it needs no per-tool edits.
//
// Manifest fields:
//   id            catalog tool id
//   label         one line for the router: what the dataset covers
//   routerScope   what the router must know to route correctly: coverage and
//                 the honest exclusions (questions that must NOT come here)
//   dataset       the full ledger (require'd JSON)
//   modelSlice(d) the subset of the ledger the answer model sees
//   charts        pre-built chart kinds the model may SELECT, or null
//   views         page views the model may SELECT, or null
//   viewDefault   fallback when the model picks an invalid view
//   highlight     { key, uppercase, describe }: dataset key whose object keys
//                 validate the highlight, plus the schema description
//   rules         per-tool answer rules appended to the global rules
//   link(p)       deep link built from the validated answer
//   src(d, p)     source line built from the ledger and the validated answer

const DL03 = require('./dl03-answers.json');
const DL02 = require('./dl02-answers.json');
const DL01 = require('./dl01-answers.json');

module.exports = [
  {
    id: 'DL-03',
    label: 'Transportation and MBTA: ridership by mode and month, recovery vs 2019, cost per trip, farebox recovery',
    routerScope: 'Covers MBTA ridership (unlinked passenger trips) by mode and month through the dataset as_of month and recovery vs 2019; service supplied and productivity (vehicle revenue hours and miles, and unlinked trips per vehicle revenue hour, by mode, latest full year vs 2019); reliability (share of trips meeting the headway or schedule-adherence standard) for bus, commuter rail, ferry, and The RIDE, by mode and by line, with a trend back to 2016; and operating cost per trip and farebox recovery rates INCLUDING their trend across report years 2022 to 2024. Questions about the cost of a ride or trip route here (answered as cost to provide). Questions about how reliable, on time, or punctual bus, commuter rail, ferry, or The RIDE are route here. Does NOT cover: subway or Green Line reliability (the MBTA measures rapid transit with Excess Trip Time, a different method adopted December 2024), safety, the capital budget, debt, the fare PRICES riders are charged (ticket and pass prices), or other transit agencies.',
    dataset: DL03,
    modelSlice: function (d) {
      // Ship the whole ledger EXCEPT service.monthly_vrm_total: that raw monthly
      // series drives the page chart only, and the service annual and derived
      // rollups already answer every trend question, so it need not go to the
      // model. The monthly ridership series is kept for month-level questions.
      if (!d.service) return d;
      var o = {}; Object.keys(d).forEach(function (k) { o[k] = d[k]; });
      var s = {}; Object.keys(d.service).forEach(function (k) { if (k !== 'monthly_vrm_total') s[k] = d.service[k]; });
      o.service = s;
      return o;
    },
    charts: ['monthly_trend', 'recovery_by_mode', 'productivity', 'service_recovery', 'reliability_by_mode', 'reliability_trend', 'cost_per_trip', 'farebox'],
    views: null,
    viewDefault: null,
    highlight: { key: 'mode_names', uppercase: true, describe: 'a mode code (HR, MB, CR, LR, RB, FB, DR) if the question focuses on one mode, else null' },
    rules: 'DL-03 rules. Every figure cites its source in parentheses: ridership figures cite (SRC-301); cost per trip and farebox figures cite (SRC-302). Values you compute say derived, e.g. (derived vs same month 2019, SRC-301). Prefer the precomputed values in the derived block over your own arithmetic. Ridership runs through the dataset as_of month; the cost and farebox series (annual_cost_series) covers NTD report years 2022 to 2024, so cost and farebox TREND questions inside that window are answerable, use the derived cost_per_trip_trend block. All figures are verified against FTA NTD; never call any figure prototype or pending. Cost per trip, farebox recovery rates, cost trends, and ridership are all answerable; never mark them unanswerable. When a question about the cost or price of a ride is ambiguous between the fare a rider pays and the cost to provide the trip, answer with the cost to provide and note in detail that fare prices are not tracked here. Service and productivity questions are answerable from the service block and cite (SRC-301) or (derived, SRC-301): service supplied is vehicle revenue hours and miles, productivity is unlinked trips per vehicle revenue hour, both by mode for the latest full year against full-year 2019; prefer service.derived and service.by_mode over your own arithmetic. Reliability questions are answerable from the reliability block and cite (SRC-303): it covers bus, commuter rail, ferry, and The RIDE as the share of trips meeting the headway or schedule-adherence standard, with trailing-twelve-month figures, a yearly trend back to 2016, and by-line and by-route detail; prefer reliability.modes, reliability.derived, and the by-line lists, and say figures are the trailing twelve months. Subway (Red, Orange, Blue) and Green Line reliability are NOT in this dataset: the MBTA measures rapid transit with Excess Trip Time, adopted December 2024; if asked for subway or Green Line reliability, on-time performance, or punctuality, set answerable false, say so plainly, and offer the reliability the dataset does cover. Chart selection: monthly_trend = ridership over time or recovery overall; recovery_by_mode = comparing ridership across modes vs 2019; productivity = trips per revenue hour or how full the service runs; service_recovery = service supplied vs ridership, or whether service outran riders; reliability_by_mode = comparing reliability across modes; reliability_trend = whether reliability is improving, or reliability by line and route; cost_per_trip = cost to provide; farebox = share riders pay; none = no view fits.',
    link: function (p) { return p.chart && p.chart !== 'none' ? '/mbta/#view-' + p.chart : '/mbta/'; },
    src: function (d) { return 'FTA NTD, ridership and service through ' + d.as_of + ' (SRC-301); cost per trip and farebox from NTD Annual Metrics, report years 2022 to ' + (d.cost_report_year || '2024') + ' (SRC-302); reliability from the MBTA Open Data Portal, trailing twelve months (SRC-303). Ridership, service, and cost figures verified against the National Transit Database.'; }
  },
  {
    id: 'DL-02',
    label: 'Florida Insurance Watch: homeowners premiums by county, Citizens series, litigation, takeouts, risk transfer',
    routerScope: 'Covers Florida homeowners insurance: county average premiums, Citizens Property Insurance policy counts and finances, litigation shares, the takeout program, and risk transfer. Does NOT cover: advice on buying, dropping, or switching coverage; predictions of future rates or hurricanes; individual premium quotes; claims or legal guidance; insurer solvency opinions; other insurance lines; other states.',
    dataset: DL02,
    modelSlice: function (d) { return d; },
    charts: ['citizens_trend', 'county_compare', 'premium_change', 'litigation', 'risk_transfer', 'takeouts'],
    views: ['home', 'policy', 'report'],
    viewDefault: 'home',
    highlight: { key: 'county_premiums', uppercase: false, describe: 'the exact county name as written in county_premiums if the question focuses on one county, else null' },
    rules: 'DL-02 rules. Every figure in text AND detail cites its source id in parentheses, e.g. (SRC-FL-01) for county premiums, (SRC-FL-02) for Citizens figures, (SRC-FL-03) for litigation shares, (SRC-FL-04) for risk transfer. Values you compute say derived, e.g. (derived, SRC-FL-02). Prefer the precomputed values in citizens_key_facts and county_rankings over your own arithmetic. Dollar figures are annual average premiums for the county, not quotes. Chart selection: citizens_trend = Citizens policy counts over time, growth, decline, depopulation; county_compare = what a county pays or comparing counties; premium_change = whether premiums are rising or falling; litigation = lawsuits, litigation share, why reform happened; risk_transfer = reinsurance, cat fund, private capital; takeouts = the takeout program and flows; none = no view fits. When the question names a county, prefer county_compare (or premium_change if it is about change) with that county as highlight. View selection: home for what households pay, counties, Citizens size, flood; policy for market health, litigation, takeouts, risk transfer; report for reform grades.',
    link: function (p) { return '/florida-insurance/#view-' + p.view; },
    src: function (d) { return 'Florida Insurance Watch ledger, through ' + d.as_of + ': FL OIR county tables (SRC-FL-01), Citizens filings (SRC-FL-02), NAIC MCAS via OIR (SRC-FL-03), Citizens audited notes (SRC-FL-04).'; }
  },
  {
    id: 'DL-01',
    label: 'State Tax Atlas: every jurisdiction’s income tax rate, surtaxes, wealth-tax proposals, ballot pathways, and risk tier',
    routerScope: 'Covers all 51 US jurisdictions: enacted top income tax rates and surtaxes, slated changes already in law, active wealth-tax and high-income surtax proposals, citizen-initiative ballot pathways, Pioneer’s Short-Term Risk tier, and a dated watch list of upcoming events (hearings, rulings, deadlines, elections) through 2028, so what-to-watch and upcoming-dates questions route here. Does NOT cover: personal tax or legal advice; whether to move or relocate; predicting how a ballot measure, election, or court case will turn out; calculating an individual’s tax; sales, property, corporate, or estate taxes except where a record already notes them; other countries or years outside the dataset.',
    dataset: DL01,
    modelSlice: function (d) {
      // The answer model sees the analytical core: no grid coordinates, no
      // source URL lists (the handler builds the source line from those).
      var states = {};
      Object.keys(d.states).forEach(function (k) {
        var s = d.states[k], o = {};
        Object.keys(s).forEach(function (f) { if (f !== 'row' && f !== 'col') o[f] = s[f]; });
        states[k] = o;
      });
      return {
        tool_id: d.tool_id, title: d.title, as_of: d.as_of, horizon: d.horizon,
        scope: d.scope, views: d.views, meta: d.meta, derived: d.derived,
        events: d.events, states: states
      };
    },
    charts: null,
    views: ['current', 'proposals', 'ballot', 'future', 'events'],
    viewDefault: 'current',
    highlight: { key: 'states', uppercase: true, describe: 'the exact two-letter jurisdiction code (for example CA, MA, DC) if the question focuses on one jurisdiction, else null' },
    rules: 'DL-01 rules. Answer from the jurisdiction record fields: topRate, currentStatus, futureRisk, ballot, wealthTax, incomeSurtax, currentNote, futureNote, slated (when present), ballotNote, and the proposals array. Prefer the precomputed rankings, lists, and counts in the derived block over deriving your own; they cite (derived). Translate every code to its meta label in prose and never print the raw code: currentStatus surtax_active reads as "surtax in effect", futureRisk very_high reads as "very high", ballot open reads as "direct initiative, simple majority". Cite sources the way the atlas does, by naming in parentheses the instrument already in the record: enacted and proposed measures cite their bill, act, or proposition number, e.g. (SB 3125 / Act 24), (Prop 40), (HJRCA 21); a base top rate with no measure cites (Tax Foundation, 2026); Short-Term Risk tiers and composite scores cite (Pioneer model). Rate and dollar figures are as written in the record; never recompute a bracket or estimate anyone’s tax. The events block is the dated watch list through 2028: for what-to-watch or upcoming-dates questions, judge each event date against as_of and the window asked, lead with the nearest matching events (date, state, and what resolves), name the instrument each turns on, and set view to events; describing an event and its stakes is answering from the dataset, never a prediction of its outcome. View selection: current = enacted top rate, surtax, or status; proposals = wealth-tax or surtax vehicles in play; ballot = initiative pathways and thresholds; future = the Short-Term Risk tier and outlook; events = a dated hearing, ruling, or election on the watch list.',
    link: function (p) { return '/tax-atlas/#view-' + p.view + (p.highlight ? '&state=' + p.highlight : ''); },
    src: function (d, p) {
      var srcs = d.default_sources.map(function (x) { return x.label; });
      if (p.highlight && d.state_sources[p.highlight]) {
        d.state_sources[p.highlight].forEach(function (x) { srcs.push(x.label); });
      }
      return 'State Tax Atlas, law and measures as of ' + d.as_of + '. Sources: ' + srcs.join('; ') + '.';
    }
  }
];
