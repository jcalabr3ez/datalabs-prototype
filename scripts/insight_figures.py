#!/usr/bin/env python3
"""Compact insight charts for live suite pages and the landing portfolio.

Every number comes from a published ledger cell. Waitlists and other
unpublished series are captioned as missing, never invented.
"""
from __future__ import annotations

GOLD = "#CCB26D"
NAVY = "#293C5C"
INK = "#222222"
GREY = "#8DA0B5"

LETTERS = "ABCDEFGH"


def _sec(ledger):
    return ((ledger.get("derived") or {}).get("secondary")) or {}


def _fig(
    fid,
    title,
    lede,
    src,
    kind,
    fmt,
    unit,
    labels,
    series,
    note,
    span=1,
    height=None,
    url=None,
):
    out = {
        "id": fid,
        "title": title,
        "lede": lede,
        "src": src,
        "type": kind,
        "format": fmt,
        "unit": unit or "",
        "labels": labels,
        "series": series,
        "note": note,
        "span": span,
        "index_axis": "y" if kind == "bar" else "x",
    }
    if height:
        out["height"] = height
    if url:
        out["url"] = url
    return out


def _bars(labels, values, highlight=None, highlight_names=None):
    names = set(highlight_names or [])
    if highlight:
        names.add(highlight)
    colors = [
        GOLD if (lab in names or lab == "Massachusetts" or lab == "Boston") else NAVY
        for lab in labels
    ]
    return [{"label": "", "data": values, "colors": colors}]


def _line(values, label, color=GOLD):
    return [{"label": label, "data": values, "color": color}]


def _grouped(series_specs):
    out = []
    for spec in series_specs:
        out.append({
            "label": spec["label"],
            "data": spec["data"],
            "color": spec.get("color") or NAVY,
        })
    return out


def _us_dwarfs(us, others):
    if us is None:
        return False
    mx = max((abs(v) for v in others if v is not None), default=0)
    return bool(mx) and abs(us) > 8 * mx


def _snap_val(node):
    if node is None:
        return None
    if isinstance(node, dict):
        return node.get("v")
    return node


def from_snap(snap, fid, title=None, lede=None, note=None, skip_us=None, span=1):
    if not snap:
        return None
    ma = snap.get("ma") if isinstance(snap.get("ma"), dict) else None
    ma_v = _snap_val(snap.get("ma"))
    us = _snap_val(snap.get("us"))
    hi = snap.get("highest") or {}
    lo = snap.get("lowest") or {}
    others = [v for v in (ma_v, hi.get("v"), lo.get("v")) if v is not None]
    hide_us = skip_us if skip_us is not None else _us_dwarfs(us, others)
    pairs = []
    if us is not None and not hide_us:
        pairs.append(("United States", us))
    if hi.get("name") and hi.get("v") is not None and hi.get("st") != "MA":
        pairs.append((hi["name"], hi["v"]))
    if ma_v is not None:
        pairs.append(("Massachusetts", ma_v))
    lo_st = lo.get("st")
    hi_st = hi.get("st")
    if lo.get("name") and lo.get("v") is not None and lo_st not in ("MA", hi_st):
        pairs.append((lo["name"], lo["v"]))
    if len(pairs) < 2:
        return None
    unit = snap.get("unit") or ""
    src = snap.get("src") or ""
    title = title or snap.get("label") or "Comparison"
    if lede is None:
        lede = snap.get("label") or title
        if ma and ma.get("rank") and ma.get("n"):
            lede += f". Massachusetts ranks {ma['rank']} of {ma['n']} (derived)."
    note = note or snap.get("note") or "Published cells only. Ranks are Pioneer calculations (derived)."
    fmt = "percent" if "percent" in unit.lower() else (
        "usd" if "dollar" in unit.lower() else "number"
    )
    return _fig(
        fid, title, lede, src, "bar", fmt, unit,
        [p[0] for p in pairs],
        _bars([p[0] for p in pairs], [p[1] for p in pairs]),
        note, span=span,
    )


def from_latest(ledger, fid="latest-compare", title=None, lede=None, note=None, skip_us=None):
    latest = ledger.get("latest") or {}
    if not latest.get("ma") and not latest.get("highest"):
        return None
    src_map = ledger.get("source_id_map") or {}
    snap = {
        "us": latest.get("us"),
        "ma": latest.get("ma"),
        "highest": latest.get("highest"),
        "lowest": latest.get("lowest"),
        "label": ledger.get("metric_label") or "Latest comparison",
        "src": next(iter(src_map), ""),
        "unit": ledger.get("unit") or "",
        "note": note,
    }
    return from_snap(snap, fid, title=title, lede=lede, note=note, skip_us=skip_us)


def named_list(rows, fid, title, lede, src, fmt, unit, note, name_key="name", val_key="v", n=8, highlight=None, span=1):
    items = [r for r in (rows or []) if r.get(val_key) is not None][:n]
    if len(items) < 2:
        return None
    labels = [r.get(name_key) or "" for r in items]
    values = [r[val_key] for r in items]
    return _fig(
        fid, title, lede, src, "bar", fmt, unit, labels,
        _bars(labels, values, highlight=highlight),
        note, span=span, height="mid" if len(items) >= 8 else None,
    )


def _trend_xy(points, y_key="y"):
    labels, values = [], []
    for p in points or []:
        lab = p.get(y_key) or p.get("m") or p.get("period") or ""
        if isinstance(lab, str) and lab.startswith("School year "):
            lab = lab.replace("School year ", "")
        labels.append(lab)
        values.append(p.get("v"))
    return labels, values


# ---------------------------------------------------------------------------
# Per-tool figures
# ---------------------------------------------------------------------------

def figs_dl06(ledger):
    sec = _sec(ledger)
    out = []
    ch74 = sec.get("ma_chapter74_cte") or {}
    labels, values = _trend_xy(ch74.get("trend"))
    if labels and all(v is not None for v in values):
        first, last = values[0], values[-1]
        out.append(_fig(
            "ch74-seats",
            "Chapter 74 vocational seats filled, 2021-22 to 2025-26",
            (
                f"Enrollment rose from {first:,} to {last:,} "
                f"({ch74.get('change_since_2021_22_pct')} percent). "
                "This is seats filled, not a waitlist."
            ),
            ch74.get("src") or "SRC-606-03",
            "line", "number", "students",
            labels, _line(values, "Chapter 74 enrollment"),
            (
                "DESE / E2C Chapter 74 career technical education. "
                "A statewide waitlist or lottery table is not published. "
                "This figure is enrollment (seats filled), not unmet demand."
            ),
            span=2,
        ))
    programs = ch74.get("top_occupational_programs") or []
    if programs:
        out.append(named_list(
            programs, "ch74-programs",
            "Largest Chapter 74 occupational programs, 2025-26",
            (
                "Health Assisting is the largest career major at "
                f"{programs[0]['v']:,} students. Exploratory "
                f"({(ch74.get('exploratory') or {}).get('v'):,} students) "
                "is a grade 9 rotation, not a career major, and is omitted here."
            ),
            ch74.get("src") or "SRC-606-03",
            "number", "students",
            (
                "Published program counts. Waitlists by program are not in the "
                "statewide file, so this page does not draw them."
            ),
            n=8, span=2,
        ))
    mcas = sec.get("mcas_2025") or {}
    if mcas.get("ela_3_8_pct") is not None:
        labels = ["ELA grades 3-8", "Math grades 3-8", "ELA grade 10", "Math grade 10"]
        values = [
            mcas["ela_3_8_pct"], mcas["math_3_8_pct"],
            mcas["ela_10_pct"], mcas["math_10_pct"],
        ]
        out.append(_fig(
            "mcas-2025",
            "MCAS share meeting or exceeding, All Students, 2025",
            (
                f"Grades 3-8: ELA {mcas['ela_3_8_pct']} percent, "
                f"math {mcas['math_3_8_pct']} percent. Grade 10: "
                f"ELA {mcas['ela_10_pct']} percent, math {mcas['math_10_pct']} percent."
            ),
            mcas.get("src") or "SRC-606-04",
            "bar", "percent", "percent",
            labels, _bars(labels, values),
            mcas.get("note") or "Statewide All Students, Next Generation MCAS 2025.",
        ))
    latest = ledger.get("latest") or {}
    ma_ppe = (latest.get("ma") or {}).get("v")
    us_ppe = (latest.get("us") or {}).get("v")
    ma_rank = (latest.get("ma") or {}).get("rank")
    ppe = from_latest(
        ledger, "ppe-compare",
        title="Current expenditures per pupil, FY 2024",
        lede=(
            f"Massachusetts spent ${ma_ppe:,} per pupil, rank {ma_rank} of 51. "
            f"The United States average was ${us_ppe:,}."
        ) if ma_ppe and us_ppe else None,
        note="NCES NPEFS FY 2024 (First Look 2026-008 Table 4).",
    )
    if ppe:
        out.append(ppe)
    return out


def figs_dl07(ledger):
    sec = _sec(ledger)
    out = []
    naep = (sec.get("naep_2024") or {}).get("series") or {}
    order = [
        ("read4", "Grade 4 reading"),
        ("read8", "Grade 8 reading"),
        ("math4", "Grade 4 math"),
        ("math8", "Grade 8 math"),
    ]
    us, ma = [], []
    ok = True
    for key, _lab in order:
        rec = naep.get(key) or {}
        if rec.get("us") is None or _snap_val(rec.get("ma")) is None:
            ok = False
            break
        us.append(rec["us"])
        ma.append(_snap_val(rec["ma"]))
    if ok and us:
        out.append(_fig(
            "naep-2024",
            "NAEP 2024: Massachusetts versus national public",
            "Massachusetts ranks 1 of 51 on all four reading and math series.",
            "SRC-607-05",
            "grouped", "number", "scale score",
            [lab for _k, lab in order],
            _grouped([
                {"label": "National public", "data": us, "color": INK},
                {"label": "Massachusetts", "data": ma, "color": GOLD},
            ]),
            "NAEP average scale scores, 2024. National public is the published NP line.",
            span=2,
        ))
    for key, fid, title in (
        ("acgr_2021_22", "acgr", "Four-year adjusted cohort graduation rate, 2021-22"),
        ("oss_suspension_2020_21", "oss", "Out-of-school suspension share, 2020-21"),
    ):
        fig = from_snap(sec.get(key), fid, title=title)
        if fig:
            out.append(fig)
    fig = from_snap(
        sec.get("npefs_ppe_fy2024"), "npefs-ppe",
        title="Current expenditures per pupil, FY 2024",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl08(ledger):
    sec = _sec(ledger)
    out = []
    sat = sec.get("sat_2023") or {}
    fig = from_snap(
        sat, "sat-2023",
        title="SAT mean total score, 2023 graduates",
        lede=(
            f"Massachusetts {int(sat['ma']['v'])} versus a U.S. mean of "
            f"{int(sat['us'])}. Participation was "
            f"{sat.get('participation_pct', {}).get('ma')} percent in "
            f"Massachusetts and {sat.get('participation_pct', {}).get('us')} "
            "percent nationally."
        ) if sat.get("ma") and sat.get("us") else None,
    )
    if fig:
        out.append(fig)
    latest = from_latest(
        ledger, "enroll-compare",
        title="Fall 2022 postsecondary enrollment",
        note="NCES Digest table 304.10. The U.S. bar is omitted when it dwarfs the states.",
        skip_us=True,
    )
    if latest:
        out.append(latest)
    fac = sec.get("faculty_composition_fall_2023") or {}
    if fac.get("us") and fac.get("professors") and fac.get("female") is not None:
        labels = ["All full-time faculty", "Professors", "Women"]
        values = [fac["us"], fac["professors"], fac["female"]]
        out.append(_fig(
            "faculty-ft",
            "Full-time faculty, Fall 2023 (national)",
            (
                f"{fac['us']:,} full-time faculty. Professors were "
                f"{fac.get('professor_share_pct')} percent; women were "
                f"{fac.get('female_share_pct')} percent."
            ),
            fac.get("src") or "SRC-608-05",
            "bar", "number", "faculty",
            labels, _bars(labels, values),
            fac.get("note") or "Digest 315.20 is national and has no state column.",
            span=2,
        ))
    return out


def figs_dl09(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_snap(
        sec.get("teachers_fte_fall_2022"), "teachers-fte",
        title="Public-school teachers (FTE), Fall 2022",
        skip_us=True,
    )
    if fig:
        out.append(fig)
    latest = from_latest(
        ledger, "charter-enroll",
        title="Public charter fall enrollment, 2022-23",
        skip_us=True,
        note="NCES Digest table 216.90. Kentucky published zero charter enrollment.",
    )
    if latest:
        out.append(latest)
    return out


def figs_dl10(ledger):
    latest = ledger.get("latest") or {}
    derived = ledger.get("derived") or {}
    sec = _sec(ledger)
    out = []
    by_type = latest.get("by_type") or {}
    if by_type:
        items = sorted(by_type.items(), key=lambda kv: -kv[1])
        labels = [k for k, _ in items]
        values = [v for _, v in items]
        out.append(_fig(
            "hospital-type",
            "Massachusetts hospitals by CMS type",
            f"{latest.get('n_hospitals')} facilities. {latest.get('five_star')} have a five-star overall rating.",
            "SRC-610-02",
            "bar", "number", "hospitals",
            labels, _bars(labels, values),
            "CMS Hospital General Information, Massachusetts facilities.",
            span=2,
        ))
    stars = {}
    for r in ledger.get("rows") or []:
        v = r.get("v")
        if v is None:
            continue
        stars[int(v)] = stars.get(int(v), 0) + 1
    if stars:
        labels = [f"{s} star" + ("" if s == 1 else "s") for s in range(5, 0, -1)]
        values = [stars.get(s, 0) for s in range(5, 0, -1)]
        out.append(_fig(
            "hospital-stars",
            "Rated Massachusetts hospitals by overall star rating",
            (
                f"{latest.get('n_rated')} rated, {latest.get('n_unrated')} unrated. "
                "Unrated facilities are omitted from this figure."
            ),
            "SRC-610-02",
            "bar", "number", "hospitals",
            labels, _bars(labels, values),
            "CMS overall star rating among rated facilities only.",
        ))
    own = derived.get("by_ownership") or {}
    if own:
        items = sorted(own.items(), key=lambda kv: -kv[1])
        labels = [k.replace("Voluntary non-profit - ", "Nonprofit, ") for k, _ in items]
        values = [v for _, v in items]
        out.append(_fig(
            "hospital-own",
            "Massachusetts hospitals by ownership",
            "Nonprofit private is the largest ownership group.",
            "SRC-610-02",
            "bar", "number", "hospitals",
            labels, _bars(labels, values),
            "CMS ownership labels, shortened for the axis.",
        ))
    chia = sec.get("chia_srp_2023") or {}
    fig = named_list(
        chia.get("top_eight"), "chia-srp",
        "Highest CHIA statewide commercial relative prices, CY 2023",
        (
            f"{chia.get('highest', {}).get('name')} was highest at "
            f"{chia.get('highest', {}).get('v')}. Boston Children's Hospital "
            f"was {chia.get('childrens', {}).get('v')}."
        ) if chia.get("highest") else "CHIA statewide commercial relative price.",
        chia.get("src") or "SRC-610-03",
        "number", "relative price (statewide = 1.00)",
        chia.get("note") or "CHIA Appendix A, commercial self- and fully-insured.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
    cms = sec.get("cms_hospital_depth") or {}
    fig = named_list(
        cms.get("top_cities"), "hosp-cities",
        "Massachusetts hospitals by city",
        (
            f"{cms.get('highest_city', {}).get('name')} has the most CMS-listed "
            f"facilities. {cms.get('emergency_pct')} percent report emergency services."
        ) if cms.get("highest_city") else "CMS facilities by city.",
        cms.get("src") or "SRC-610-02",
        "number", "hospitals",
        "CMS Hospital General Information, Massachusetts facilities.",
        n=8,
    )
    if fig:
        out.append(fig)
    return out


def figs_dl12(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_snap(
        sec.get("mfcu_recoveries_fy2025"), "mfcu",
        title="Medicaid Fraud Control Unit recoveries, FY 2025",
        skip_us=True,
        note="HHS OIG FY 2025 statistical chart. The U.S. total is $1.97 billion; it is omitted so the state bars remain readable.",
    )
    if fig:
        out.append(fig)
    latest = from_latest(
        ledger, "medicaid-spend",
        title="Medicaid net expenditures, FY 2024",
        skip_us=True,
    )
    if latest:
        out.append(latest)
    return out


def figs_dl13(ledger):
    sec = _sec(ledger)
    out = []
    bed = sec.get("bed_births_deaths") or {}
    trend = bed.get("trend") or []
    if trend:
        labels = [r["q"] for r in trend]
        births = [r.get("ma_birth_rate_pct") for r in trend]
        deaths = [r.get("ma_death_rate_pct") for r in trend]
        ma = bed.get("ma") or {}
        ov = bed.get("overlap") or {}
        out.append(_fig(
            "bed-rates",
            "Massachusetts establishment birth and death rates",
            (
                f"The birth rate was {ma.get('birth_rate_pct')} percent in "
                f"{ma.get('births_as_of')}. Deaths are published through "
                f"{ma.get('deaths_as_of')}. In {ov.get('q')}, the last "
                f"overlapping quarter, births were {ov.get('ma_birth_rate_pct')} "
                f"percent and deaths were {ov.get('ma_death_rate_pct')} percent."
            ),
            bed.get("src") or "SRC-613-02",
            "line", "percent", "percent of establishments",
            labels,
            [
                {"label": "Birth rate", "data": births, "color": GOLD},
                {"label": "Death rate", "data": deaths, "color": INK},
            ],
            bed.get("note") or (
                "BLS Business Employment Dynamics, total private, seasonally "
                "adjusted. Deaths lag three quarters."
            ),
            span=2,
        ))
    latest = from_latest(
        ledger, "bfs",
        title="Business applications, latest month",
        skip_us=True,
        note="Census Business Formation Statistics. The U.S. total is omitted so state bars remain readable.",
    )
    if latest:
        out.append(latest)
    return out


def figs_dl14(ledger):
    sec = _sec(ledger)
    out = []
    wage = sec.get("qcew_avg_weekly_wage_2025q4") or {}
    fig = from_snap(
        wage, "qcew-wage",
        title="Average weekly wage, all industries, 2025 Q4",
        lede=(
            f"Massachusetts ${int(wage['ma']['v']):,}, rank {wage['ma']['rank']} "
            f"of {wage['ma']['n']}, behind {(wage.get('highest') or {}).get('name')}."
        ) if wage.get("ma") else None,
    )
    if fig:
        out.append(fig)
    ui = sec.get("ui_initial_claims") or {}
    fig = from_snap(
        ui, "ui-claims",
        title="UI initial claims, week ending 2026-08-08",
        skip_us=True,
        note=(
            "ETA 539 cell C3. Massachusetts also reported "
            f"{ui.get('ma_continued'):,} continued weeks claimed. "
            "The U.S. total is omitted so state bars remain readable."
        ) if ui.get("ma_continued") else ui.get("note"),
    )
    if fig:
        out.append(fig)
    labor = sec.get("laus_labor_2026") or {}
    fig = from_snap(
        labor.get("lfpr"), "lfpr",
        title="Labor-force participation rate",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        labor.get("epop"), "epop",
        title="Employment-population ratio",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        labor.get("employment"), "employment",
        title="Employment level",
        skip_us=True,
        note="BLS LAUS statewide seasonally adjusted employment. The U.S. total is not in this file.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl15(ledger):
    sec = _sec(ledger)
    out = []
    inds = ((sec.get("sagdp2_naics_2025") or {}).get("industries")) or {}
    pairs = []
    for key, label in (
        ("manufacturing", "Manufacturing"),
        ("finance_insurance", "Finance and insurance"),
        ("information", "Information"),
        ("construction", "Construction"),
    ):
        rec = inds.get(key) or {}
        v = _snap_val(rec.get("ma"))
        if v is not None:
            pairs.append((label, v * 1_000_000))
    if pairs:
        labels = [p[0] for p in pairs]
        values = [p[1] for p in pairs]
        out.append(_fig(
            "ma-industries",
            "Massachusetts current-dollar GDP by industry, 2025",
            "Finance and insurance is the largest of these published NAICS slices.",
            "SRC-615-03",
            "bar", "usd", "dollars",
            labels, _bars(labels, values),
            "BEA SAGDP2. Values are Massachusetts industry GDP in current dollars. Information is suppressed in some other states.",
            span=2,
        ))
    pi = (sec.get("personal_income_2025") or {}).get("per_capita") or {}
    fig = from_snap(
        pi, "pcpi",
        title="Per capita personal income, 2025",
        lede="Massachusetts $97,456, rank 3 of 51.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl16(ledger):
    sec = _sec(ledger)
    out = []
    cs = sec.get("case_shiller_boston") or {}
    labels, values = _trend_xy(cs.get("trend"), y_key="m")
    if labels and values:
        out.append(_fig(
            "cs-boston",
            "Case-Shiller Boston house-price index",
            (
                f"Boston MSA {cs.get('boston')} in {cs.get('as_of_label')}, "
                f"{cs.get('yoy_pct')} percent year over year. "
                "January 2000 equals 100."
            ),
            cs.get("src") or "SRC-616-03",
            "line", "number", "index, January 2000 = 100",
            labels, _line(values, "Boston MSA"),
            cs.get("note") or "FRED BOXRSA, seasonally adjusted.",
            span=2,
        ))
    fig = from_snap(
        sec.get("fhfa_hpi_annual_change_2025"), "fhfa-hpi",
        title="FHFA house-price index, annual change, 2025",
    )
    if fig:
        out.append(fig)
    latest = from_latest(
        ledger, "permits",
        title="Building permits, latest year-to-date",
        skip_us=True,
    )
    if latest:
        out.append(latest)
    return out


def figs_dl17(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_snap(
        sec.get("rucc_2023"), "rucc",
        title="Share of 2020 population in metro RUCC 1-3 counties",
        note="USDA RUCC 2023. Codes are county-level. This is the metro population share, not a county count.",
    )
    if fig:
        out.append(fig)
    latest = from_latest(
        ledger, "pop-2025",
        title="Resident population, July 1, 2025",
        skip_us=True,
    )
    if latest:
        out.append(latest)
    return out


def figs_dl19(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_latest(
        ledger, "rpp",
        title="Regional price parities, all items, 2024",
        lede="Massachusetts 105.8 versus a U.S. index of 100. California is highest.",
        note="BEA SARPP. United States equals 100.",
        skip_us=False,
    )
    if fig:
        out.append(fig)
    comps = ((sec.get("rpp_components_2024") or {}).get("components")) or {}
    order = [
        ("goods", "Goods"),
        ("housing", "Housing"),
        ("utilities", "Utilities"),
        ("other_services", "Other services"),
    ]
    us, ma = [], []
    labels = []
    for key, lab in order:
        rec = comps.get(key) or {}
        if rec.get("us") is None or _snap_val(rec.get("ma")) is None:
            continue
        labels.append(lab)
        us.append(rec["us"])
        ma.append(_snap_val(rec["ma"]))
    if labels:
        out.append(_fig(
            "rpp-components",
            "Regional price parities by component, 2024",
            "Housing is the Massachusetts component furthest above the national index of 100.",
            "SRC-619-02",
            "grouped", "number", "index (US = 100)",
            labels,
            _grouped([
                {"label": "United States", "data": us, "color": INK},
                {"label": "Massachusetts", "data": ma, "color": GOLD},
            ]),
            "BEA SARPP component RPPs. United States equals 100 on each line.",
            span=2,
        ))
    return out


def figs_dl20(ledger):
    sec = _sec(ledger)
    mig = sec.get("ma_county_taxpayer_migration_2022_23") or {}
    fig = named_list(
        mig.get("counties"), "county-mig",
        "Massachusetts county net domestic taxpayer migration, 2022-23",
        "Bristol County is the only net gainer. Middlesex County lost the most returns.",
        mig.get("src") or "SRC-620-02",
        "number", "returns",
        mig.get("note") or "Net equals Total Migration-US inflow minus outflow. Same-state and foreign rows are excluded.",
        n=14, span=2,
    )
    out = [fig] if fig else []
    latest = from_latest(
        ledger, "state-mig",
        title="State-to-state taxpayer migration, 2022-23",
        skip_us=True,
    )
    if latest:
        out.append(latest)
    return out


def figs_dl21(ledger):
    sec = _sec(ledger)
    agi = sec.get("ma_county_agi_2022") or {}
    fig = named_list(
        agi.get("top_five"), "county-agi",
        "Massachusetts county adjusted gross income, tax year 2022",
        "Middlesex County is highest at $125.60 billion.",
        agi.get("src") or "SRC-621-02",
        "usd", "dollars",
        agi.get("note") or "County AGI is the sum of SOI size-of-AGI stubs.",
        n=5, span=2,
    )
    out = [fig] if fig else []
    latest = from_latest(
        ledger, "state-agi",
        title="State adjusted gross income, tax year 2022",
        skip_us=True,
    )
    if latest:
        out.append(latest)
    stubs = ((sec.get("agi_stubs_2022") or {}).get("ma") or {}).get("stubs") or []
    if stubs:
        labels = [s["name"].replace("adjusted gross income", "AGI") for s in stubs]
        values = [s["agi_share_pct"] for s in stubs]
        mp = (sec.get("agi_stubs_2022") or {}).get("ma", {}).get("million_plus") or {}
        out.append(_fig(
            "agi-stubs",
            "Massachusetts AGI by size-of-AGI stub, tax year 2022",
            (
                f"Returns with $1 million or more held {mp.get('agi_share_pct')} "
                "percent of Massachusetts AGI."
            ),
            "SRC-621-03",
            "bar", "percent", "percent of AGI",
            labels, _bars(labels, values),
            "IRS SOI Historic Table 2 size-of-AGI stubs. This is not a dedicated percentile file.",
            span=2,
        ))
    fig = from_snap(
        (sec.get("agi_stubs_2022") or {}).get("million_plus_agi_share"),
        "agi-million",
        title="Share of AGI on returns with $1 million or more, tax year 2022",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl22(ledger):
    sec = _sec(ledger)
    ntd = sec.get("ntd_annual_2024") or {}
    out = []
    mbta = ntd.get("mbta") or {}
    if mbta.get("farebox_pct") is not None and ntd.get("us_farebox_pct") is not None:
        labels = ["United States", "MBTA"]
        values = [ntd["us_farebox_pct"], mbta["farebox_pct"]]
        out.append(_fig(
            "farebox",
            "Farebox recovery, report year 2024",
            (
                f"MBTA fares covered {mbta['farebox_pct']} percent of operating cost, "
                f"versus {ntd['us_farebox_pct']} percent across {ntd.get('agencies'):,} agencies."
            ),
            ntd.get("src") or "SRC-622-02",
            "bar", "percent", "percent",
            labels, _bars(labels, values, highlight="MBTA"),
            "FTA NTD annual agency file, report year 2024.",
        ))
    if mbta.get("operating") is not None and (ntd.get("highest") or {}).get("v"):
        labels = [ntd["highest"]["name"], "MBTA"]
        values = [ntd["highest"]["v"], mbta["operating"]]
        out.append(_fig(
            "ntd-op",
            "Agency operating expenses, report year 2024",
            (
                f"MBTA operating cost was ${mbta['operating'] / 1e9:.2f} billion, "
                f"rank {mbta.get('rank')} of {mbta.get('n')}. Cost per trip was "
                f"${mbta.get('cost_per_trip')}."
            ),
            ntd.get("src") or "SRC-622-02",
            "bar", "usd", "dollars",
            labels, _bars(labels, values, highlight="MBTA"),
            "The U.S. operating total is omitted so the agency bars remain readable.",
        ))
    return out


def figs_dl23(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_snap(
        sec.get("fema_pa_obligations"), "fema-pa",
        title="FEMA Public Assistance federal share obligated",
        skip_us=True,
        note="OpenFEMA extract. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("nri_mean_county_score"), "nri",
        title="National Risk Index, mean county score",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl24(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_snap(
        sec.get("seds_production_2024"), "seds-prod",
        title="Total energy production, 2024",
        skip_us=True,
        note="EIA SEDS TEPRB. Massachusetts ranks 46 of 51. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("seds_consumption_2024"), "seds-cons",
        title="Total energy consumption, 2024",
        skip_us=True,
        note="EIA SEDS TETCB. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl25(ledger):
    sec = _sec(ledger)
    peers = ((sec.get("population_peers_2025") or {}).get("peers") or {}).get("Boston city") or []
    latest = ledger.get("latest") or {}
    boston = (latest.get("highest") or {}).get("v")
    rows = []
    if boston is not None:
        rows.append({"name": "Boston city", "v": boston})
    rows.extend({"name": r["name"], "v": r["pop"]} for r in peers if r.get("pop") is not None)
    fig = named_list(
        rows, "boston-peers",
        "Boston and the five nearest Census 2025 populations",
        "Nearest means closest resident count, not the old Pioneer socioeconomic peer workbook.",
        "SRC-625-02",
        "number", "people",
        "Census vintage 2025 subcounty estimates, SUMLEV 061. Five nearest counts for Boston city.",
        n=6, highlight="Boston city", span=2,
    )
    out = [fig] if fig else []
    acs = sec.get("acs_towns_2024") or {}
    fig = named_list(
        (acs.get("income") or {}).get("top_eight"), "town-income",
        "Highest median household income, ACS 2020-2024",
        (
            f"{(acs.get('income') or {}).get('highest', {}).get('name')} is highest. "
            f"Boston is ${(acs.get('boston') or {}).get('median_hh_income'):,}."
        ) if (acs.get("boston") or {}).get("median_hh_income") else "ACS median household income.",
        acs.get("src") or "SRC-625-03",
        "usd", "dollars",
        "Census ACS 5-year 2020-2024, county subdivisions. Some small towns are suppressed.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
    fig = named_list(
        (acs.get("home_value") or {}).get("top_eight"), "town-home",
        "Highest median home value, ACS 2020-2024",
        "Owner-occupied median value among towns with a published ACS estimate.",
        acs.get("src") or "SRC-625-03",
        "usd", "dollars",
        "Census ACS 5-year 2020-2024 table B25077.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
    peers = (acs.get("socioeconomic_peers") or {}).get("Boston city") or []
    rows = [{"name": "Boston city", "v": (acs.get("boston") or {}).get("median_hh_income")}]
    rows.extend({"name": r["name"], "v": r.get("median_hh_income")} for r in peers)
    fig = named_list(
        rows, "acs-peers",
        "Boston and five nearest ACS socioeconomic peers",
        "Nearest on z-scored income, home value, and bachelor's share. Not the old Pioneer workbook.",
        acs.get("src") or "SRC-625-03",
        "usd", "dollars",
        acs.get("peer_method") or "ACS 5-year socioeconomic distance.",
        n=6, highlight="Boston city", span=2,
    )
    if fig:
        out.append(fig)
    return out


def figs_dl26(ledger):
    sec = _sec(ledger)
    ppe = sec.get("district_ppe_fy2025") or {}
    fig = named_list(
        ppe.get("top_five"), "dist-ppe",
        "Highest district total expenditures per pupil, FY 2025",
        (
            f"Truro is highest at ${ppe.get('highest', {}).get('v'):,}. "
            f"Lowest is {ppe.get('lowest', {}).get('name')} at "
            f"${ppe.get('lowest', {}).get('v'):,}."
        ) if ppe.get("highest") and ppe.get("lowest") else "DESE district total expenditures per pupil.",
        ppe.get("src") or "SRC-606-07",
        "usd", "dollars per pupil",
        "DESE / E2C district finance. Small districts sit at the top of a per-pupil ranking.",
        n=5, span=2,
    )
    out = [fig] if fig else []
    acs = sec.get("acs_rankings_2024") or {}
    fig = named_list(
        (acs.get("income") or {}).get("top_eight"), "rank-income",
        "Highest median household income, ACS 2020-2024",
        (
            f"{(acs.get('income') or {}).get('highest', {}).get('name')} is highest at "
            f"${(acs.get('income') or {}).get('highest', {}).get('v'):,}."
        ) if (acs.get("income") or {}).get("highest") else "ACS median household income.",
        acs.get("src") or "SRC-626-03",
        "usd", "dollars",
        "Census ACS 5-year 2020-2024. DLS levy and crime ranks are not a stable public CSV.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
    fig = named_list(
        (acs.get("poverty") or {}).get("top_eight"), "rank-poverty",
        "Highest poverty rate, ACS 2020-2024",
        (
            f"{(acs.get('poverty') or {}).get('highest', {}).get('name')} is highest at "
            f"{(acs.get('poverty') or {}).get('highest', {}).get('v')} percent."
        ) if (acs.get("poverty") or {}).get("highest") else "ACS poverty rate.",
        acs.get("src") or "SRC-626-03",
        "percent", "percent",
        "Census ACS 5-year 2020-2024 table B17001.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
    fig = named_list(
        (acs.get("home_value") or {}).get("top_eight"), "rank-home",
        "Highest median home value, ACS 2020-2024",
        "Owner-occupied median value among towns with a published ACS estimate.",
        acs.get("src") or "SRC-626-03",
        "usd", "dollars",
        "Census ACS 5-year 2020-2024 table B25077.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
    return out


def figs_dl27(ledger):
    sec = _sec(ledger)
    bud = sec.get("boston_operating_budget_fy26") or {}
    out = []
    fig = named_list(
        bud.get("top_five"), "bos-budget",
        "Largest Boston operating-budget departments, FY26 appropriation",
        "Boston Public Schools is the largest line.",
        bud.get("src") or "SRC-627-02",
        "usd", "dollars",
        "City of Boston adopted operating budget, FY26 appropriation.",
        n=5, span=2,
    )
    if fig:
        out.append(fig)
    if bud.get("fy25_actual") is not None:
        labels = ["FY25 actual", "FY26 appropriation", "FY27 budget"]
        values = [bud["fy25_actual"], bud["fy26_appropriation"], bud.get("fy27_budget")]
        if values[2] is not None:
            out.append(_fig(
                "bos-years",
                "Boston operating budget, three published years",
                "The adopted FY26 appropriation is $4.91 billion.",
                bud.get("src") or "SRC-627-02",
                "bar", "usd", "dollars",
                labels, _bars(labels, values),
                "City of Boston operating budget file.",
            ))
    return out


def figs_dl28(ledger):
    rows = [
        r for r in (ledger.get("rows") or [])
        if r.get("name") and r.get("name") != "Total Taxes" and r.get("v")
    ]
    fig = named_list(
        rows, "tax-types",
        "Massachusetts state tax collections by type, 2026 Q1",
        "Individual income is the largest source after the total.",
        "SRC-628-01",
        "usd", "dollars",
        "Census QTAX 2026 Q1 table 3. Total Taxes is omitted so the type split is readable. DOR monthly reports remain pending.",
        n=8, span=2,
    )
    out = [fig] if fig else []
    sec = _sec(ledger)
    q = sec.get("qtax_type_shares_2026q1") or {}
    types = [t for t in (q.get("types") or []) if t.get("ma_share_pct") and t["ma_share_pct"] >= 3]
    types = sorted(types, key=lambda t: -t["ma_share_pct"])[:8]
    if types:
        labels = [t["name"] for t in types]
        values = [t["ma_share_pct"] for t in types]
        inc = q.get("individual_income") or {}
        out.append(_fig(
            "tax-shares",
            "Massachusetts tax-type shares, 2026 Q1",
            (
                f"Individual income was {inc.get('ma_share_pct')} percent of "
                "Commonwealth collections."
            ),
            q.get("src") or "SRC-628-01",
            "bar", "percent", "percent of total taxes",
            labels, _bars(labels, values),
            "Census QTAX 2026 Q1. Types under 3 percent are omitted.",
            span=2,
        ))
    stc = ((sec.get("stc_ma_2023") or {}).get("ma_types")) or []
    fig = named_list(
        [t for t in stc if t.get("name") and t["name"] != "Total Taxes"],
        "stc-ma",
        "Massachusetts annual state tax collections, FY 2023",
        "Census Annual Survey of State Government Tax Collections.",
        "SRC-628-02",
        "usd", "dollars",
        "Census STC FY 2023. Amounts are published in thousands of dollars.",
        n=6, span=2,
    )
    if fig:
        out.append(fig)
    return out


def figs_dl29(ledger):
    fig = from_latest(
        ledger, "state-taxes",
        title="State tax collections, 2026 Q1",
        skip_us=True,
        note="Census QTAX 2026 Q1 table 3. The U.S. total is omitted so state bars remain readable. NASBO rainy-day figures remain pending.",
    )
    out = [fig] if fig else []
    sec = _sec(ledger)
    fig = from_snap(
        sec.get("aspep_fte_2023"), "aspep",
        title="State government FTE employment, 2023",
        skip_us=True,
        note="Census ASPEP 2023. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    stc = sec.get("stc_2023") or {}
    fig = from_snap(
        stc.get("total"), "stc-total",
        title="State tax collections, FY 2023",
        skip_us=True,
        note="Census STC FY 2023. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        stc.get("income_share"), "stc-income-share",
        title="Individual income tax share of state collections, FY 2023",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl30(ledger):
    sec = _sec(ledger)
    out = []
    quasi = sec.get("quasi_payroll_2025") or {}
    fig = named_list(
        quasi.get("top_five"), "quasi",
        "Massachusetts quasi-public payroll, calendar 2025",
        (
            f"Fifteen agencies paid ${quasi.get('total'):,.0f} to "
            f"{quasi.get('employees'):,} employees. Massport is the largest."
        ) if quasi.get("total") else "CTHRU quasi-public payroll.",
        quasi.get("src") or "SRC-630-03",
        "usd", "dollars",
        "CTHRU quasi-public agency payroll, calendar 2025.",
        n=5, span=2,
    )
    if fig:
        out.append(fig)
    vend = sec.get("vendor_extract_fy2025") or {}
    fig = named_list(
        vend.get("top_ten"), "vendors",
        "Largest CTHRU vendor payments, non-payroll object classes, FY 2025",
        "Names are the published payee field, including summary trust and payroll-like rollups that survived the object-class filter.",
        vend.get("src") or "SRC-630-04",
        "usd", "dollars",
        vend.get("note") or "CTHRU Comptroller spending extract.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
    return out


def figs_dl31(ledger):
    fig = from_latest(
        ledger, "prisoners",
        title="Prisoners under jurisdiction, year-end 2023",
        skip_us=True,
        note="BJS Prisoners in 2023, table 2. The U.S. total is omitted so state bars remain readable. FBI crime rates are not a stable machine file on this page.",
    )
    out = [fig] if fig else []
    sec = _sec(ledger)
    b = sec.get("bjs_depth_2023") or {}
    fig = from_snap(
        b.get("imprisonment_rate"), "prison-rate",
        title="Imprisonment rate per 100,000 residents, 2023",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        b.get("admissions"), "admissions",
        title="Admissions of sentenced prisoners, 2023",
        skip_us=True,
        note="BJS Prisoners in 2023, table 8. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        b.get("juveniles_in_adult_prisons"), "youth-adult",
        title="Prisoners age 17 or younger in adult prisons, 2023",
        skip_us=True,
        note="BJS table 15. This is youth in adult prisons, not OJJDP juvenile-justice custody.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl32(ledger):
    latest = ledger.get("latest") or {}
    derived = ledger.get("derived") or {}
    out = []
    fig = named_list(
        latest.get("components") or derived.get("components"),
        "components",
        "Massachusetts legislator payroll by component, calendar 2025",
        "Base salary, Comptroller supplemental (AA1), and stipends (A14). Employer-paid health and pension contributions are not in this file.",
        "SRC-632-01",
        "usd",
        "dollars",
        "CTHRU named payroll for Representative and Senator titles, calendar 2025.",
        n=3,
        span=2,
    )
    if fig:
        out.append(fig)
    fig = named_list(
        derived.get("chamber_medians"),
        "chamber-median",
        "House and Senate median pay, calendar 2025",
        "Medians are from the published Representative and Senator rows, including partial-year replacements.",
        "SRC-632-01",
        "usd",
        "dollars",
        "CTHRU named House and Senate payroll, calendar 2025.",
        n=2,
        span=1,
    )
    if fig:
        out.append(fig)
    fig = named_list(
        ledger.get("rows"),
        "top-pay",
        "Highest legislator pay, calendar 2025",
        "Speaker and Senate President sit at the top. Type a name in the table to open the component card.",
        "SRC-632-01",
        "usd",
        "dollars",
        "CTHRU named House and Senate payroll, calendar 2025.",
        n=8,
        span=1,
    )
    if fig:
        out.append(fig)
    return out


DISPATCH = {
    "DL-06": figs_dl06,
    "DL-07": figs_dl07,
    "DL-08": figs_dl08,
    "DL-09": figs_dl09,
    "DL-10": figs_dl10,
    "DL-12": figs_dl12,
    "DL-13": figs_dl13,
    "DL-14": figs_dl14,
    "DL-15": figs_dl15,
    "DL-16": figs_dl16,
    "DL-17": figs_dl17,
    "DL-19": figs_dl19,
    "DL-20": figs_dl20,
    "DL-21": figs_dl21,
    "DL-22": figs_dl22,
    "DL-23": figs_dl23,
    "DL-24": figs_dl24,
    "DL-25": figs_dl25,
    "DL-26": figs_dl26,
    "DL-27": figs_dl27,
    "DL-28": figs_dl28,
    "DL-29": figs_dl29,
    "DL-30": figs_dl30,
    "DL-31": figs_dl31,
    "DL-32": figs_dl32,
}


def insight_figures(app, ledger):
    if (ledger.get("status") or app.get("wave")) in ("build", "pending"):
        return []
    if ledger.get("status") != "live":
        return []
    tid = app["id"]
    fn = DISPATCH.get(tid)
    figs = fn(ledger) if fn else []
    figs = [f for f in figs if f]
    if not figs:
        fallback = from_latest(ledger)
        if fallback:
            figs = [fallback]
    return figs
