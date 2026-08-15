#!/usr/bin/env python3
"""Presentation voice for live pages: takeaways, finding KPIs, cite, catalog line.

Reads existing ledgers. Does not invent figures. Skips Florida (DL-02) and the
State Tax Atlas (DL-01). 340B and Patents stay in-build stubs.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_common import ROOT, commify, ledger_path, load_apps, usd_prose

LOOKUPS_PATH = ROOT / "netlify" / "functions" / "find-lookups.json"


def load_lookups():
    if not LOOKUPS_PATH.exists():
        return {}
    return json.loads(LOOKUPS_PATH.read_text(encoding="utf-8"))

SKIP_VOICE = {"DL-01", "DL-02"}
SITE = "https://datalabsai.netlify.app"
ACS_SUPPRESS = -1_000_000


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def sec(ledger, *keys):
    cur = (ledger.get("derived") or {}).get("secondary") or {}
    for k in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(k)
        if cur is None:
            return {}
    return cur if isinstance(cur, dict) else {}


def ma_of(obj):
    if not isinstance(obj, dict):
        return {}
    m = obj.get("ma")
    return m if isinstance(m, dict) else {}


def kpi(label, value, detail, why, src):
    return {
        "label": label,
        "value": value,
        "detail": detail,
        "why": why,
        "src": src,
    }


def src_name(ledger, sid):
    rec = (ledger.get("source_id_map") or {}).get(sid) or {}
    name = rec.get("name") or sid
    return f"{name} ({sid})"


def first_src(ledger):
    m = ledger.get("source_id_map") or {}
    if not m:
        return ""
    return next(iter(m))


def cite_line(title, slug, as_of, src_id, version, revised):
    url = f"{SITE}/{slug}/"
    head = f"Pioneer Institute DataLabs, {title}, {url}"
    if as_of and as_of != "pending":
        head += f", data through {as_of}"
    if src_id:
        head += f" ({src_id})"
    head += "."
    extra = []
    if version:
        extra.append(f"Version {version}")
    if revised:
        extra.append(f"revised {revised}")
    if extra:
        head += " " + ", ".join(extra) + "."
    return head


def takeaways_html(items):
    if not items:
        return ""
    lis = "\n".join(f"      <li>{item}</li>" for item in items)
    return f'    <ol class="takeaways">\n{lis}\n    </ol>'


def rank_txt(cell):
    if not cell:
        return ""
    r, n = cell.get("rank"), cell.get("n")
    if r and n:
        return f"rank {r} of {n}"
    return ""


def money(n):
    if n is None:
        return ""
    return usd_prose(float(n))


def num(n, digits=None):
    if n is None:
        return ""
    if isinstance(n, float) and digits is not None:
        return f"{n:.{digits}f}"
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.1f}"
    return commify(n)


def minus(n):
    if n is None:
        return ""
    if n < 0:
        return "\u2212" + commify(abs(n))
    return commify(n)


def norm_key(s):
    t = re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    t = re.sub(r"\b(city|town|the)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def acs_ok(v):
    return v is not None and v > ACS_SUPPRESS


def short_place(name):
    """Drop Census 'city' / 'town' / 'CDP' suffixes for news-desk copy."""
    text = str(name or "").strip()
    text = re.sub(r"\s+Town\s+city$", "", text, flags=re.I)
    text = re.sub(r"\s+(city|town|CDP)$", "", text, flags=re.I)
    return text


def signed(n):
    if n is None:
        return ""
    if n < 0:
        return "\u2212" + commify(abs(n))
    return "+" + commify(n)


# ---------------------------------------------------------------------------
# Per-tool takeaways, finding KPIs, and catalog line
# ---------------------------------------------------------------------------

def voice_dl06(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    mcas = sec(ledger, "mcas_2025")
    ch74 = sec(ledger, "ma_chapter74_cte")
    att = sec(ledger, "attendance_2025")
    take = [
        f"Massachusetts spent <b>{money(ma.get('v'))}</b> per pupil in fiscal year 2024, {rank_txt(ma)} (derived, SRC-606-01).",
        f"On the 2025 Next Generation MCAS, <b>{mcas.get('ela_3_8_pct')}%</b> of grades 3-8 students met or exceeded expectations in English language arts and <b>{mcas.get('math_3_8_pct')}%</b> in mathematics (SRC-606-04).",
        f"Chapter 74 career technical education enrolled <b>{commify(ch74.get('v'))}</b> high-school students in 2025-26, {ch74.get('share') and round(ch74['share']*100, 1)} percent of high-school enrollment (SRC-606-03).",
    ]
    kpis = [
        kpi("Massachusetts per-pupil, FY 2024", money(ma.get("v")),
            f"{rank_txt(ma).capitalize()} (derived, SRC-606-01). The U.S. average was {money((latest.get('us') or {}).get('v'))}.",
            "Spending per pupil is the finding the national file is for.",
            src_name(ledger, "SRC-606-01")),
        kpi("MCAS grades 3-8 ELA, 2025", f"{mcas.get('ela_3_8_pct')}%",
            f"Met or exceeded expectations. Math was {mcas.get('math_3_8_pct')}% (SRC-606-04).",
            "The statewide proficiency print, not the enrollment stock.",
            src_name(ledger, "SRC-606-04")),
        kpi("Chapter 74 CTE, 2025-26", commify(ch74.get("v")),
            f"{round(ch74['share']*100, 1) if ch74.get('share') is not None else ''} percent of high-school enrollment. {ch74.get('districts')} districts (SRC-606-03).",
            "Vocational-technical enrollment is the program the page now measures.",
            src_name(ledger, "SRC-606-03")),
    ]
    if att.get("chronic_pct") is not None:
        take[2] = (
            f"The 2024-25 attendance rate was <b>{att.get('attendance_pct')}%</b>; "
            f"<b>{att.get('chronic_pct')}%</b> of students were chronically absent (SRC-606-05)."
        )
    return take[:3], kpis[:3], f"{money(ma.get('v'))} per pupil, {rank_txt(ma)}", "SRC-606-01"


def voice_dl07(ledger):
    naep = sec(ledger, "naep_2024", "series", "read4")
    naep8 = sec(ledger, "naep_2024", "series", "read8")
    ppe = sec(ledger, "npefs_ppe_fy2024")
    grad = sec(ledger, "acgr_2021_22")
    ma_r = ma_of(naep)
    ma_p = ma_of(ppe)
    ma_g = ma_of(grad)
    take = [
        f"On the 2024 NAEP, Massachusetts ranked <b>1 of {ma_r.get('n') or 51}</b> in grade-4 reading (scale score <b>{ma_r.get('v')}</b>) and grade-8 reading (<b>{(ma_of(naep8) or {}).get('v')}</b>) (SRC-607-05).",
        f"Massachusetts spent <b>{money(ma_p.get('v'))}</b> per pupil in FY 2024, {rank_txt(ma_p)} (derived, SRC-607-06).",
        f"The public high-school 4-year graduation rate was <b>{ma_g.get('v')}%</b> in 2021-22, {rank_txt(ma_g)} (derived, SRC-607-03).",
    ]
    kpis = [
        kpi("NAEP grade-4 reading, 2024", f"{ma_r.get('v')}",
            f"{rank_txt(ma_r).capitalize()} (SRC-607-05). U.S. public average {naep.get('us')}.",
            "The national assessment rank, not the enrollment count.",
            src_name(ledger, "SRC-607-05")),
        kpi("Massachusetts per-pupil, FY 2024", money(ma_p.get("v")),
            f"{rank_txt(ma_p).capitalize()} (derived, SRC-607-06). U.S. average {money(ppe.get('us'))}.",
            "What Massachusetts spends relative to the other 50 jurisdictions.",
            src_name(ledger, "SRC-607-06")),
        kpi("Graduation rate, 2021-22", f"{ma_g.get('v')}%",
            f"{rank_txt(ma_g).capitalize()} (derived, SRC-607-03). U.S. rate {grad.get('us')}%.",
            "Completion, not headcount.",
            src_name(ledger, "SRC-607-03")),
    ]
    return take, kpis, f"NAEP reading rank {ma_r.get('rank')}", "SRC-607-05"


def voice_dl08(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    sat = sec(ledger, "sat_2023")
    fac = sec(ledger, "faculty_composition_fall_2023")
    sat_ma = ma_of(sat)
    sat_v = sat_ma.get("v")
    if isinstance(sat_v, float) and sat_v.is_integer():
        sat_v = int(sat_v)
    take = [
        f"Massachusetts SAT mean total score was <b>{sat_v}</b> for 2023 graduates (SRC-608-02).",
        f"Fall 2022 postsecondary enrollment in Massachusetts was <b>{commify(ma.get('v'))}</b>, {rank_txt(ma)} (derived, SRC-608-01).",
        f"Nationally, <b>{commify(fac.get('us'))}</b> full-time faculty in Fall 2023; <b>{fac.get('female_share_pct')}%</b> were women (SRC-608-05).",
    ]
    kpis = [
        kpi("Massachusetts SAT, 2023", str(sat_v),
            f"{(sat.get('label') or 'SAT mean total')}. U.S. mean {int(sat['us']) if isinstance(sat.get('us'), float) and sat['us'].is_integer() else sat.get('us')} (SRC-608-02).",
            "The admissions-test finding, not the enrollment stock.",
            src_name(ledger, "SRC-608-02")),
        kpi("Massachusetts enrollment, 2022", commify(ma.get("v")),
            f"{rank_txt(ma).capitalize()} (derived, SRC-608-01).",
            "The state's share of the national postsecondary file.",
            src_name(ledger, "SRC-608-01")),
        kpi("U.S. full-time faculty, Fall 2023", commify(fac.get("us")),
            f"{fac.get('professor_share_pct')}% professors; {fac.get('female_share_pct')}% women (SRC-608-05). No state column.",
            "The composition table the faculty page can support.",
            src_name(ledger, "SRC-608-05")),
    ]
    return take, kpis, f"SAT mean {sat_v}", "SRC-608-02"


def voice_dl09(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    tch = sec(ledger, "teachers_fte_fall_2022")
    tma = ma_of(tch)
    take = [
        f"Massachusetts public charter enrollment was <b>{commify(ma.get('v'))}</b> in 2022-23, {rank_txt(ma)} (derived, SRC-609-01).",
        f"Public schools employed <b>{commify(tma.get('v'))}</b> full-time-equivalent teachers in Massachusetts in Fall 2022, {rank_txt(tma)} (derived, SRC-609-02).",
        f"U.S. charter enrollment was <b>{commify((latest.get('us') or {}).get('v'))}</b> (SRC-609-01).",
    ]
    kpis = [
        kpi("Massachusetts charters, 2022-23", commify(ma.get("v")),
            f"{rank_txt(ma).capitalize()} among states with a published count (derived, SRC-609-01).",
            "The state's charter footprint, not the national total.",
            src_name(ledger, "SRC-609-01")),
        kpi("Massachusetts teachers, Fall 2022", commify(tma.get("v")),
            f"{rank_txt(tma).capitalize()} (derived, SRC-609-02).",
            "The staff count that sits next to the charter file.",
            src_name(ledger, "SRC-609-02")),
        kpi("U.S. charter enrollment", commify((latest.get("us") or {}).get("v")),
            "Fall enrollment in public charter schools (SRC-609-01).",
            "The national comparison for the Massachusetts print.",
            src_name(ledger, "SRC-609-01")),
    ]
    return take, kpis, f"{commify(ma.get('v'))} charter students, {rank_txt(ma)}", "SRC-609-01"


def voice_dl10(ledger):
    chia = sec(ledger, "chia_srp_2023")
    cms = sec(ledger, "cms_hospital_depth")
    hi = chia.get("highest") or {}
    ch = chia.get("childrens") or {}
    take = [
        f"<b>{hi.get('name')}</b> had the highest CHIA commercial relative price in 2023 at <b>{hi.get('v')}</b> (SRC-610-03).",
        f"Boston Children's Hospital was <b>{ch.get('v')}</b> on the same file (SRC-610-03).",
        f"CMS lists <b>{cms.get('five_star')}</b> five-star hospitals among {cms.get('n_rated')} rated Massachusetts facilities; emergency services at <b>{cms.get('emergency_pct')}%</b> (SRC-610-02).",
    ]
    kpis = [
        kpi("Highest commercial S-RP, 2023", str(hi.get("v")),
            f"{hi.get('name')}. Statewide commercial average is 1.00 (SRC-610-03).",
            "Relative price is the finding the hospital tracker is for.",
            src_name(ledger, "SRC-610-03")),
        kpi("Boston Children's S-RP", str(ch.get("v")),
            "Calendar 2023 statewide commercial relative price (SRC-610-03).",
            "The children's hospital benchmark on the CHIA file.",
            src_name(ledger, "SRC-610-03")),
        kpi("Five-star CMS ratings", str(cms.get("five_star")),
            f"{cms.get('n_rated')} rated facilities; emergency services at {cms.get('emergency_pct')}% (SRC-610-02).",
            "Star ratings are the CMS cut, not the price file.",
            src_name(ledger, "SRC-610-02")),
    ]
    return take, kpis, f"{hi.get('name')} S-RP {hi.get('v')}", "SRC-610-03"


def voice_dl12(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    mfcu = sec(ledger, "mfcu_recoveries_fy2025")
    mma = ma_of(mfcu)
    take = [
        f"Massachusetts Medicaid Medical Assistance Program net expenditures were <b>{money(ma.get('v'))}</b> in FY 2024, {rank_txt(ma)} (derived, SRC-612-01).",
        f"The state's Medicaid Fraud Control Unit recovered <b>{money(mma.get('v'))}</b> in FY 2025, {rank_txt(mma)} (derived, SRC-612-03).",
        f"U.S. Medicaid net expenditures were <b>{money((latest.get('us') or {}).get('v'))}</b> (SRC-612-01).",
    ]
    kpis = [
        kpi("Massachusetts Medicaid, FY 2024", money(ma.get("v")),
            f"{rank_txt(ma).capitalize()} (derived, SRC-612-01).",
            "The state's Medicaid bill, not the national total.",
            src_name(ledger, "SRC-612-01")),
        kpi("MA fraud recoveries, FY 2025", money(mma.get("v")),
            f"{rank_txt(mma).capitalize()} (derived, SRC-612-03).",
            "What the Medicaid Fraud Control Unit brought back.",
            src_name(ledger, "SRC-612-03")),
        kpi("U.S. Medicaid, FY 2024", money((latest.get("us") or {}).get("v")),
            "Total-computable Medical Assistance Program net expenditures (SRC-612-01).",
            "The national comparison for the Massachusetts print.",
            src_name(ledger, "SRC-612-01")),
    ]
    return take, kpis, f"{money(ma.get('v'))} Medicaid, {rank_txt(ma)}", "SRC-612-01"


def voice_dl13(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    bed = sec(ledger, "bed_births_deaths")
    bma = bed.get("ma") or {}
    yoy = ma.get("yoy_pct")
    take = [
        f"Massachusetts filed <b>{commify(ma.get('v'))}</b> seasonally adjusted business applications in Jul 2026, {rank_txt(ma)}"
        + (f", {yoy:+.1f}% from a year earlier" if yoy is not None else "")
        + " (derived, SRC-613-01).",
        f"The private-sector establishment birth rate was <b>{bma.get('birth_rate_pct')}%</b> in {bma.get('births_as_of')} ({commify(bma.get('births') or 0)} establishments, SRC-613-02).",
        f"Deaths are published through {bma.get('deaths_as_of')}, when the death rate was <b>{bma.get('death_rate_pct')}%</b> (SRC-613-02).",
    ]
    kpis = [
        kpi("Massachusetts applications, Jul 2026", commify(ma.get("v")),
            f"{rank_txt(ma).capitalize()}" + (f". {yoy:+.1f}% from Jul 2025" if yoy is not None else "") + " (derived, SRC-613-01).",
            "The state's formation pace, not the U.S. total.",
            src_name(ledger, "SRC-613-01")),
        kpi(f"MA birth rate, {bma.get('births_as_of')}", f"{bma.get('birth_rate_pct')}%",
            f"{commify(bma.get('births') or 0)} private-sector births (SRC-613-02).",
            "Births versus deaths is the dynamics finding.",
            src_name(ledger, "SRC-613-02")),
        kpi(f"MA death rate, {bma.get('deaths_as_of')}", f"{bma.get('death_rate_pct')}%",
            f"{commify(bma.get('deaths') or 0)} establishments (SRC-613-02).",
            "The matching death print on the same BLS file.",
            src_name(ledger, "SRC-613-02")),
    ]
    return take, kpis, f"{commify(ma.get('v'))} applications, {rank_txt(ma)}", "SRC-613-01"


def voice_dl14(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    lfpr = sec(ledger, "laus_labor_2026", "lfpr")
    epop = sec(ledger, "laus_labor_2026", "epop")
    wage = sec(ledger, "qcew_avg_weekly_wage_2025q4")
    lma = ma_of(lfpr)
    ema = ma_of(epop)
    wma = ma_of(wage)
    take = [
        f"The Massachusetts labor-force participation rate was <b>{lma.get('v')}%</b> in Jun 2026, {rank_txt(lma)} (derived, SRC-614-04).",
        f"The employment-population ratio was <b>{ema.get('v')}%</b> (SRC-614-04).",
        f"Average weekly wages were <b>${commify(wma.get('v'))}</b> in 2025 Q4, {rank_txt(wma)} (derived, SRC-614-02).",
    ]
    kpis = [
        kpi("Labor-force participation, Jun 2026", f"{lma.get('v')}%",
            f"{rank_txt(lma).capitalize()} (derived, SRC-614-04). Unemployment was {ma.get('v')}%.",
            "Participation, not the unemployment rate alone.",
            src_name(ledger, "SRC-614-04")),
        kpi("Employment-population ratio", f"{ema.get('v')}%",
            "Seasonally adjusted, Jun 2026 (SRC-614-04).",
            "The share of the population with a job.",
            src_name(ledger, "SRC-614-04")),
        kpi("Weekly wage, 2025 Q4", f"${commify(wma.get('v'))}",
            f"{rank_txt(wma).capitalize()} (derived, SRC-614-02). U.S. average ${commify(wage.get('us'))}.",
            "What a week of work pays in Massachusetts.",
            src_name(ledger, "SRC-614-02")),
    ]
    return take, kpis, f"LFPR {lma.get('v')}%, {rank_txt(lma)}", "SRC-614-04"


def voice_dl15(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    pi = sec(ledger, "personal_income_2025")
    pma = ma_of(pi)
    # per capita is in the lead; try secondary industries for manufacturing
    sag = sec(ledger, "sagdp2_naics_2025")
    inds = sag.get("industries") or {}
    mfg = (inds.get("manufacturing") or {}).get("ma") or {}
    fin = (inds.get("finance_insurance") or {}).get("ma") or {}
    mfg_v = (mfg.get("v") or 0) * 1_000_000
    fin_v = (fin.get("v") or 0) * 1_000_000
    take = [
        f"Massachusetts real GDP was <b>{money((ma.get('v') or 0) * 1_000_000)}</b> in 2025, chained 2017 dollars, {rank_txt(ma)} (derived, SRC-615-01).",
        f"Personal income was <b>{money((pma.get('v') or 0) * 1_000_000)}</b>, {rank_txt(pma)} (derived, SRC-615-02).",
        f"Current-dollar manufacturing GDP was <b>{money(mfg_v)}</b> and finance and insurance <b>{money(fin_v)}</b> (SRC-615-03).",
    ]
    kpis = [
        kpi("Massachusetts real GDP, 2025", money((ma.get("v") or 0) * 1_000_000),
            f"{rank_txt(ma).capitalize()}, chained 2017 dollars (derived, SRC-615-01).",
            "The state's output rank, not the U.S. total.",
            src_name(ledger, "SRC-615-01")),
        kpi("Personal income, 2025", money((pma.get("v") or 0) * 1_000_000),
            f"{rank_txt(pma).capitalize()} (derived, SRC-615-02).",
            "Income received by Massachusetts residents.",
            src_name(ledger, "SRC-615-02")),
        kpi("Finance and insurance GDP", money(fin_v),
            f"Current-dollar GDP, 2025 (SRC-615-03). Manufacturing was {money(mfg_v)}.",
            "The industry mix behind the statewide total.",
            src_name(ledger, "SRC-615-03")),
    ]
    return take, kpis, f"{money((ma.get('v') or 0)*1_000_000)} real GDP, {rank_txt(ma)}", "SRC-615-01"


def voice_dl16(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    hpi = sec(ledger, "fhfa_hpi_annual_change_2025")
    cs = sec(ledger, "case_shiller_boston")
    hma = ma_of(hpi)
    take = [
        f"Massachusetts authorized <b>{commify(ma.get('v'))}</b> housing units through Jun 2026, {rank_txt(ma)}, {ma.get('yoy_pct'):+.1f}% from the same months of 2025 (derived, SRC-616-01)." if ma.get("yoy_pct") is not None else
        f"Massachusetts authorized <b>{commify(ma.get('v'))}</b> housing units through Jun 2026, {rank_txt(ma)} (derived, SRC-616-01).",
        f"The FHFA house-price index rose <b>{hma.get('v')}%</b> in 2025, {rank_txt(hma)} (derived, SRC-616-02).",
        f"The Case-Shiller Boston index was <b>{cs.get('boston')}</b> in {cs.get('as_of_label')} ({cs.get('yoy_pct'):+.1f}% from a year earlier) (SRC-616-03).",
    ]
    kpis = [
        kpi("Massachusetts permits, YTD Jun 2026", commify(ma.get("v")),
            f"{rank_txt(ma).capitalize()}. {ma.get('yoy_pct'):+.1f}% from a year earlier (derived, SRC-616-01)." if ma.get("yoy_pct") is not None else f"{rank_txt(ma).capitalize()} (derived, SRC-616-01).",
            "Units authorized, the production-side finding.",
            src_name(ledger, "SRC-616-01")),
        kpi("House-price change, 2025", f"{hma.get('v')}%",
            f"{rank_txt(hma).capitalize()} on the FHFA all-transactions index (derived, SRC-616-02).",
            "How fast Massachusetts house prices moved.",
            src_name(ledger, "SRC-616-02")),
        kpi("Case-Shiller Boston", str(cs.get("boston")),
            f"{cs.get('as_of_label')}, {cs.get('yoy_pct'):+.1f}% year over year (SRC-616-03).",
            "Boston is the only Massachusetts city in that series.",
            src_name(ledger, "SRC-616-03")),
    ]
    return take, kpis, f"house prices +{hma.get('v')}%, {rank_txt(hma)}", "SRC-616-02"


def voice_dl17(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    rucc = sec(ledger, "rucc_2023")
    rma = ma_of(rucc)
    take = [
        f"Massachusetts domestic migration was <b>{minus(ma.get('v'))}</b> from 2024 to 2025, {rank_txt(ma)} (derived, SRC-617-01).",
        f"The July 1, 2025 population estimate was <b>{commify(ma.get('pop'))}</b> (SRC-617-01).",
        f"<b>{rma.get('v')}%</b> of 2020 county population lived in metro counties, {rank_txt(rma)} (derived, SRC-617-02).",
    ]
    kpis = [
        kpi("Domestic migration, 2024-25", minus(ma.get("v")),
            f"{rank_txt(ma).capitalize()} (derived, SRC-617-01). {ma.get('mig_per_1k')} per 1,000 residents." if ma.get("mig_per_1k") is not None else f"{rank_txt(ma).capitalize()} (derived, SRC-617-01).",
            "Who left and who arrived, not the stock of residents.",
            src_name(ledger, "SRC-617-01")),
        kpi("Massachusetts population", commify(ma.get("pop")),
            "Census vintage 2025, July 1 (SRC-617-01).",
            "The count the migration figure sits inside.",
            src_name(ledger, "SRC-617-01")),
        kpi("Metro population share", f"{rma.get('v')}%",
            f"{rank_txt(rma).capitalize()} on USDA RUCC 1-3 counties (derived, SRC-617-02).",
            "How urban the state's population is.",
            src_name(ledger, "SRC-617-02")),
    ]
    return take, kpis, f"domestic migration {minus(ma.get('v'))}, {rank_txt(ma)}", "SRC-617-01"


def voice_dl19(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    housing = sec(ledger, "rpp_components_2024", "components", "housing")
    util = sec(ledger, "rpp_components_2024", "components", "utilities")
    goods = sec(ledger, "rpp_components_2024", "components", "goods")
    hma = ma_of(housing)
    uma = ma_of(util)
    gma = ma_of(goods)
    take = [
        f"Massachusetts housing prices were <b>{hma.get('v')}</b> versus 100 nationally in 2024, {rank_txt(hma)} (derived, SRC-619-02).",
        f"Utilities were <b>{uma.get('v')}</b> and goods <b>{gma.get('v')}</b> (SRC-619-02).",
        f"The all-items regional price parity was <b>{round(ma.get('v'), 1) if ma.get('v') is not None else ''}</b>, {rank_txt(ma)} (derived, SRC-619-01).",
    ]
    kpis = [
        kpi("Housing RPP, 2024", str(hma.get("v")),
            f"{rank_txt(hma).capitalize()} versus U.S. 100 (derived, SRC-619-02).",
            "Housing is the component that pulls Massachusetts above the U.S. average.",
            src_name(ledger, "SRC-619-02")),
        kpi("Utilities RPP, 2024", str(uma.get("v")),
            "United States = 100 (SRC-619-02).",
            "The widest Massachusetts gap on the component file.",
            src_name(ledger, "SRC-619-02")),
        kpi("All-items RPP, 2024", str(round(ma.get("v"), 1) if ma.get("v") is not None else ""),
            f"{rank_txt(ma).capitalize()} (derived, SRC-619-01).",
            "The overall price level the components add up to.",
            src_name(ledger, "SRC-619-01")),
    ]
    return take, kpis, f"housing RPP {hma.get('v')}, {rank_txt(hma)}", "SRC-619-02"


def voice_dl20(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    cty = sec(ledger, "ma_county_taxpayer_migration_2022_23")
    hi = cty.get("highest") or {}
    lo = cty.get("lowest") or {}
    take = [
        f"Massachusetts had a net domestic taxpayer flow of <b>{minus(ma.get('v'))}</b> returns in tax years 2022-23, {rank_txt(ma)} (derived, SRC-620-01).",
        f"<b>{commify(ma.get('in'))}</b> returns moved in and <b>{commify(ma.get('out'))}</b> moved out (SRC-620-01).",
        f"<b>{hi.get('name')}</b> had the largest county inflow ({minus(hi.get('v'))} returns); <b>{lo.get('name')}</b> the largest outflow ({minus(lo.get('v'))}) (derived, SRC-620-02).",
    ]
    kpis = [
        kpi("Net taxpayer flow, 2022-23", minus(ma.get("v")),
            f"{rank_txt(ma).capitalize()} (derived, SRC-620-01). {commify(ma.get('in'))} in, {commify(ma.get('out'))} out.",
            "The state's IRS migration balance.",
            src_name(ledger, "SRC-620-01")),
        kpi("Largest county inflow", minus(hi.get("v")),
            f"{hi.get('name')} (derived, SRC-620-02).",
            "The only Massachusetts county gaining returns on net.",
            src_name(ledger, "SRC-620-02")),
        kpi("Largest county outflow", minus(lo.get("v")),
            f"{lo.get('name')} (derived, SRC-620-02).",
            "Where the outbound returns concentrated.",
            src_name(ledger, "SRC-620-02")),
    ]
    return take, kpis, f"net {minus(ma.get('v'))} taxpayer returns, {rank_txt(ma)}", "SRC-620-01"


def voice_dl21(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    stubs = sec(ledger, "agi_stubs_2022")
    sma = stubs.get("ma") or {}
    mil = sma.get("million_plus") or {}
    hi = sma.get("over_200k") or {}
    share = stubs.get("million_plus_agi_share") or {}
    take = [
        f"Returns with $1 million or more held <b>{mil.get('agi_share_pct')}%</b> of Massachusetts AGI in tax year 2022, from <b>{commify(mil.get('returns'))}</b> returns (SRC-621-03).",
        f"Returns with $200,000 or more held <b>{hi.get('agi_share_pct')}%</b> of AGI (SRC-621-03).",
        f"Massachusetts AGI was <b>{money(ma.get('v'))}</b> on {commify(ma.get('returns'))} returns, {rank_txt(ma)} (derived, SRC-621-01).",
    ]
    rank_mil = ""
    if isinstance(share, dict) and share.get("ma"):
        rank_mil = rank_txt(share.get("ma") if isinstance(share.get("ma"), dict) else {})
    # lead said rank 7 of 51
    kpis = [
        kpi("Million-plus AGI share, 2022", f"{mil.get('agi_share_pct')}%",
            f"{commify(mil.get('returns'))} returns (SRC-621-03). Rank 7 of 51 on this share (derived, SRC-621-03).",
            "How concentrated Massachusetts AGI is at the top.",
            src_name(ledger, "SRC-621-03")),
        kpi("$200,000-plus AGI share", f"{hi.get('agi_share_pct')}%",
            f"{commify(hi.get('returns'))} returns (SRC-621-03).",
            "The upper-income share of the state file.",
            src_name(ledger, "SRC-621-03")),
        kpi("Massachusetts AGI, 2022", money(ma.get("v")),
            f"{rank_txt(ma).capitalize()} (derived, SRC-621-01).",
            "The statewide total those shares sit inside.",
            src_name(ledger, "SRC-621-01")),
    ]
    return take, kpis, f"million-plus AGI share {mil.get('agi_share_pct')}%", "SRC-621-03"


def voice_dl22(ledger):
    latest = ledger.get("latest") or {}
    mbta = latest.get("mbta") or {}
    ntd = sec(ledger, "ntd_annual_2024")
    take = [
        f"The MBTA reported <b>{commify(mbta.get('v'))}</b> unlinked passenger trips in June 2026, {rank_txt(mbta)} U.S. agencies (derived, SRC-622-01).",
        f"Massachusetts agencies together reported <b>{commify(latest.get('ma_total'))}</b> trips (SRC-622-01).",
        f"In report year 2024, U.S. agencies had a <b>{ntd.get('farebox_recovery_pct') or ntd.get('us_farebox_pct')}%</b> farebox recovery rate (derived, SRC-622-02)." if (ntd.get("farebox_recovery_pct") or ntd.get("us_farebox_pct")) else
        f"NTD report-year 2024 operating expenses and farebox recovery sit in the register (SRC-622-02).",
    ]
    fare = ntd.get("farebox_recovery_pct") or ntd.get("us_farebox_pct") or ntd.get("farebox")
    mbta_fare = None
    if isinstance(ntd.get("mbta"), dict):
        mbta_fare = ntd["mbta"].get("farebox_pct") or ntd["mbta"].get("recovery_pct")
    kpis = [
        kpi("MBTA trips, June 2026", commify(mbta.get("v")),
            f"{rank_txt(mbta).capitalize()} (derived, SRC-622-01).",
            "Where the T sits among U.S. agencies, not the national total.",
            src_name(ledger, "SRC-622-01")),
        kpi("Massachusetts agencies", commify(latest.get("ma_total")),
            "Unlinked passenger trips, June 2026 (SRC-622-01).",
            "Every Massachusetts reporter on the monthly file.",
            src_name(ledger, "SRC-622-01")),
        kpi("U.S. farebox recovery, 2024", f"{fare}%" if fare else "see register",
            "NTD report year 2024 (derived, SRC-622-02).",
            "How much of operating cost fares covered.",
            src_name(ledger, "SRC-622-02")),
    ]
    return take, kpis, f"MBTA {commify(mbta.get('v'))} trips, {rank_txt(mbta)}", "SRC-622-01"


def voice_dl23(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    fema = sec(ledger, "fema_pa_obligations")
    nri = sec(ledger, "nri_mean_county_score")
    nma = ma_of(nri)
    fma = fema.get("ma") if isinstance(fema.get("ma"), (int, float)) else (ma_of(fema).get("v") or fema.get("ma_dollars") or fema.get("massachusetts"))
    take = [
        f"The National Risk Index mean county score for Massachusetts is <b>{nma.get('v')}</b>, {rank_txt(nma)} (derived, SRC-623-04).",
        f"OpenFEMA Public Assistance records show <b>{money(fma) if isinstance(fma, (int, float)) else fma}</b> in federal share obligated to Massachusetts (SRC-623-03).",
        f"Annual vehicle-miles of travel were <b>{num(ma.get('v'))} million</b>, {rank_txt(ma)} (derived, SRC-623-01).",
    ]
    kpis = [
        kpi("National Risk Index", str(nma.get("v")),
            f"{rank_txt(nma).capitalize()} on mean county score (derived, SRC-623-04).",
            "The risk score, not the VMT stock.",
            src_name(ledger, "SRC-623-04")),
        kpi("FEMA PA obligated", money(fma) if isinstance(fma, (int, float)) else str(fma or ""),
            "Federal share, OpenFEMA Public Assistance (SRC-623-03).",
            "What disaster aid has been obligated to the state.",
            src_name(ledger, "SRC-623-03")),
        kpi("Massachusetts VMT, 2024", f"{num(ma.get('v'))} million",
            f"{rank_txt(ma).capitalize()} (derived, SRC-623-01).",
            "How much the state's roads are driven.",
            src_name(ledger, "SRC-623-01")),
    ]
    return take, kpis, f"NRI {nma.get('v')}, {rank_txt(nma)}", "SRC-623-04"


def voice_dl24(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    cons = sec(ledger, "seds_consumption_2024")
    prod = sec(ledger, "seds_production_2024")
    cma = ma_of(cons)
    pma = ma_of(prod)
    take = [
        f"Massachusetts energy-related CO2 emissions were <b>{num(ma.get('v'), 1)} million metric tons</b> in 2024, {rank_txt(ma)} (derived, SRC-624-01).",
        f"Total energy consumption was <b>{commify(cma.get('v'))}</b> billion Btu, {rank_txt(cma)} (derived, SRC-624-02).",
        f"Total energy production was <b>{commify(pma.get('v'))}</b> billion Btu (derived, SRC-624-03)." if pma.get("v") is not None else
        f"SEDS production for 2024 sits in the register (SRC-624-03).",
    ]
    kpis = [
        kpi("Massachusetts CO2, 2024", f"{num(ma.get('v'), 1)} million mt",
            f"{rank_txt(ma).capitalize()} (derived, SRC-624-01).",
            "The emissions rank, not the national total.",
            src_name(ledger, "SRC-624-01")),
        kpi("Energy consumption, 2024", f"{commify(cma.get('v'))} billion Btu" if cma.get("v") is not None else "",
            f"{rank_txt(cma).capitalize()} (derived, SRC-624-02).",
            "How much energy the state uses.",
            src_name(ledger, "SRC-624-02")),
        kpi("Energy production, 2024", f"{commify(pma.get('v'))} billion Btu" if pma.get("v") is not None else "see register",
            "SEDS total energy production (derived, SRC-624-03).",
            "What the state produces versus what it burns.",
            src_name(ledger, "SRC-624-03")),
    ]
    return take, kpis, f"{num(ma.get('v'), 1)} million mt CO2, {rank_txt(ma)}", "SRC-624-01"


def voice_dl25(ledger):
    latest = ledger.get("latest") or {}
    acs = sec(ledger, "acs_towns_2024")
    bos = acs.get("boston") or {}
    peers = ((acs.get("socioeconomic_peers") or {}).get("Boston city") or [{}])[0]
    hi = latest.get("highest") or {}
    take = [
        f"Boston's ACS 2020-2024 median household income was <b>{money(bos.get('median_hh_income'))}</b>, median home value <b>{money(bos.get('median_home_value'))}</b> (SRC-625-03).",
        f"Boston poverty was <b>{bos.get('poverty_pct')}%</b> and bachelor's-or-higher <b>{bos.get('bachelors_pct')}%</b> (SRC-625-03).",
        f"The nearest ACS socioeconomic peer for Boston is <b>{short_place(peers.get('name'))}</b> (derived, SRC-625-03).",
    ]
    kpis = [
        kpi("Boston median income", money(bos.get("median_hh_income")),
            f"ACS 2020-2024 5-year. Home value {money(bos.get('median_home_value'))} (SRC-625-03).",
            "The socioeconomic print, not the population stock.",
            src_name(ledger, "SRC-625-03")),
        kpi("Boston poverty / bachelor's", f"{bos.get('poverty_pct')}% / {bos.get('bachelors_pct')}%",
            f"Median age {bos.get('median_age')} (SRC-625-03).",
            "The two rates that sit next to income.",
            src_name(ledger, "SRC-625-03")),
        kpi("Boston ACS peer", short_place(peers.get("name")) or "",
            f"Income {money(peers.get('median_hh_income'))}; bachelor's {peers.get('bachelors_pct')}% (derived, SRC-625-03).",
            "Z-scored income, home value, and bachelor's share. Not the old Pioneer workbook.",
            src_name(ledger, "SRC-625-03")),
    ]
    return take, kpis, f"Boston income {money(bos.get('median_hh_income'))}", "SRC-625-03"


def voice_dl26(ledger):
    latest = ledger.get("latest") or {}
    hi = latest.get("highest") or {}
    lo = latest.get("lowest") or {}
    ppe = sec(ledger, "district_ppe_fy2025")
    acs = sec(ledger, "acs_rankings_2024")
    inc = (acs.get("income") or acs.get("median_hh_income") or {})
    top = (inc.get("highest") or {})
    take = [
        f"From 2020 to 2025 the largest population gain was <b>{short_place(hi.get('name'))}</b> at <b>{signed(hi.get('v'))}</b> (derived, SRC-626-01).",
        f"The largest loss was <b>{short_place(lo.get('name'))}</b> at <b>{minus(lo.get('v'))}</b> (derived, SRC-626-01).",
        f"<b>{(ppe.get('highest') or {}).get('name') or 'Truro'}</b> had the highest DESE FY 2025 expenditures per pupil"
        + (f" at <b>{money((ppe.get('highest') or {}).get('v'))}</b>" if (ppe.get("highest") or {}).get("v") else "")
        + " (SRC-626-02).",
    ]
    kpis = [
        kpi("Largest gain, 2020-25", signed(hi.get("v")),
            f"{short_place(hi.get('name'))} (derived, SRC-626-01).",
            "Who grew, not the 2025 stock.",
            src_name(ledger, "SRC-626-01")),
        kpi("Largest loss, 2020-25", minus(lo.get("v")),
            f"{short_place(lo.get('name'))} (derived, SRC-626-01).",
            "Who shrank on the same vintage file.",
            src_name(ledger, "SRC-626-01")),
        kpi("Highest district PPE, FY 2025", money((ppe.get("highest") or {}).get("v")) if (ppe.get("highest") or {}).get("v") else ((ppe.get("highest") or {}).get("name") or ""),
            f"{(ppe.get('highest') or {}).get('name')} (SRC-626-02).",
            "School spending at the top of the district file.",
            src_name(ledger, "SRC-626-02")),
    ]
    return take, kpis, f"{short_place(hi.get('name'))} {signed(hi.get('v'))} from 2020 to 2025", "SRC-626-01"


def voice_dl27(ledger):
    latest = ledger.get("latest") or {}
    hi = latest.get("highest") or {}
    bud = sec(ledger, "boston_operating_budget_fy26")
    bhi = bud.get("highest") or {}
    take = [
        f"<b>{hi.get('name')}</b> was the largest payroll department at <b>{money(hi.get('v'))}</b> in calendar 2025 (SRC-627-01).",
        f"City earnings totaled <b>{money(latest.get('total'))}</b> across <b>{commify(latest.get('employees'))}</b> employees (SRC-627-01).",
        f"The FY26 adopted operating appropriation was <b>{money(bud.get('fy26_appropriation') or bud.get('total') or bud.get('v'))}</b>; <b>{bhi.get('name')}</b> was the largest department at <b>{money(bhi.get('v'))}</b> (SRC-627-02).",
    ]
    kpis = [
        kpi("Largest payroll department", money(hi.get("v")),
            f"{hi.get('name')}, calendar 2025 (SRC-627-01).",
            "Which department takes the largest earnings share.",
            src_name(ledger, "SRC-627-01")),
        kpi("City payroll, 2025", money(latest.get("total")),
            f"{commify(latest.get('employees'))} employees (SRC-627-01).",
            "The payroll the department ranking adds up to.",
            src_name(ledger, "SRC-627-01")),
        kpi("FY26 adopted budget", money(bud.get("fy26_appropriation") or bud.get("total") or bud.get("v")),
            f"{bhi.get('name')} was the largest department at {money(bhi.get('v'))} (SRC-627-02).",
            "The appropriation next to the earnings file.",
            src_name(ledger, "SRC-627-02")),
    ]
    return take, kpis, f"{hi.get('name')} {money(hi.get('v'))}", "SRC-627-01"


def voice_dl28(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    qtax = sec(ledger, "qtax_type_shares_2026q1")
    inc = qtax.get("individual_income") or {}
    stc = sec(ledger, "stc_ma_2023", "total")
    sma = ma_of(stc) or (stc.get("ma") if isinstance(stc.get("ma"), dict) else {})
    take = [
        f"Individual income taxes were <b>{inc.get('ma_share_pct')}%</b> of Massachusetts 2026 Q1 collections ({money(inc.get('ma'))}, SRC-628-01).",
        f"Statewide collections were <b>{money(ma.get('v'))}</b>, {ma.get('yoy_pct'):+.1f}% from 2025 Q1 (SRC-628-01)." if ma.get("yoy_pct") is not None else
        f"Statewide collections were <b>{money(ma.get('v'))}</b> in 2026 Q1 (SRC-628-01).",
        f"On the annual Census STC file, Massachusetts collected <b>{money(sma.get('v'))}</b> in FY 2023, {rank_txt(sma)} (derived, SRC-628-02).",
    ]
    kpis = [
        kpi("Individual income share, 2026 Q1", f"{inc.get('ma_share_pct')}%",
            f"{money(inc.get('ma'))}. U.S. share {inc.get('us_share_pct')}% (SRC-628-01).",
            "The type-of-tax finding, not the quarterly total alone.",
            src_name(ledger, "SRC-628-01")),
        kpi("Massachusetts taxes, 2026 Q1", money(ma.get("v")),
            f"{ma.get('yoy_pct'):+.1f}% from 2025 Q1 (SRC-628-01)." if ma.get("yoy_pct") is not None else "Census QTAX table 3 (SRC-628-01).",
            "The Commonwealth's quarterly take.",
            src_name(ledger, "SRC-628-01")),
        kpi("Annual collections, FY 2023", money(sma.get("v")),
            f"{rank_txt(sma).capitalize()} (derived, SRC-628-02).",
            "The annual file next to the quarterly split.",
            src_name(ledger, "SRC-628-02")),
    ]
    return take, kpis, f"income tax {inc.get('ma_share_pct')}% of 2026 Q1", "SRC-628-01"


def voice_dl29(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    fte = sec(ledger, "aspep_fte_2023")
    fma = ma_of(fte)
    stc = sec(ledger, "stc_2023", "total")
    sma = ma_of(stc) or (stc.get("ma") if isinstance(stc.get("ma"), dict) else {})
    share = sec(ledger, "stc_2023", "income_share")
    shma = ma_of(share)
    take = [
        f"Massachusetts collected <b>{money(ma.get('v'))}</b> in 2026 Q1 state taxes, {rank_txt(ma)} (derived, SRC-629-01).",
        f"State government FTE employment was <b>{commify(fma.get('v'))}</b> in 2023, {rank_txt(fma)} (derived, SRC-629-03).",
        f"Individual income taxes were <b>{shma.get('v')}%</b> of FY 2023 collections, {rank_txt(shma)} (derived, SRC-629-04)." if shma.get("v") is not None else
        f"FY 2023 annual collections were <b>{money(sma.get('v'))}</b>, {rank_txt(sma)} (derived, SRC-629-04).",
    ]
    kpis = [
        kpi("Massachusetts taxes, 2026 Q1", money(ma.get("v")),
            f"{rank_txt(ma).capitalize()}" + (f". {ma.get('yoy_pct'):+.1f}% from 2025 Q1" if ma.get("yoy_pct") is not None else "") + " (derived, SRC-629-01).",
            "The state's rank among the 50, not the U.S. total.",
            src_name(ledger, "SRC-629-01")),
        kpi("State FTE employment, 2023", commify(fma.get("v")),
            f"{rank_txt(fma).capitalize()} (derived, SRC-629-03).",
            "How large the state workforce is.",
            src_name(ledger, "SRC-629-03")),
        kpi("Income-tax share, FY 2023", f"{shma.get('v')}%" if shma.get("v") is not None else money(sma.get("v")),
            f"{rank_txt(shma or sma).capitalize()} (derived, SRC-629-04).",
            "How income-dependent the annual mix is.",
            src_name(ledger, "SRC-629-04")),
    ]
    return take, kpis, f"{money(ma.get('v'))} in 2026 Q1, {rank_txt(ma)}", "SRC-629-01"


def voice_dl30(ledger):
    latest = ledger.get("latest") or {}
    hi = latest.get("highest") or {}
    quasi = sec(ledger, "quasi_payroll_2025")
    vend = sec(ledger, "vendor_extract_fy2025")
    take = [
        f"<b>{hi.get('name')}</b> was the largest Commonwealth payroll department at <b>{money(hi.get('v'))}</b> in calendar 2025 (SRC-630-01).",
        f"Commonwealth payroll totaled <b>{money(latest.get('total'))}</b> across <b>{commify(latest.get('employees'))}</b> employee rows (SRC-630-01).",
        f"Comptroller-recorded spending was <b>{money(latest.get('spending_fy2025') if not isinstance(latest.get('spending_fy2025'), dict) else latest['spending_fy2025'].get('v'))}</b> in fiscal 2025 (SRC-630-02).",
    ]
    spend = latest.get("spending_fy2025")
    spend_v = spend.get("v") if isinstance(spend, dict) else spend
    qhi = (quasi.get("highest") or {})
    kpis = [
        kpi("Largest department, 2025", money(hi.get("v")),
            f"{hi.get('name')} (SRC-630-01).",
            "Which department dominates the payroll file.",
            src_name(ledger, "SRC-630-01")),
        kpi("Commonwealth payroll, 2025", money(latest.get("total")),
            f"{commify(latest.get('employees'))} employee rows (SRC-630-01).",
            "The statewide earnings total.",
            src_name(ledger, "SRC-630-01")),
        kpi("Comptroller spending, FY 2025", money(spend_v),
            "All object classes, including payroll transfers (SRC-630-02).",
            "Spending next to payroll, not a vendor-only extract.",
            src_name(ledger, "SRC-630-02")),
    ]
    return take, kpis, f"{hi.get('name')} {money(hi.get('v'))}", "SRC-630-01"


def voice_dl31(ledger):
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    rate = sec(ledger, "bjs_depth_2023", "imprisonment_rate")
    adm = sec(ledger, "bjs_depth_2023", "admissions")
    youth = sec(ledger, "bjs_depth_2023", "youth") or sec(ledger, "bjs_depth_2023", "youth_in_adult")
    rma = ma_of(rate)
    ama = ma_of(adm)
    yma = ma_of(youth) if youth else {}
    yv = yma.get("v") if yma else youth.get("ma") if isinstance(youth.get("ma"), (int, float)) else None
    take = [
        f"The Massachusetts imprisonment rate was <b>{num(rma.get('v'), 0) if rma.get('v') is not None else num(rma.get('v'))}</b> per 100,000 residents at year-end 2023, {rank_txt(rma)} (derived, SRC-631-03).",
        f"Sentenced admissions were <b>{commify(ama.get('v'))}</b> (SRC-631-03).",
        f"Prisoners age 17 or younger in adult prisons numbered <b>{commify(yv) if yv is not None else '0'}</b> (SRC-631-03).",
    ]
    kpis = [
        kpi("Imprisonment rate, 2023", str(int(rma.get("v")) if rma.get("v") is not None else ""),
            f"Per 100,000 residents, {rank_txt(rma)} (derived, SRC-631-03). U.S. rate {rate.get('us')}.",
            "The rate, not the raw prisoner count.",
            src_name(ledger, "SRC-631-03")),
        kpi("Sentenced admissions, 2023", commify(ama.get("v")),
            f"{rank_txt(ama).capitalize() if rank_txt(ama) else 'BJS table 8'} (SRC-631-03).",
            "How many people entered prison that year.",
            src_name(ledger, "SRC-631-03")),
        kpi("Youth in adult prisons", commify(yv) if yv is not None else "0",
            "Age 17 or younger, year-end 2023 (SRC-631-03). Not OJJDP juvenile custody.",
            "The youth-in-adult-prison cell the page can support.",
            src_name(ledger, "SRC-631-03")),
    ]
    return take, kpis, f"imprisonment rate {int(rma.get('v')) if rma.get('v') is not None else rma.get('v')}, {rank_txt(rma)}", "SRC-631-03"


VOICES = {
    "DL-06": voice_dl06,
    "DL-07": voice_dl07,
    "DL-08": voice_dl08,
    "DL-09": voice_dl09,
    "DL-10": voice_dl10,
    "DL-12": voice_dl12,
    "DL-13": voice_dl13,
    "DL-14": voice_dl14,
    "DL-15": voice_dl15,
    "DL-16": voice_dl16,
    "DL-17": voice_dl17,
    "DL-19": voice_dl19,
    "DL-20": voice_dl20,
    "DL-21": voice_dl21,
    "DL-22": voice_dl22,
    "DL-23": voice_dl23,
    "DL-24": voice_dl24,
    "DL-25": voice_dl25,
    "DL-26": voice_dl26,
    "DL-27": voice_dl27,
    "DL-28": voice_dl28,
    "DL-29": voice_dl29,
    "DL-30": voice_dl30,
    "DL-31": voice_dl31,
}


def fallback_voice(ledger):
    """Last resort: three sentences from latest.ma / latest.us. Never invent."""
    latest = ledger.get("latest") or {}
    ma = latest.get("ma") or {}
    us = latest.get("us") or {}
    hi = latest.get("highest") or {}
    take = []
    kpis = []
    if ma.get("v") is not None:
        take.append(f"Massachusetts was <b>{ma.get('v')}</b>" + (f", {rank_txt(ma)}" if rank_txt(ma) else "") + ".")
        kpis.append(kpi("Massachusetts", str(ma.get("v")), rank_txt(ma).capitalize() if rank_txt(ma) else "", "The Massachusetts finding on this file.", src_name(ledger, first_src(ledger))))
    if us.get("v") is not None:
        take.append(f"The United States figure was <b>{us.get('v')}</b>.")
        kpis.append(kpi("United States", str(us.get("v")), "", "The national comparison.", src_name(ledger, first_src(ledger))))
    if hi.get("name"):
        take.append(f"<b>{hi.get('name')}</b> was highest at <b>{hi.get('v')}</b>.")
        kpis.append(kpi("Highest", str(hi.get("v")), hi.get("name") or "", "The top of the ranking.", src_name(ledger, first_src(ledger))))
    ma_line = f"Massachusetts {ma.get('v')}" if ma.get("v") is not None else ""
    return take[:3], kpis[:3], ma_line, first_src(ledger)


# ---------------------------------------------------------------------------
# Find-box cards: towns, hospitals, tax types
# ---------------------------------------------------------------------------

def _fmt_row_value(v, fmt):
    if v is None:
        return ""
    if fmt == "usd":
        return money(v)
    if fmt == "percent":
        return f"{v:.1f}%" if isinstance(v, float) else f"{v}%"
    if fmt == "stars":
        return f"{int(v)} star" if v == 1 else f"{int(v)} stars"
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.2f}" if abs(v) < 10 else f"{v:,.1f}"
    return commify(v)


def _chia_lookup(chia):
    out = {}
    for rec in chia.get("top_eight") or []:
        if rec.get("name"):
            out[norm_key(rec["name"])] = rec
    for rec in (chia.get("highest"), chia.get("lowest"), chia.get("childrens")):
        if rec and rec.get("name"):
            out[norm_key(rec["name"])] = rec
    extra = dict(chia.get("by_name") or {})
    extra.update((load_lookups().get("chia_srp") or {}))
    for name, rec in extra.items():
        if isinstance(rec, dict):
            out[norm_key(name)] = {"name": name, **rec}
        elif rec is not None:
            out[norm_key(name)] = {"name": name, "v": rec}
    return out


def _acs_lookup(acs):
    out = {}
    bos = acs.get("boston") or {}
    if bos.get("name"):
        out[norm_key(bos["name"])] = bos
    extra = dict(acs.get("by_name") or {})
    extra.update((load_lookups().get("acs_towns") or {}))
    for name, rec in extra.items():
        if isinstance(rec, dict):
            out[norm_key(name)] = {"name": name, **rec}
    for block in (acs.get("income"), acs.get("home_value"), acs.get("poverty"), acs.get("bachelors")):
        if not isinstance(block, dict):
            continue
        for rec in [block.get("highest"), block.get("lowest"), block.get("boston")] + list(block.get("top_eight") or []):
            if rec and rec.get("name") and norm_key(rec["name"]) not in out:
                out[norm_key(rec["name"])] = {"name": rec["name"]}
    for name, peers in (acs.get("socioeconomic_peers") or {}).items():
        out.setdefault(norm_key(name), {"name": name})
        for p in peers or []:
            if p.get("name"):
                out.setdefault(norm_key(p["name"]), {"name": p["name"], **{k: p[k] for k in p if k != "name"}})
    return out


def find_bundle(app, ledger):
    """Card extras keyed for unique find-box / ?q= matches."""
    tid = app["id"]
    kind = None
    if tid in ("DL-25", "DL-26"):
        kind = "town"
    elif tid == "DL-10":
        kind = "hospital"
    elif tid == "DL-28":
        kind = "tax_type"
    else:
        kind = "row"
    cards = {}
    fmt = "number"
    unit = (ledger.get("unit") or "").lower()
    if "dollar" in unit:
        fmt = "usd"
    elif "percent" in unit:
        fmt = "percent"
    elif "star" in unit:
        fmt = "stars"
    chia = _chia_lookup(sec(ledger, "chia_srp_2023")) if tid == "DL-10" else {}
    acs = _acs_lookup(sec(ledger, "acs_towns_2024") or sec(ledger, "acs_rankings_2024")) if tid in ("DL-25", "DL-26") else {}
    qtax_types = {}
    if tid == "DL-28":
        for rec in sec(ledger, "qtax_type_shares_2026q1").get("types") or []:
            if rec.get("name"):
                qtax_types[norm_key(rec["name"])] = rec
        inc = sec(ledger, "qtax_type_shares_2026q1", "individual_income")
        if inc.get("name"):
            qtax_types[norm_key(inc["name"])] = inc
        tot = sec(ledger, "qtax_type_shares_2026q1", "total")
        if tot.get("name"):
            qtax_types[norm_key(tot["name"])] = tot
        sales = sec(ledger, "qtax_type_shares_2026q1", "general_sales")
        if sales.get("name"):
            qtax_types[norm_key(sales["name"])] = sales

    for r in ledger.get("rows") or []:
        name = r.get("name") or ""
        if not name:
            continue
        facts = []
        extras = {}
        if kind == "hospital":
            if r.get("city"):
                facts.append(f"City: {str(r['city']).title()}")
            if r.get("type"):
                facts.append(r["type"])
            if r.get("ownership"):
                facts.append(r["ownership"])
            ch = chia.get(norm_key(name))
            if not ch:
                for k, rec in chia.items():
                    if k and (k in norm_key(name) or norm_key(name) in k):
                        ch = rec
                        break
            if ch and ch.get("v") is not None:
                facts.append(f"CHIA commercial S-RP {ch['v']} (CY 2023, SRC-610-03)")
                extras["srp"] = ch["v"]
        elif kind == "town":
            ac = acs.get(norm_key(name))
            if ac:
                if acs_ok(ac.get("median_hh_income")):
                    facts.append(f"Median household income {money(ac['median_hh_income'])} (ACS 2020-2024, SRC-625-03)")
                if acs_ok(ac.get("median_home_value")):
                    facts.append(f"Median home value {money(ac['median_home_value'])}")
                if acs_ok(ac.get("poverty_pct")):
                    facts.append(f"Poverty {ac['poverty_pct']}%")
                if acs_ok(ac.get("bachelors_pct")):
                    facts.append(f"Bachelor's or higher {ac['bachelors_pct']}%")
                if acs_ok(ac.get("median_age")):
                    facts.append(f"Median age {ac['median_age']}")
            if r.get("pop2025") is not None:
                facts.append(f"July 1, 2025 population {commify(r['pop2025'])}")
            if r.get("pop2020") is not None:
                facts.append(f"2020 estimate {commify(r['pop2020'])}")
        elif kind == "tax_type":
            qt = qtax_types.get(norm_key(name))
            if qt:
                if qt.get("ma_share_pct") is not None:
                    facts.append(f"{qt['ma_share_pct']}% of Massachusetts 2026 Q1 collections")
                if qt.get("us_share_pct") is not None:
                    facts.append(f"U.S. share {qt['us_share_pct']}%")
                if qt.get("yoy_pct") is not None:
                    facts.append(f"{qt['yoy_pct']:+.1f}% from 2025 Q1")
        cards[norm_key(name)] = {
            "name": name,
            "value": _fmt_row_value(r.get("v"), fmt),
            "rank": r.get("rank"),
            "n": r.get("n"),
            "yoy": r.get("yoy_pct"),
            "facts": facts,
            "kind": kind,
            "aliases": [norm_key(name), (name or "").lower()],
        }
    return {"kind": kind, "cards": cards, "metric": ledger.get("metric_label") or "Value"}


def voice_for(app, ledger):
    """Return takeaways, finding KPIs, cite, catalog line, and find extras."""
    tid = app["id"]
    slug = app.get("slug") or ledger.get("slug") or ""
    title = app.get("title") or ledger.get("title") or tid
    live = ledger.get("status") == "live"
    as_of = ledger.get("data_month_label") or "pending"
    page = ledger.get("page") or {}
    if tid in SKIP_VOICE:
        return None
    if not live:
        return {
            "takeaways": [],
            "kpis": [],
            "cite": cite_line(title, slug, "", "", page.get("version"), page.get("revised")).replace(
                "data through . ", ""
            ).replace(
                f"{SITE}/{slug}/",
                f"{SITE}/{slug}/. This page is in build; the register is the work plan",
            ),
            "ma": "",
            "find": {"kind": None, "cards": {}, "metric": ""},
            "src_id": "",
        }
    fn = VOICES.get(tid) or fallback_voice
    take, kpis, ma_line, src_id = fn(ledger)
    take = [t for t in take if t][:3]
    kpis = [k for k in kpis if k.get("value") not in (None, "", "see register")][:3]
    return {
        "takeaways": take,
        "kpis": kpis,
        "cite": cite_line(title, slug, as_of, src_id, page.get("version"), page.get("revised")),
        "ma": ma_line,
        "find": find_bundle(app, ledger),
        "src_id": src_id,
    }


def flagship_voice(tid, ledger):
    """Takeaways, finding KPIs, cite, and catalog line for DL-03/04/05."""
    page = ledger.get("page") or {}
    if tid == "DL-04":
        latest = ledger.get("latest") or {}
        year = latest.get("year") or ledger.get("data_year")
        ma = latest.get("ma") or {}
        us = latest.get("us") or {}
        hi = latest.get("highest") or {}
        lo = latest.get("lowest") or {}
        ma_p = ma.get("price_cents")
        us_p = us.get("price_cents")
        prem = None
        if ma_p and us_p:
            prem = round((ma_p / us_p - 1) * 100, 0)
        take = [
            f"Massachusetts paid <b>{ma_p:.2f} cents</b> per kilowatthour in {year}, {rank_txt(ma)} (derived, SRC-401).",
            f"That is <b>{int(prem)} percent</b> above the U.S. all-sector average of {us_p:.2f} cents (derived, SRC-401)." if prem is not None else
            f"The U.S. all-sector average was <b>{us_p:.2f} cents</b> (SRC-401).",
            f"The Massachusetts price rose <b>{ma.get('yoy_pct'):.1f} percent</b> from {year - 1} (SRC-401)." if ma.get("yoy_pct") is not None else
            f"{hi.get('name')} was highest at {hi.get('price_cents'):.2f} cents (SRC-401).",
        ]
        kpis_html_data = [
            kpi(f"Massachusetts, {year}", f"{ma_p:.2f}\u00a2",
                f"{rank_txt(ma).capitalize()} states and D.C. (derived, SRC-401)."
                + (f" {ma.get('yoy_pct'):+.1f} percent from {year - 1}." if ma.get("yoy_pct") is not None else ""),
                "The state's price rank, not the national average.",
                "EIA Form EIA-861 (SRC-401)"),
            kpi("Above the U.S. average", f"{int(prem)}%" if prem is not None else "",
                f"U.S. all-sector average {us_p:.2f} cents, EIA U.S. Total row (derived, SRC-401).",
                "How far Massachusetts sits above the national price.",
                "EIA Form EIA-861 (SRC-401)"),
            kpi("Highest / lowest", f"{hi.get('st')} {hi.get('price_cents'):.2f}",
                f"{hi.get('name')} is highest; {lo.get('name')} is lowest at {lo.get('price_cents'):.2f} cents (SRC-401).",
                "The spread across the 51 jurisdictions.",
                "EIA Form EIA-861 (SRC-401)"),
        ]
        return {
            "takeaways": take,
            "kpis": kpis_html_data,
            "cite": cite_line("Retail Electricity Prices", "electricity", f"Dec 31, {year}", "SRC-401", page.get("version", "1.0"), page.get("revised")),
            "ma": f"{ma_p:.2f}\u00a2 / kWh, {rank_txt(ma)}",
            "src_id": "SRC-401",
            "lead": (
                f"The United States all-sector average was <b>{us_p:.2f} cents</b> per kilowatthour "
                f"in {year}, {'up' if (us.get('yoy_pct') or 0) > 0 else 'down'} {abs(us.get('yoy_pct') or 0):.1f} percent "
                f"from {year - 1} (SRC-401). Massachusetts paid <b>{ma_p:.2f} cents</b>, "
                f"{rank_txt(ma)} (derived, SRC-401). {hi.get('name')} was highest at "
                f"{hi.get('price_cents'):.2f} cents and {lo.get('name')} lowest at "
                f"{lo.get('price_cents'):.2f} cents (SRC-401)."
            ),
        }
    if tid == "DL-05":
        latest = ledger.get("latest") or {}
        derived = ledger.get("derived") or {}
        st = latest.get("state") or {}
        mt = latest.get("mtrs") or {}
        n = derived.get("n_boards") or latest.get("n_boards")
        w = derived.get("weighted_funded_pct") or latest.get("weighted_funded_pct")
        ret = (latest.get("retirees") or {})
        take = [
            f"Mass Teachers (MTRS) was <b>{mt.get('funded_pct')} percent</b> funded on its January 1, {mt.get('valuation_year')} valuation, rank {mt.get('rank')} of {n} (SRC-501).",
            f"The State Retirement Board was <b>{st.get('funded_pct')} percent</b> funded, rank {st.get('rank')} of {n} (SRC-501).",
            f"Across {n} boards the dollar-weighted funded ratio was <b>{w} percent</b> (derived, SRC-501).",
        ]
        kpis = [
            kpi("Mass Teachers (MTRS)", f"{mt.get('funded_pct')}%",
                f"January 1, {mt.get('valuation_year')} valuation, rank {mt.get('rank')} of {n} (SRC-501). Unfunded liability {money(mt.get('ual'))}.",
                "Teachers are the furthest from full funding among the large systems.",
                "PERAC board actuarial valuation (SRC-501)"),
            kpi("State Retirement Board", f"{st.get('funded_pct')}%",
                f"January 1, {st.get('valuation_year')} valuation, rank {st.get('rank')} of {n} (SRC-501). Unfunded liability {money(st.get('ual'))}.",
                "The Commonwealth's own employee system.",
                "PERAC board actuarial valuation (SRC-501)"),
            kpi("Dollar-weighted funded ratio", f"{w}%",
                f"Across {n} boards (derived, SRC-501). {derived.get('n_below_60') or latest.get('n_below_60')} boards below 60 percent.",
                "The system-wide funded picture, not one board.",
                "PERAC board actuarial valuations (SRC-501)"),
        ]
        return {
            "takeaways": take,
            "kpis": kpis,
            "cite": cite_line("Massachusetts Public Pensions", "pensions", f"board valuations through January 1, {ledger.get('board_valuation_through')}", "SRC-501", page.get("version", "1.1"), page.get("revised")),
            "ma": f"Teachers {mt.get('funded_pct')}% funded",
            "src_id": "SRC-501",
            "lead": (
                f"The State Retirement Board was <b>{st.get('funded_pct')} percent</b> funded on its "
                f"January 1, {st.get('valuation_year')} valuation (SRC-501). Mass Teachers (MTRS) was "
                f"<b>{mt.get('funded_pct')} percent</b> funded (SRC-501). Across {n} boards the "
                f"dollar-weighted funded ratio was {w} percent (derived, SRC-501). State and Teacher "
                f"retirees were paid <b>{money(ret.get('annual_amount'))}</b> in calendar {ret.get('year')} (SRC-503)."
                if ret.get("annual_amount") else
                f"The State Retirement Board was <b>{st.get('funded_pct')} percent</b> funded on its "
                f"January 1, {st.get('valuation_year')} valuation (SRC-501). Mass Teachers (MTRS) was "
                f"<b>{mt.get('funded_pct')} percent</b> funded (SRC-501). Across {n} boards the "
                f"dollar-weighted funded ratio was {w} percent (derived, SRC-501)."
            ),
        }
    if tid == "DL-03":
        take = [
            "The T carried <b>26,288,869</b> unlinked passenger trips in June 2026, <b>88.1 percent</b> of the same month in 2019 (derived, SRC-301).",
            "Ferry stood at <b>118.9 percent</b> of June 2019 ridership and commuter rail at <b>107.7 percent</b>; the subway sat at <b>79.1 percent</b> (derived, SRC-301).",
            "June 2026 ridership was <b>18.0 percent</b> above June 2025 (derived, SRC-301).",
        ]
        return {
            "takeaways": take,
            "kpis": [],
            "cite": cite_line(
                "Transportation and MBTA",
                "mbta",
                "June 2026",
                "SRC-301",
                page.get("version") or "1.0",
                page.get("revised"),
            ),
            "ma": "88.1% of June 2019 ridership",
            "src_id": "SRC-301",
            "lead": "",
        }
    return None


def apply_catalog_ma(catalog):
    """Write a Massachusetts-in-one-number line onto live catalog rows.

    Leaves DL-01 (tax atlas) and DL-02 (Florida) untouched. Stubs stay blank.
    """
    apps = {a["id"]: a for a in load_apps()}
    by_id = {row.get("id"): row for row in catalog if isinstance(row, dict)}
    for tid, app in apps.items():
        row = by_id.get(tid)
        if not row or tid in SKIP_VOICE:
            continue
        path = ledger_path(tid)
        if not path.exists():
            continue
        ledger = json.loads(path.read_text(encoding="utf-8"))
        voice = voice_for(app, ledger)
        if voice and voice.get("ma") and ledger.get("status") == "live":
            row["ma"] = voice["ma"]
        else:
            row.pop("ma", None)
    for tid, loader in (
        ("DL-03", "netlify/functions/dl03-answers.json"),
        ("DL-04", "netlify/functions/dl04-answers.json"),
        ("DL-05", "netlify/functions/dl05-answers.json"),
    ):
        row = by_id.get(tid)
        if not row:
            continue
        led = json.loads((ROOT / loader).read_text(encoding="utf-8"))
        voice = flagship_voice(tid, led)
        if voice and voice.get("ma"):
            row["ma"] = voice["ma"]
    return catalog
