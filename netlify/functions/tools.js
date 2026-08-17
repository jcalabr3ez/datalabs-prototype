// Pioneer DataLabs question engine: per-tool manifests.
// Adding an AI-enabled tool = drop its dataset JSON in this directory, add one
// entry here, and flip "ai": true in catalog.json. ask.js iterates this list;
// it needs no per-tool edits.
//
// Manifest fields:
//   id            catalog tool id
//   label         one line: what the dataset covers
//   scope         what the engine must know to answer or decline correctly:
//                 coverage and the honest exclusions (questions that must NOT
//                 be answered from this dataset)
//   triggers      recall-oriented phrases; a hit ships the full modelSlice.
//                 Misses still ship coreSlice, so a thin trigger list cannot
//                 hide a tool. Short tokens (<=2 chars) match as whole words.
//   dataset       the full ledger (require'd JSON)
//   coreSlice(d)  the always-sent answering core (scope, derived, latest
//                 figures). Keep this small: at 20 tools every core ships.
//   modelSlice(d) the full subset the model sees when this tool is a hit
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
const DL04 = require('./dl04-answers.json');
const DL05 = require('./dl05-answers.json');
const DL06 = require('./dl06-answers.json');
const DL07 = require('./dl07-answers.json');
const DL08 = require('./dl08-answers.json');
const DL09 = require('./dl09-answers.json');
const DL10 = require('./dl10-answers.json');
const DL11 = require('./dl11-answers.json');
const DL12 = require('./dl12-answers.json');
const DL13 = require('./dl13-answers.json');
const DL14 = require('./dl14-answers.json');
const DL15 = require('./dl15-answers.json');
const DL16 = require('./dl16-answers.json');
const DL17 = require('./dl17-answers.json');
const DL19 = require('./dl19-answers.json');
const DL20 = require('./dl20-answers.json');
const DL21 = require('./dl21-answers.json');
const DL22 = require('./dl22-answers.json');
const DL23 = require('./dl23-answers.json');
const DL24 = require('./dl24-answers.json');
const DL25 = require('./dl25-answers.json');
const DL26 = require('./dl26-answers.json');
const DL27 = require('./dl27-answers.json');
const DL28 = require('./dl28-answers.json');
const DL29 = require('./dl29-answers.json');
const DL30 = require('./dl30-answers.json');
const DL31 = require('./dl31-answers.json');
const DL32 = require('./dl32-answers.json');

var CORE_HEAVY = {
  trend: 1, rows: 1, district_rows: 1, states: 1, cube: 1,
  ma_districts: 1, fl_districts: 1, series: 1, points: 1,
  top: 1, top_ten: 1, race: 1, selected: 1, grades: 1,
  types: 1, ma_types: 1, agencies: 1
};

function slimSnap(snap) {
  if (!snap || typeof snap !== 'object' || Array.isArray(snap)) return snap;
  var out = {};
  // Compact every-jurisdiction map so a named-state question can answer
  // from the core. Do not copy `rows` (those stay on the full slice).
  // Window snaps already keep `ranked`; skip those.
  if (Array.isArray(snap.rows) && snap.rows.length && snap.rows.length <= 60 && !snap.ranked) {
    var by = {};
    snap.rows.forEach(function (r) {
      if (r && r.st) by[r.st] = { v: r.v, rank: r.rank, name: r.name };
    });
    if (Object.keys(by).length) out.by_st = by;
  }
  Object.keys(snap).forEach(function (k) {
    if (CORE_HEAVY[k]) return;
    var v = snap[k];
    if (v && typeof v === 'object' && !Array.isArray(v) && (v.n_ranked || v.ma || v.highest || v.lfpr)) {
      out[k] = slimSnap(v);
    } else {
      out[k] = v;
    }
  });
  return out;
}

function slimTrend(trend) {
  if (!trend || typeof trend !== 'object') return trend;
  if (Array.isArray(trend)) return trend.slice(-36);
  var keep = { US: 1, MA: 1, FL: 1 };
  var out = {};
  Object.keys(trend).forEach(function (st) {
    if (!keep[st]) return;
    var series = trend[st];
    out[st] = Array.isArray(series) ? series.slice(-36) : series;
  });
  return out;
}

function slimDerived(derived) {
  if (!derived || typeof derived !== 'object') return derived;
  var out = {
    note: derived.note,
    highest_five: derived.highest_five,
    lowest_five: derived.lowest_five,
    massachusetts_rank: derived.massachusetts_rank,
    n_ranked: derived.n_ranked
  };
  if (derived.windows) {
    var win = {};
    Object.keys(derived.windows).forEach(function (k) {
      win[k] = slimSnap(derived.windows[k]);
    });
    out.windows = win;
  }
  Object.keys(derived).forEach(function (k) {
    if (out[k] !== undefined || k === 'secondary') return;
    var v = derived[k];
    if (v && typeof v === 'object' && !Array.isArray(v) && (v.ma || v.us || v.v != null)) {
      out[k] = slimSnap(v);
    }
  });
  if (derived.secondary) {
    var sec = {};
    Object.keys(derived.secondary).forEach(function (k) {
      sec[k] = slimSnap(derived.secondary[k]);
    });
    out.secondary = sec;
  }
  return out;
}

function suiteCore(d) {
  var src = {};
  Object.keys(d.source_id_map || {}).forEach(function (k) {
    var s = d.source_id_map[k] || {};
    src[k] = { name: s.name, cadence: s.cadence };
  });
  return {
    tool_id: d.tool_id, title: d.title, as_of: d.as_of,
    scope: d.scope, exclusions: d.exclusions,
    vintage_note: d.vintage_note, metric: d.metric,
    metric_label: d.metric_label, unit: d.unit,
    data_month_label: d.data_month_label,
    latest: d.latest, derived: slimDerived(d.derived), source_ids: src
  };
}

function suiteModel(d) {
  return {
    tool_id: d.tool_id, title: d.title, as_of: d.as_of,
    scope: d.scope, exclusions: d.exclusions,
    vintage_note: d.vintage_note, metric: d.metric,
    metric_label: d.metric_label, unit: d.unit,
    data_month_label: d.data_month_label,
    latest: d.latest, derived: d.derived, rows: d.rows, trend: slimTrend(d.trend),
    source_id_map: d.source_id_map, pending: d.pending
  };
}

function suiteHasTrend(d) {
  var t = d && d.trend;
  if (!t) return false;
  if (Array.isArray(t)) return t.length >= 2;
  return Object.keys(t).some(function (k) {
    return t[k] && t[k].length >= 2;
  });
}

function suiteViewId(view, opts) {
  opts = opts || {};
  if (view === 'latest') return opts.latestId || 'view-rank';
  if (view === 'table' && opts.tableId) return opts.tableId;
  return 'view-' + view;
}

function suiteRules(id, src, extra, hasTrend, hasTable) {
  var pick;
  if (hasTable === false) {
    pick = hasTrend
      ? 'View and chart selection: latest and trend = the namesake series over time. This page has no ranking table. '
      : 'View and chart selection: latest = the namesake finding. This page has no ranking table. ';
  } else {
    pick = hasTrend
      ? 'View and chart selection: latest = the current ranking; trend = change over time; table = every row. '
      : 'View and chart selection: latest = the current ranking; table = every row. This page has no trend view. ';
  }
  return id + ' rules. Every figure cites its source in parentheses, e.g. (' + src + '). Ranks, year-over-year changes, and trailing-window means cite (derived, ' + src + '). Prefer the precomputed values in latest, derived.windows, and derived.secondary over your own arithmetic. Do not average unpublished state-periods. Unscoped questions use the published United States cell in latest.us when that cell exists; never average the fifty states to invent a U.S. figure. If latest.us is missing, answer with the published highest state, not an invented national total. A named-state question uses that state\'s row, or by_st[ST] on a companion snap when rows are not in this slice. Answer the metric named in metric_label and any series stored under derived.secondary or derived.windows; cite the source id on each figure. Topics named as pending or listed in exclusions are unanswerable: say so plainly and do not invent a figure. Decline advice, forecasts, and individual lookups the ledger does not hold. ' + pick + 'When the question names a state or municipality present in entities, set highlight to that key. ' + (extra || '');
}

function suiteLink(slug, opts) {
  opts = opts || {};
  var hasTrend = !!opts.hasTrend;
  var hasTable = opts.hasTable !== false;
  var extra = opts.extraViews || [];
  return function (p) {
    var allowed = ['latest'].concat(hasTrend ? ['trend'] : []).concat(hasTable ? ['table'] : []).concat(extra);
    var view = (p.view && allowed.indexOf(p.view) >= 0) ? p.view : 'latest';
    var url = '/' + slug + '/#' + suiteViewId(view, opts);
    if (p.highlight) url += '&st=' + encodeURIComponent(p.highlight);
    return url;
  };
}

function suiteSrc(d) {
  return d.title + ', through ' + (d.data_month_label || d.as_of) + '. ' + (d.vintage_note || '');
}

function suiteTool(d, spec) {
  var hasTrend = spec.hasTrend != null ? spec.hasTrend : suiteHasTrend(d);
  var hasTable = spec.hasTable !== false;
  var extraViews = spec.extraViews || [];
  var views = ['latest'];
  if (hasTrend) views.push('trend');
  if (hasTable) views.push('table');
  extraViews.forEach(function (v) { views.push(v); });
  var charts = views.filter(function (v) { return extraViews.indexOf(v) < 0; });
  return {
    id: spec.id,
    label: spec.label,
    scope: (d.scope || '') + ' ' + (d.exclusions || ''),
    triggers: spec.triggers,
    dataset: d,
    coreSlice: suiteCore,
    modelSlice: suiteModel,
    charts: charts,
    views: views,
    viewDefault: 'latest',
    highlight: {
      key: 'entities',
      uppercase: spec.uppercase !== false,
      describe: spec.hl || 'the exact two-letter jurisdiction code (for example MA, CA, TX) if the question focuses on one state, else null'
    },
    rules: suiteRules(spec.id, spec.src, spec.extra, hasTrend, hasTable),
    link: suiteLink(d.slug, {
      hasTrend: hasTrend,
      hasTable: hasTable,
      extraViews: extraViews,
      latestId: spec.latestId,
      tableId: spec.tableId
    }),
    src: suiteSrc
  };
}

module.exports = [
  {
    id: 'DL-03',
    label: 'MBTA Performance: ridership by mode and month, recovery vs 2019, cost per trip, farebox recovery',
    scope: 'Covers MBTA ridership (unlinked passenger trips) by mode and month through the dataset as_of month and recovery vs 2019; service supplied and productivity (vehicle revenue hours and miles, and unlinked trips per vehicle revenue hour, by mode, latest full year vs 2019); reliability (share of trips meeting the headway or schedule-adherence standard) for bus, commuter rail, ferry, and The RIDE, by mode and by line, with a trend back to 2016; and operating cost per trip and farebox recovery, the share of operating cost that fares cover, INCLUDING their trend across report years 2022 to 2024. Questions about the cost of a ride or trip, whether a ride costs more or less than before, and what share of the cost fares cover all answer here (cost is answered as cost to provide, farebox recovery as the covered share). Questions about how reliable, on time, or punctual bus, commuter rail, ferry, or The RIDE are route here. Does NOT cover: subway or Green Line reliability (the MBTA measures rapid transit with Excess Trip Time, a different method adopted December 2024), safety, the capital budget, debt, the ticket and pass PRICES a rider pays (only these prices are excluded, NOT farebox recovery or cost per trip, which are covered above and DO answer here), or other transit agencies.',
    triggers: [
      'mbta', 'the t', 'transit', 'subway', 'commuter rail', 'commuter', 'green line',
      'red line', 'orange line', 'blue line', 'the ride', 'paratransit', 'ferry',
      'ridership', 'unlinked', 'farebox', 'fare', 'cost per trip', 'vehicle revenue',
      'productivity', 'reliability', 'on time', 'ontime', 'punctual', 'headway',
      'pre-pandemic', 'bus rapid', 'silver line', 'ntd', 'transportation'
    ],
    dataset: DL03,
    coreSlice: function (d) {
      var service = d.service || {};
      var rel = d.reliability || {};
      return {
        tool_id: d.tool_id || 'DL-03', as_of: d.as_of, scope: d.scope,
        vintage_note: d.vintage_note, source_id: d.source_id,
        cost_source_id: d.cost_source_id, mode_names: d.mode_names,
        latest_month: d.latest_month,
        recovery_vs_2019_same_month_pct: d.recovery_vs_2019_same_month_pct,
        recovery_baseline: d.recovery_baseline, yoy_change_pct: d.yoy_change_pct,
        annual_cost_and_farebox: d.annual_cost_and_farebox,
        annual_cost_note: d.annual_cost_note, derived: d.derived,
        cost_report_year: d.cost_report_year,
        service: {
          as_of: service.as_of, source_id: service.source_id,
          latest_full_year: service.latest_full_year, note: service.note,
          annual_totals: service.annual_totals, by_mode: service.by_mode,
          derived: service.derived
        },
        reliability: {
          as_of: rel.as_of, source_id: rel.source_id,
          metric_note: rel.metric_note, excludes_note: rel.excludes_note,
          modes: rel.modes, derived: rel.derived
        }
      };
    },
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
    label: 'Florida Homeowners Insurance: homeowners premiums by county, Citizens series, litigation, takeouts, risk transfer',
    scope: 'Covers Florida homeowners insurance: county average premiums, Citizens Property Insurance policy counts and finances, litigation shares, the takeout program, and risk transfer. Does NOT cover: advice on buying, dropping, or switching coverage; predictions of future rates or hurricanes; individual premium quotes; claims or legal guidance; insurer solvency opinions; other insurance lines; other states.',
    triggers: [
      'florida', 'homeowners', 'homeowner', 'insurance', 'premium', 'citizens',
      'miami', 'miami-dade', 'dade', 'takeout', 'litigation', 'reinsurance',
      'cat fund', 'risk transfer', 'oir', 'windstorm', 'county premium'
    ],
    dataset: DL02,
    coreSlice: function (d) {
      return {
        as_of: d.as_of, scope: d.scope, source_id_map: d.source_id_map,
        citizens_key_facts: d.citizens_key_facts,
        county_premiums: d.county_premiums,
        county_premium_notes: d.county_premium_notes,
        county_rankings: d.county_rankings,
        litigation_share: d.litigation_share, litigation_note: d.litigation_note,
        takeout_net_inflow: d.takeout_net_inflow, takeout_note: d.takeout_note,
        risk_transfer: d.risk_transfer, risk_transfer_note: d.risk_transfer_note,
        market_facts: d.market_facts, reform_context: d.reform_context
      };
    },
    modelSlice: function (d) { return d; },
    charts: ['citizens_trend', 'county_compare', 'premium_change', 'litigation', 'risk_transfer', 'takeouts'],
    views: ['home', 'policy', 'report'],
    viewDefault: 'home',
    highlight: { key: 'county_premiums', uppercase: false, describe: 'the exact county name as written in county_premiums if the question focuses on one county, else null' },
    rules: 'DL-02 rules. Every figure in text AND detail cites its source id in parentheses, e.g. (SRC-FL-01) for county premiums, (SRC-FL-02) for Citizens figures, (SRC-FL-03) for litigation shares, (SRC-FL-04) for risk transfer. Values you compute say derived, e.g. (derived, SRC-FL-02). Prefer the precomputed values in citizens_key_facts and county_rankings over your own arithmetic. Dollar figures are annual average premiums for the county, not quotes. Chart selection: citizens_trend = Citizens policy counts over time, growth, decline, depopulation; county_compare = what a county pays or comparing counties; premium_change = whether premiums are rising or falling; litigation = lawsuits, litigation share, why reform happened; risk_transfer = reinsurance, cat fund, private capital; takeouts = the takeout program and flows; none = no view fits. When the question names a county, prefer county_compare (or premium_change if it is about change) with that county as highlight. View selection: home for what households pay, counties, Citizens size, flood; policy for market health, litigation, takeouts, risk transfer; report for reform grades.',
    link: function (p) { return '/florida-insurance/#view-' + p.view; },
    src: function (d) { return 'Florida Homeowners Insurance ledger, through ' + d.as_of + ': FL OIR county tables (SRC-FL-01), Citizens filings (SRC-FL-02), NAIC MCAS via OIR (SRC-FL-03), Citizens audited notes (SRC-FL-04).'; }
  },
  {
    id: 'DL-01',
    label: 'State Wealth Taxes: every jurisdiction’s wealth-tax, surtax, and intangibles provisions, ballot pathways, and risk tier',
    scope: 'Covers all 51 US jurisdictions: enacted top income tax rates and surtaxes (a single state’s current top income tax rate answers here, for example what is California’s top income tax rate), slated changes already in law, active wealth-tax and high-income surtax proposals, citizen-initiative ballot pathways, Pioneer’s Short-Term Risk tier, and a dated watch list of upcoming events (hearings, rulings, deadlines, elections) through 2028, so what-to-watch and upcoming-dates questions route here. Does NOT cover: personal tax or legal advice; whether to move or relocate; predicting how a ballot measure, election, or court case will turn out; calculating an individual’s tax; sales, property, corporate, or estate taxes except where a record already notes them; other countries or years outside the dataset.',
    triggers: [
      'tax', 'surtax', 'wealth', 'income tax', 'top rate', 'ballot', 'proposition',
      'prop 40', 'initiative', 'jurisdiction', 'california', 'texas', 'watch list',
      'what to watch', 'events should', 'high earner', 'atlas'
    ],
    dataset: DL01,
    coreSlice: function (d) {
      // Always-sent core: codes and rates for every jurisdiction, plus the
      // derived rankings and the dated watch list. Long notes and proposal
      // writeups stay in modelSlice and ship only on a tax-atlas hit.
      var states = {};
      Object.keys(d.states).forEach(function (k) {
        var s = d.states[k], o = {};
        ['abbr', 'name', 'topRate', 'currentStatus', 'futureRisk', 'ballot',
          'wealthTax', 'incomeSurtax', 'slated'].forEach(function (f) {
          if (s[f] !== undefined) o[f] = s[f];
        });
        states[k] = o;
      });
      return {
        tool_id: d.tool_id, title: d.title, as_of: d.as_of, horizon: d.horizon,
        scope: d.scope, views: d.views, meta: d.meta, derived: d.derived,
        events: d.events, states: states
      };
    },
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
      return 'State Wealth Taxes, law and measures as of ' + d.as_of + '. Sources: ' + srcs.join('; ') + '.';
    }
  },
  {
    id: 'DL-04',
    label: 'Retail electricity prices: all-sector average cents per kilowatthour by state, plus sales, generation, and capacity',
    scope: 'Covers the all-sector average retail price of electricity by state and for the United States, plus residential, commercial, and industrial averages from the same EIA-861 file, plus retail sales, net generation, net summer capacity, and per-capita sales and generation, calendar years 2012 through the dataset data_year. The U.S. figure is EIA\'s published U.S. Total row, a sales-weighted average, never an unweighted mean of the state prices. Does NOT cover: utility, city, or customer-class rates; forecasts or what prices will do next year; bill calculators or rate-case advice; other fuels.',
    triggers: [
      'electricity', 'electric', 'kilowatthour', 'kwh', 'cents per', 'retail price',
      'electricity price', 'electricity cost', 'power price', 'utility rate',
      'eia-861', 'form eia', 'all-sector', 'hawaii electricity',
      'massachusetts electricity', 'state electricity', 'household',
      'residential electricity', 'what does a household pay', 'commercial electricity',
      'industrial electricity'
    ],
    dataset: DL04,
    coreSlice: function (d) {
      return {
        tool_id: d.tool_id, as_of: d.as_of, data_year: d.data_year, scope: d.scope,
        vintage_note: d.vintage_note, source_id_map: d.source_id_map,
        entities: d.entities, latest: d.latest, latest_states: d.latest_states,
        derived: d.derived,
        residential_states: d.residential_states,
        residential_trend: d.residential_trend,
        price_trend_us: d.price_trend.US,
        price_trend_ma: d.price_trend.MA
      };
    },
    modelSlice: function (d) {
      var o = {};
      Object.keys(d).forEach(function (k) { if (k !== 'series') o[k] = d[k]; });
      return o;
    },
    charts: ['price_rank', 'price_trend', 'sales_rank', 'gen_rank', 'res_rank'],
    views: ['prices', 'trends', 'supply', 'table', 'households'],
    viewDefault: 'prices',
    highlight: { key: 'entities', uppercase: true, describe: 'the exact two-letter jurisdiction code (for example MA, HI, ND, US) if the question focuses on one state, else null' },
    rules: 'DL-04 rules. Every figure cites its source in parentheses: prices and sales cite (SRC-401); generation cites (SRC-403); capacity cites (SRC-404); population and per-capita figures cite (SRC-402) or (derived, SRC-401, SRC-402). Ranks and year-over-year changes cite (derived, SRC-401). Prefer the precomputed values in latest, latest_states, derived.sectors, residential_states, and latest.residential over your own arithmetic. The U.S. all-sector average is latest.us.price_cents, EIA\'s U.S. Total row; never average the 50 state prices. An unscoped household question uses latest.residential.us.price_cents, not Massachusetts. Household questions use latest.residential and residential_states (price_cents on each row). Commercial and industrial averages sit in derived.sectors. A residential price is still not a household bill. Chart selection: res_rank = household or residential prices; price_rank = all-sector comparison; price_trend = change over time or since 2012; sales_rank = how much electricity was sold; gen_rank = how much was generated; none = no view fits. When the question names a state, set highlight to that state code. View selection: households for residential prices; prices for the all-sector ranking; trends for the 2012-forward series; supply for sales or generation; table for the full latest-year table. Decline forecasts, utility-specific rates, and bill advice.',
    link: function (p) {
      var chart = p.chart && p.chart !== 'none' ? p.chart : (p.view && p.view !== 'prices' ? p.view : 'price_rank');
      if (chart === 'res_rank' || p.view === 'households') chart = 'households';
      var url = '/electricity/#view-' + chart;
      if (p.highlight) url += '&st=' + p.highlight;
      return url;
    },
    src: function (d) {
      return 'EIA Form EIA-861 / Electric Power Annual table 2.10, all-sector prices and sales through ' + d.data_year + ' (SRC-401); EIA-923 generation (SRC-403); EIA-860 capacity (SRC-404); Census Bureau population (SRC-402). The U.S. figure is EIA\'s U.S. Total row.';
    }
  },
  {
    id: 'DL-05',
    label: 'Massachusetts public pensions: every retirement board\'s funded status and returns, plus the State and Teacher retiree payroll',
    scope: 'Covers every Massachusetts public retirement board\'s latest PERAC actuarial valuation (funded ratio, unfunded liability, actuarial accrued liability, membership, average salary and benefit, assumed rate of return) and compiled investment returns (one-year, five-year, ten-year, and since-inception), plus the compiled State (MSERS) and Teachers (MTRS) retiree payroll for calendar years 2011 through the dataset retiree_year: yearly headcount and annual pension totals, department and title rankings, the largest individual pensions, and a page-side name search of the latest CTHRU year (search_year). Does NOT cover: answering a named-retiree lookup in the ask box (use the Retirees search on the page); municipal or local-board retiree names; retirement advice, benefit estimates, or what a member will receive; forecasts of funded status; other states\' pension systems; or Commonwealth payroll and vendor payments.',
    triggers: [
      'pension', 'pensions', 'perac', 'funded ratio', 'unfunded', 'retirement board',
      'retiree', 'retirees', 'mtrs', 'msers', 'mass teachers', 'teachers retirement',
      'state retirement', 'cthru', 'public pension', 'pension payroll',
      'springfield pension', 'boston teachers'
    ],
    dataset: DL05,
    coreSlice: function (d) {
      return {
        tool_id: d.tool_id, as_of: d.as_of, scope: d.scope,
        vintage_note: d.vintage_note, source_id_map: d.source_id_map,
        board_valuation_through: d.board_valuation_through,
        returns_year: d.returns_year, retiree_year: d.retiree_year,
        search_year: d.search_year,
        latest: d.latest, derived: d.derived, entities: d.entities,
        boards: d.boards.map(function (b) {
          return {
            id: b.id, name: b.name, valuation_year: b.valuation_year,
            funded_pct: b.funded_pct, ual: b.ual, rank: b.rank,
            return_1y_pct: b.return_1y_pct, return_10y_pct: b.return_10y_pct,
            active: b.active, retired: b.retired
          };
        }),
        retirees: {
          latest: d.retirees.latest,
          yearly: d.retirees.yearly.map(function (y) {
            return {
              year: y.year, count: y.count, annual_amount: y.annual_amount,
              msers_count: y.msers.count, mtrs_count: y.mtrs.count,
              msers_amount: y.msers.annual_amount, mtrs_amount: y.mtrs.annual_amount
            };
          }),
          top_pensions: d.retirees.top_pensions,
          search: d.retirees.search ? {
            year: d.retirees.search.year,
            count: d.retirees.search.count,
            annual_amount: d.retirees.search.annual_amount,
            complete: d.retirees.search.complete,
            as_of: d.retirees.search.as_of,
            new_retirees_count: d.retirees.search.new_retirees
              ? d.retirees.search.new_retirees.count : null
          } : null
        }
      };
    },
    modelSlice: function (d) {
      var o = {};
      Object.keys(d).forEach(function (k) {
        if (k !== 'funded_history' && k !== 'verification') o[k] = d[k];
      });
      return o;
    },
    charts: ['funded_rank', 'funded_trend', 'returns_rank', 'retiree_trend'],
    views: ['boards', 'returns', 'retirees', 'table'],
    viewDefault: 'boards',
    highlight: { key: 'entities', uppercase: false, describe: 'the board id slug (for example state, mtrs, springfield, boston-teachers) if the question focuses on one board, else null' },
    rules: 'DL-05 rules. Every figure cites its source in parentheses: funded ratios, unfunded liabilities, membership, and assumed returns cite (SRC-501); investment returns cite (SRC-502); State and Teacher retiree payroll, counts, department rankings, and named top pensions cite (SRC-503). Ranks and the dollar-weighted funded ratio cite (derived, SRC-501). Prefer the precomputed values in latest and derived over your own arithmetic. Funded ratio is PERAC\'s published actuarial ratio, not market value over liability. CTHRU retiree counts are named-retiree payroll rows, not the PERAC actuarial recipient census (which also counts survivors). Chart selection: funded_rank = comparing boards or who is best or worst funded; funded_trend = change over time; returns_rank = investment returns; retiree_trend = State or Teacher retiree payroll over time; none = no view fits. When the question names a board, set highlight to that board id. View selection: boards for funded status; returns for investment performance; retirees for the State and Teacher payroll or a named-retiree question; table for the full board table. The page has a last-name search of search_year; the ask box does not look up a named retiree. Answer who is paid the most from top_pensions. Decline ask-box name lookups, benefit estimates, forecasts, and other states.',
    link: function (p) {
      var chart = p.chart && p.chart !== 'none' ? p.chart : (p.view && p.view !== 'boards' ? p.view : 'funded_rank');
      var url = '/pensions/#view-' + chart;
      if (p.highlight) url += '&st=' + p.highlight;
      return url;
    },
    src: function (d) {
      return 'PERAC board actuarial valuations through January 1, ' + d.board_valuation_through + ' (SRC-501); PERAC compiled investment returns, calendar ' + d.returns_year + ' (SRC-502); CTHRU State and Teachers Retirement Benefits, calendar years 2011 through ' + d.retiree_year + ' (SRC-503). Name search uses calendar ' + d.search_year + '.';
    }
  },
  suiteTool(DL06, {
    id: 'DL-06',
    label: 'Massachusetts Schools: Fall public-school enrollment, with per-pupil spending, MCAS, and Chapter 74 as later views',
    src: 'SRC-606-02',
    triggers: [
      'massachusetts enrollment', 'public-school enrollment', 'public school enrollment',
      'how many students are enrolled in massachusetts',
      'per-pupil', 'per pupil', 'school spending', 'massachusetts k-12',
      'k-12 spending', 'k12 spending', 'current expenditures per pupil',
      'vocational', 'voc-tech', 'voc tech', 'chapter 74', 'career technical',
      'cte enrollment', 'vocational technical', 'mcas', 'next generation mcas',
      'attendance rate', 'chronic absentee', 'dropout', 'district finance',
      'low income', 'english learner', 'selected populations', 'enrollment by race',
      'enrollment by grade', 'kindergarten'
    ],
    extra: 'Chapter 74 CTE sits in derived.secondary.ma_chapter74_cte. Next Generation MCAS 2025 sits in derived.secondary.mcas_2025; attendance in attendance_2025; dropouts in dropouts_2025; district per-pupil finance in district_finance_fy2025. Race, selected-population, and grade counts sit in derived.secondary.ma_enrollment_demographics_2026. Waitlists, lottery outcomes, and a 30,000-seat target are pending: decline those.',
    latestId: 'view-trend',
    hasTable: false
  }),
  suiteTool(DL07, {
    id: 'DL-07',
    label: 'State School Scores: NAEP grade 4 reading by state, with enrollment and finance as later views',
    src: 'SRC-607-05',
    triggers: [
      'k-12 enrollment', 'k12 enrollment', 'public school enrollment',
      'public k-12', 'national k-12', 'fall 2023 enrollment',
      'fall 2024 enrollment',
      'elementary and secondary enrollment', 'naep', 'nations report card',
      'expulsion', 'expelled', 'out-of-school suspension',
      'suspension by race', 'improved on naep', 'naep grade'
    ],
    extra: 'Graduation rates, out-of-school suspension shares, and expulsion shares sit in derived.secondary. Suspension and expulsion shares by race sit in derived.secondary.discipline_race_2020_21. In-school suspension is not a column on Digest 233.40: decline those. NAEP state reading and math scores sit in derived.secondary.naep_2024.series (2024 snapshots: read4, read8, math4, math8). The all-year national-public and Massachusetts series, plus every-state 2019-to-2024 change, sit in derived.secondary.naep_2024.history. 2022-to-2024 change is the same history object without per-state rows. NPEFS FY 2024 current expenditures per pupil sit in derived.secondary.npefs_ppe_fy2024.',
    hasTrend: false
  }),
  suiteTool(DL08, {
    id: 'DL-08',
    label: 'College Enrollment: fall enrollment in degree-granting institutions by state',
    src: 'SRC-608-01',
    extraViews: ['ipeds-6yr-state', 'he-tuition'],
    triggers: [
      'college', 'college enrollment', 'higher education', 'postsecondary',
      'fall enrollment', 'degree-granting', 'university enrollment',
      'college faculty', 'students per faculty', 'college tuition',
      'in-state tuition', 'higher-education finance', 'college graduation'
    ],
    extra: 'SAT mean scores sit in derived.secondary.sat_2023. Public FTE faculty, staff, and students-per-faculty sit in derived.secondary.public_fte_faculty_fall_2023, public_fte_staff_fall_2023, and students_per_faculty_fall_2023. State 6-year bachelor\'s graduation rates sit in derived.secondary.ipeds_6yr_grad_by_state_2017. Tuition, appropriations, expenditures, degrees, and institution counts sit under derived.secondary with he_ and bachelors_ / degree_granting_ keys. National full-time faculty composition remains in faculty_composition_fall_2023. ACT state means are not in the current Digest xlsx set: decline those.'
  }),
  suiteTool(DL09, {
    id: 'DL-09',
    label: 'Charter school fall enrollment by state',
    src: 'SRC-609-01',
    triggers: [
      'charter', 'charters', 'charter school', 'charter enrollment'
    ],
    extra: 'Teacher FTE counts sit in derived.secondary.teachers_fte_fall_2022. Total staff and instructional aides sit in derived.secondary.k12_staff_fte_fall_2022 and k12_aides_fte_fall_2022.'
  }),
  suiteTool(DL10, {
    id: 'DL-10',
    label: 'Massachusetts hospitals from CMS Hospital General Information, including overall star ratings',
    src: 'SRC-610-02',
    uppercase: false,
    hl: 'the exact hospital name as written in entities if the question focuses on one facility, else null',
    triggers: [
      'massachusetts hospitals', 'massachusetts hospital', 'hospital rating',
      'cms hospital', 'hospital star', 'how many hospitals',
      'relative price', 'chia relative', 'chia hospital'
    ],
    extra: 'CHIA CY 2023 statewide commercial relative prices sit in derived.secondary.chia_srp_2023. CMS city, emergency, and star-mix detail sits in derived.secondary.cms_hospital_depth. This is not a care-advice tool. Decline where-to-seek-care questions.',
    latestId: 'view-proof'
  }),
  (function () {
    var t = suiteTool(DL11, {
      id: 'DL-11',
      label: '340B participating covered-entity sites, hospital charity-care shares, and contract pharmacies by 2024 state house district',
      src: 'SRC-611-01',
      extraViews: ['charity', 'districts'],
      triggers: [
        '340b', '340 b', 'covered entity', 'covered entities', 'opais',
        'contract pharmacy', 'contract pharmacies', 'charity care',
        'legislative mapping', 'state house district', 'hrsa opa'
      ],
      extra: 'Program growth is participating 340B IDs on the OPAIS daily export (SRC-611-01). The start-year trend is the current participating roster, not a reconstructed historical stock. Charity-care shares sit in derived.secondary.charity_care from the CMS Hospital Provider Cost Report PUF (SRC-611-02); RAND TL-303 is the method citation (SRC-611-04). Unique pharmacies by 2024 state house district sit in derived.secondary.legislative (SRC-611-03). A ZIP can cross district lines. Decline hospital or manufacturer advice and federal-rule forecasts.'
    });
    t.coreSlice = function (d) {
      var c = suiteCore(d);
      if (c.derived && c.derived.secondary && c.derived.secondary.legislative) {
        var sec = {};
        Object.keys(c.derived.secondary).forEach(function (k) { sec[k] = c.derived.secondary[k]; });
        var drop = { rows: 1, ma_districts: 1, fl_districts: 1, district_rows: 1 };
        var leg = {};
        Object.keys(sec.legislative).forEach(function (k) {
          if (!drop[k]) leg[k] = sec.legislative[k];
        });
        sec.legislative = leg;
        c.derived = Object.assign({}, c.derived, { secondary: sec });
      }
      return c;
    };
    return t;
  }()),
  suiteTool(DL12, {
    id: 'DL-12',
    label: 'Medicaid Medical Assistance Program net expenditures by state, FY 2024',
    src: 'SRC-612-01',
    triggers: [
      'medicaid', 'medicaid spending', 'medicaid expenditures', 'map net expenditures',
      'medicaid fraud', 'mfcu', 'fraud recover'
    ],
    extra: 'MFCU recoveries sit in derived.secondary.mfcu_recoveries_fy2025. NASBO health-chapter totals are PDF-only: decline those.'
  }),
  suiteTool(DL13, {
    id: 'DL-13',
    label: 'Business formation: seasonally adjusted business applications by state',
    src: 'SRC-613-01',
    triggers: [
      'business applications', 'business formation', 'new businesses',
      'bfs', 'startup applications', 'applications to start',
      'business births', 'business deaths', 'establishment birth',
      'establishment death', 'births and deaths', 'birth rate',
      'death rate', 'formation rate', 'high-propensity', 'high propensity',
      'projected formation', 'per 100,000', 'applications per'
    ],
    extra: 'Establishment birth and death rates for every state sit in derived.secondary.bed_births_deaths and derived.windows. U.S. counts there are thousands of establishments; state counts are establishments. Deaths lag three quarters. Trailing 4-quarter and 9-quarter mean ranks, including the 9 quarters ending 2024 Q3, are precomputed: use those, do not average unpublished quarters. High-propensity applications and projected 4-quarter formations sit in derived.secondary. Census BDS firm births are not in this ledger.'
  }),
  suiteTool(DL14, {
    id: 'DL-14',
    label: 'State Unemployment: seasonally adjusted unemployment rate by state',
    src: 'SRC-614-01',
    triggers: [
      'unemployment', 'unemployment rate', 'jobless', 'laus',
      'labor force', 'labor-force', 'seasonally adjusted unemployment',
      'ui claims', 'initial claims', 'unemployment insurance claims',
      'labor force participation', 'labor-force participation',
      'labor participation', 'labour participation',
      'participation rate', 'lfpr',
      'employment-population', 'epop'
    ],
    extra: 'The U.S. civilian unemployment rate is not in the LAUS statewide file: do not invent it. Trailing 12-month and 36-month mean ranks sit in derived.windows. QCEW weekly wages sit in derived.secondary.qcew_avg_weekly_wage_2025q4; the quarterly employment and wage cube sits in derived.secondary.qcew_quarter_stack. UI initial claims sit in derived.secondary.ui_initial_claims. Labor-force participation, employment-population ratio, employment, and labor-force levels sit in derived.secondary.laus_labor_2026. A named-state question uses by_st[ST] on that snap (for example by_st.WY), or rows when the full slice is present. Do not decline a state that appears in by_st. CPS age-sex-race detail is not posted: decline those.'
  }),
  suiteTool(DL15, {
    id: 'DL-15',
    label: 'State real GDP, chained 2017 dollars, all industry',
    src: 'SRC-615-01',
    triggers: [
      'real gdp', 'state gdp', 'gross domestic product', 'chained 2017',
      'economic output', 'gdp by state', 'naics', 'manufacturing gdp'
    ],
    extra: 'Personal income sits in derived.secondary.personal_income_2025. SAGDP2 current-dollar GDP by NAICS sits in derived.secondary.sagdp2_naics_2025.industries. Real GDP figures are millions of chained 2017 dollars; SAGDP2 figures are millions of current dollars; say that in prose.'
  }),
  suiteTool(DL16, {
    id: 'DL-16',
    label: 'Housing units authorized by building permit, year-to-date by state',
    src: 'SRC-616-01',
    triggers: [
      'building permits', 'housing permits', 'housing units',
      'units authorized', 'housing production', 'permit-issuing',
      'case-shiller', 'case shiller', 'boston house price'
    ],
    extra: 'FHFA house-price annual change sits in derived.secondary.fhfa_hpi_annual_change_2025. The Case-Shiller Boston MSA index sits in derived.secondary.case_shiller_boston (FRED BOXRSA). Boston is the only Massachusetts city in that series. FHFA has no U.S. row in that state file.'
  }),
  suiteTool(DL17, {
    id: 'DL-17',
    label: 'State population and domestic migration from Census vintage estimates',
    src: 'SRC-617-01',
    triggers: [
      'domestic migration', 'state population', 'population estimate',
      'vintage 2025', 'who is moving', 'rural-urban', 'rural urban continuum',
      'rucc', 'census births', 'census-estimated births', 'census deaths',
      'international migration', 'population change', 'age 65', 'hispanic share'
    ],
    extra: 'The ranking is DOMESTICMIG, not total population. Births, deaths, natural change, international migration, and NPOPCHG sit in derived.secondary.births_2025, deaths_2025, natural_change_2025, international_mig_2025, and pop_change_2025. IRS taxpayer migration sits on DL-20. Municipal populations sit on DL-25. USDA rural-urban continuum codes sit in derived.secondary.rucc_2023. Age and race shares sit in derived.secondary.pop_age_65plus_share_2025, pop_age_0_17_share_2025, pop_hispanic_share_2025, and pop_white_nh_share_2025.'
  }),
  suiteTool(DL19, {
    id: 'DL-19',
    label: 'Regional price parities, all items, United States = 100',
    src: 'SRC-619-01',
    triggers: [
      'cost of living', 'regional price', 'price parity', 'rpp',
      'how expensive is', 'housing prices parity', 'rpp housing'
    ],
    extra: 'Component RPPs (goods, housing, utilities, other services) sit in derived.secondary.rpp_components_2024.components. Tariff, defense, and fiscal-dependency measures are Pioneer products and are pending: decline those. Do not invent a Census substitute. United States is 100 by construction.'
  }),
  suiteTool(DL20, {
    id: 'DL-20',
    label: 'IRS net domestic taxpayer migration, returns in minus returns out',
    src: 'SRC-620-01',
    triggers: [
      'taxpayer migration', 'taxpayers leaving', 'filers leaving',
      'irs migration', 'state-to-state migration', 'returns in and out',
      'where did massachusetts taxpayers', 'taxpayers move', 'went to florida',
      'taxpayer returns'
    ],
    extra: 'Census domestic migration sits on DL-17. Massachusetts county nets sit in derived.secondary.ma_county_taxpayer_migration_2022_23. Origin-destination pairs, including Massachusetts to Florida, sit in derived.secondary.state_pair_flows_2022_23. Decline relocation advice.'
  }),
  suiteTool(DL21, {
    id: 'DL-21',
    label: 'IRS Statistics of Income: adjusted gross income and return counts by state',
    src: 'SRC-621-01',
    triggers: [
      'adjusted gross income', 'agi', 'tax year 2022', 'soi historic',
      'number of returns', 'income statistics', 'county agi',
      'county adjusted gross', 'million-plus', 'size of agi', 'tracking wealth'
    ],
    extra: 'This is AGI and return counts, not statutory tax rates (those sit on DL-01) and not quarterly state tax collections (DL-28 and DL-29). Massachusetts county AGI sits in derived.secondary.ma_county_agi_2022. Size-of-AGI stubs, including the million-plus AGI share, sit in derived.secondary.agi_stubs_2022. A dedicated AGI-percentile-by-state file is not posted: decline those.'
  }),
  suiteTool(DL22, {
    id: 'DL-22',
    label: 'U.S. transit agency unlinked passenger trips from FTA NTD, latest month',
    src: 'SRC-622-01',
    uppercase: false,
    hl: 'the exact agency name as written in entities if the question focuses on one agency, else null',
    triggers: [
      'transit agencies', 'transit agency', 'compare systems', 'compare transit',
      'ntd ridership', 'which transit agency', 'largest transit',
      'ntd operating', 'agency operating cost', 'agency farebox'
    ],
    extra: 'This is agency-level monthly ridership plus NTD report-year 2024 operating cost and farebox in derived.secondary.ntd_annual_2024. MBTA mode-by-mode reliability stays on DL-03.'
  }),
  suiteTool(DL23, {
    id: 'DL-23',
    label: 'Annual vehicle-miles of travel by state from FHWA VM-2',
    src: 'SRC-623-01',
    extraViews: ['degree-days'],
    triggers: [
      'vehicle-miles', 'vehicle miles', 'vmt', 'roadway travel',
      'miles driven', 'highway statistics', 'fema obligated',
      'national risk index', 'heating degree', 'cooling degree'
    ],
    extra: 'OpenFEMA Public Assistance obligations sit in derived.secondary.fema_pa_obligations; National Risk Index scores in nri_mean_county_score; NOAA degree days in noaa_degree_days_2024 when present. Transit agencies sit on DL-03 or DL-22.'
  }),
  suiteTool(DL24, {
    id: 'DL-24',
    label: 'Energy-related carbon dioxide emissions by state',
    src: 'SRC-624-01',
    triggers: [
      'carbon dioxide', 'co2', 'energy emissions', 'emissions from energy',
      'state emissions', '2024 emissions', 'energy production',
      'seds production', 'energy produce', 'energy consumption',
      'consumes', 'produce more energy'
    ],
    extra: 'Retail electricity prices sit on DL-04. SEDS consumption sits in derived.secondary.seds_consumption_2024. SEDS production sits in derived.secondary.seds_production_2024.'
  }),
  suiteTool(DL25, {
    id: 'DL-25',
    label: 'Massachusetts city and town population, Census subcounty estimates',
    src: 'SRC-625-01',
    uppercase: false,
    hl: 'the municipality as written in entities (Boston city, Lexington town) if the question focuses on one place, else null. Pages display those names without the city or town suffix.',
    triggers: [
      'massachusetts towns', 'massachusetts cities', 'municipal population',
      'city or town', 'boston population', 'population of boston',
      'population peers', 'peer towns', 'median household income',
      'town income', 'home value'
    ],
    extra: 'Population peers sit in derived.secondary.population_peers_2025 (five nearest Census 2025 counts). ACS 2020-2024 income, home value, poverty, education, age, and socioeconomic peers sit in derived.secondary.acs_towns_2024. ACS peers are z-scored income, home value, and bachelor\'s share, not the old Pioneer workbook. A DLS levy file is not a stable public CSV: decline those. Statewide population sits on DL-17. Boston payroll sits on DL-27.'
  }),
  suiteTool(DL26, {
    id: 'DL-26',
    label: 'Massachusetts municipal population change, 2020 to 2025',
    src: 'SRC-626-01',
    uppercase: false,
    hl: 'the exact municipality name as written in entities if the question focuses on one city or town, else null',
    triggers: [
      'town grew', 'towns growing', 'municipal rankings', 'population change',
      'which town grew', 'fastest growing town', 'poverty rate',
      'highest income town'
    ],
    extra: 'DESE district per-pupil education rankings sit in derived.secondary.district_ppe_fy2025. ACS 2020-2024 income, poverty, home-value, and bachelor\'s rankings sit in derived.secondary.acs_rankings_2024. DLS debt, levy, revenue, tax, and municipal crime files are not stable public CSVs: decline those. The headline ranking is 2025 minus 2020 population.'
  }),
  suiteTool(DL27, {
    id: 'DL-27',
    label: 'City of Boston department earnings, calendar year 2025',
    src: 'SRC-627-01',
    extraViews: ['bos-pay-trend'],
    uppercase: false,
    hl: 'the exact department name as written in entities if the question focuses on one department, else null',
    triggers: [
      'boston payroll', 'boston city payroll', 'boston earnings',
      'city of boston payroll', 'boston police department', 'boston departments',
      'boston employee', 'highest paid boston', 'boston top earner'
    ],
    extra: 'The FY26 operating budget sits in derived.secondary.boston_operating_budget_fy26. Named top earners sit in derived.secondary.boston_top_earners_2025; answer those names. The 2015-2025 citywide earnings trend sits in derived.secondary.boston_payroll_trend. Statewide payroll sits on DL-30. Decline a named-employee lookup that is not on the published top list.'
  }),
  suiteTool(DL28, {
    id: 'DL-28',
    label: 'Massachusetts state tax collections by type, Census QTAX latest quarter',
    src: 'SRC-628-01',
    uppercase: false,
    hl: 'the exact tax-type name as written in entities if the question focuses on one source, else null',
    triggers: [
      'massachusetts tax collections', 'commonwealth tax', 'qtax massachusetts',
      'massachusetts collected', 'massachusetts collect', 'ma state taxes'
    ],
    extra: 'The 51-state ranking sits on DL-29. QTAX type shares sit in derived.secondary.qtax_type_shares_2026q1. Census STC FY 2023 annual collections sit in derived.secondary.stc_ma_2023. DOR monthly reports and tax credits are pending. Statutory rates sit on DL-01.'
  }),
  suiteTool(DL29, {
    id: 'DL-29',
    label: 'State government tax collections by state, Census QTAX latest quarter',
    src: 'SRC-629-01',
    extraViews: ['aspp-hold'],
    triggers: [
      'state tax collections', 'state tax', 'which state collected', 'qtax',
      'quarterly tax revenue', 'state government taxes',
      'state employees', 'public employment', 'aspep',
      'government units', 'government organizations',
      'state and local revenue', 'state and local expenditure',
      'aspp', 'public pension cash', 'public pension holdings',
      'rainy-day', 'rainy day', 'income tax share'
    ],
    extra: 'The Massachusetts type-of-tax split sits on DL-28. ASPEP 2023 state FTE employment sits in derived.secondary.aspep_fte_2023. Census STC FY 2023 totals and income-tax shares sit in derived.secondary.stc_2023. State-and-local revenue and expenditure sit in derived.secondary.aslg_revenue_2022 and aslg_expenditure_2022. Government-unit counts sit in derived.secondary.gov_units_2022. Public pension cash and investments sit in derived.secondary.aspp_holdings_2025. NASBO rainy-day funds and party dominance are pending. Massachusetts retirement boards sit on DL-05. Excludes D.C.'
  }),
  suiteTool(DL30, {
    id: 'DL-30',
    label: 'Massachusetts Commonwealth payroll by department from CTHRU, plus Comptroller spending',
    src: 'SRC-630-01',
    uppercase: false,
    hl: 'the exact department name as written in entities if the question focuses on one department, else null',
    triggers: [
      'commonwealth payroll', 'state agency payroll', 'cthru payroll',
      'massachusetts state payroll', 'vendor payments', 'comptroller spending',
      'quasi-public', 'quasi public payroll'
    ],
    extra: 'Decline named-employee lookups. Named House and Senate pay sits on DL-32. Boston city payroll sits on DL-27. Retiree pensions sit on DL-05. Quasi-public payroll sits in derived.secondary.quasi_payroll_2025. The vendor-only extract sits in derived.secondary.vendor_extract_fy2025. Spending on the headline KPI is the Comptroller all-object-class total.'
  }),
  suiteTool(DL31, {
    id: 'DL-31',
    label: 'Prisoners under state or federal jurisdiction, year-end count by state',
    src: 'SRC-631-02',
    triggers: [
      'prisoners', 'incarceration', 'prison population', 'how many prisoners',
      'correctional authorities', 'bjs prisoners', 'imprisonment rate',
      'prison admissions', 'juveniles in prison'
    ],
    extra: 'Imprisonment rates, admissions, releases, and youth in adult prisons sit in derived.secondary.bjs_depth_2023. FBI crime rates and IC3 internet-crime reports are pending: decline those. Youth counts are prisoners age 17 or younger in adult prisons, not OJJDP juvenile-justice custody. Municipal crime rankings are pending. This ledger is not a Boston crime rate.'
  }),
  suiteTool(DL32, {
    id: 'DL-32',
    label: 'Massachusetts legislator pay: named House and Senate salary, supplemental pay, and stipends',
    src: 'SRC-632-01',
    uppercase: false,
    hl: 'the exact legislator name as written in entities if the question focuses on one member, else null',
    triggers: [
      'legislator', 'legislators', 'legislature pay', 'legislative pay',
      'representative salary', 'senator salary', 'house speaker',
      'senate president', 'legislative stipend', 'legislative compensation',
      'general court pay', 'ma legislator', 'massachusetts legislator',
      'how much are legislators', 'how much is the speaker',
      'gic health', 'office-expense', 'leadership premium'
    ],
    extra: 'Answer named Representative and Senator pay from the rows. Total pay is base plus AA1 (Comptroller supplemental) plus A14 (stipends). Employer-paid GIC health and MSERS pension contributions are not in this file: decline those as unpublished and do not invent them. The office-expense allowance is not a named column here. Calendar 2026 is year-to-date and is not the headline. Decline advice about a member. Statewide department payroll sits on DL-30. Retiree pensions sit on DL-05.'
  })
];
