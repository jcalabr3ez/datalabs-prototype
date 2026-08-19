#!/usr/bin/env python3
"""Compact insight charts for live suite pages and the landing portfolio.

Every number comes from a published ledger cell. Waitlists and other
unpublished series are captioned as missing, never invented.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_voice import short_place, short_place_text

GOLD = "#CCB26D"
RUST = "#C45C26"
NAVY = "#293C5C"
INK = "#1A1A1A"
STEEL = "#A9B8C8"
GREY = "#8DA0B5"


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


def _bar_color(lab, names):
    text = str(lab)
    if lab in ("United States", "US") or text.startswith("United States"):
        return INK
    if lab in ("Massachusetts", "MA") or text == "Massachusetts":
        return GOLD
    if lab in ("Florida", "FL") or text == "Florida":
        return RUST
    if lab in names:
        return NAVY
    return STEEL


def _bars(labels, values, highlight=None, highlight_names=None):
    names = set(highlight_names or [])
    if highlight:
        names.add(highlight)
    colors = [_bar_color(lab, names) for lab in labels]
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


def _filter_states(snap, extra_rows=None):
    """Published state cells only. Never invents a missing rank."""
    cells = []
    seen = set()

    def add(st, name, v):
        if v is None or not st or st in seen:
            return
        seen.add(st)
        cells.append({"st": str(st), "name": name or str(st), "v": v})

    add("US", "United States", _snap_val(snap.get("us")))
    add("MA", "Massachusetts", _snap_val(snap.get("ma")))
    fl = snap.get("fl")
    if isinstance(fl, dict):
        add(fl.get("st") or "FL", fl.get("name") or "Florida", _snap_val(fl))
    elif fl is not None:
        add("FL", "Florida", fl)
    for key in ("highest", "lowest"):
        row = snap.get(key) or {}
        if isinstance(row, dict):
            add(row.get("st"), row.get("name"), row.get("v"))
    for row in list(extra_rows or []) + list(snap.get("rows") or []):
        if isinstance(row, dict):
            add(row.get("st"), row.get("name"), row.get("v"))
    return cells


def _with_filter(fig, snap, extra_rows=None):
    if not fig:
        return fig
    states = _filter_states(snap, extra_rows)
    if len(states) >= 3:
        fig["filter_states"] = states
    return fig


def from_snap(snap, fid, title=None, lede=None, note=None, skip_us=None, span=1, extra_rows=None):
    if not snap:
        return None
    ma = snap.get("ma") if isinstance(snap.get("ma"), dict) else None
    ma_v = _snap_val(snap.get("ma"))
    fl = snap.get("fl") if isinstance(snap.get("fl"), dict) else None
    if fl is None:
        for r in snap.get("rows") or []:
            if r.get("st") == "FL":
                fl = r
                break
    us = _snap_val(snap.get("us"))
    hi = snap.get("highest") or {}
    lo = snap.get("lowest") or {}
    if fl is None:
        if hi.get("st") == "FL":
            fl = hi
        elif lo.get("st") == "FL":
            fl = lo
    fl_v = _snap_val(fl)
    others = [v for v in (ma_v, fl_v, hi.get("v"), lo.get("v")) if v is not None]
    hide_us = skip_us if skip_us is not None else _us_dwarfs(us, others)
    pairs = []
    if us is not None and not hide_us:
        pairs.append(("United States", us))
    if hi.get("name") and hi.get("v") is not None and hi.get("st") not in ("MA", "FL"):
        pairs.append((hi["name"], hi["v"]))
    if ma_v is not None:
        pairs.append(("Massachusetts", ma_v))
    lo_st = lo.get("st")
    hi_st = hi.get("st")
    if lo.get("name") and lo.get("v") is not None and lo_st not in ("MA", "FL", hi_st):
        pairs.append((lo["name"], lo["v"]))
    if len(pairs) < 2:
        return None
    unit = snap.get("unit") or ""
    src = snap.get("src") or ""
    title = title or snap.get("label") or "Comparison"
    if lede is None:
        lede = snap.get("label") or title
        bits = []
        if hi.get("name") and hi.get("st") not in ("MA", "FL"):
            bits.append(f"{hi['name']} is highest")
        if ma and ma.get("rank") and ma.get("n"):
            bits.append(f"Massachusetts ranks {ma['rank']} of {ma['n']}")
        if bits:
            lede += ". " + "; ".join(bits) + " (derived)."
    note = note or snap.get("note") or "Published cells only. Ranks are Pioneer calculations (derived)."
    fmt = "percent" if "percent" in unit.lower() else (
        "usd" if "dollar" in unit.lower() else "number"
    )
    fig = _fig(
        fid, title, lede, src, "bar", fmt, unit,
        [p[0] for p in pairs],
        _bars([p[0] for p in pairs], [p[1] for p in pairs]),
        note, span=span,
    )
    return _with_filter(fig, snap, extra_rows)


def from_latest(ledger, fid="latest-compare", title=None, lede=None, note=None, skip_us=None):
    latest = ledger.get("latest") or {}
    if not latest.get("ma") and not latest.get("highest"):
        return None
    src_map = ledger.get("source_id_map") or {}
    fl = next((r for r in (ledger.get("rows") or []) if r.get("st") == "FL"), None)
    snap = {
        "us": latest.get("us"),
        "ma": latest.get("ma"),
        "fl": fl,
        "highest": latest.get("highest"),
        "lowest": latest.get("lowest"),
        "label": ledger.get("metric_label") or "Latest comparison",
        "src": next(iter(src_map), ""),
        "unit": ledger.get("unit") or "",
        "note": note,
    }
    return from_snap(
        snap, fid, title=title, lede=lede, note=note, skip_us=skip_us,
        extra_rows=ledger.get("rows") or [],
    )


def state_map(rows, fid, title, lede, src, fmt, unit, note, name_key="name", val_key="v", span=2):
    items = []
    for r in rows or []:
        st = r.get("st")
        if not st or r.get(val_key) is None:
            continue
        items.append({
            "st": st,
            "name": r.get(name_key) or st,
            "v": r[val_key],
            "rank": r.get("rank"),
        })
    if len(items) < 10:
        return None
    fig = _fig(
        fid, title, lede, src, "map", fmt, unit,
        [r["st"] for r in items],
        [{"label": "", "data": [r["v"] for r in items]}],
        note, span=span, height="map",
    )
    fig["rows"] = items
    return fig


def named_list(rows, fid, title, lede, src, fmt, unit, note, name_key="name", val_key="v", n=8, highlight=None, highlight_names=None, span=1):
    items = [r for r in (rows or []) if r.get(val_key) is not None][:n]
    if len(items) < 2:
        return None
    labels = [short_place(r.get(name_key) or "") for r in items]
    values = [r[val_key] for r in items]
    names = [r.get(name_key) for r in items if r.get(name_key)]
    hl_names = [short_place(n) for n in (highlight_names or [])]
    return _fig(
        fid, title, short_place_text(lede, names), src, "bar", fmt, unit, labels,
        _bars(labels, values, highlight=short_place(highlight) if highlight else None, highlight_names=hl_names),
        short_place_text(note, names), span=span, height="mid" if len(items) >= 8 else None,
    )


def _slope(pairs, fid, title, lede, src, fmt, unit, note, left="2019", right="2024"):
    if not pairs:
        return None
    series = []
    for p in pairs:
        if p.get("from") is None or p.get("to") is None:
            continue
        series.append({
            "label": p["label"],
            "data": [p["from"], p["to"]],
            "color": p.get("color") or NAVY,
        })
    if len(series) < 2:
        return None
    return _fig(
        fid, title, lede, src, "slope", fmt, unit,
        [left, right], series, note, span=2,
    )


def _histogram(values, fid, title, lede, src, fmt, unit, note, bins=10, span=2):
    nums = [float(v) for v in (values or []) if v is not None]
    if len(nums) < 8:
        return None
    lo, hi = min(nums), max(nums)
    nbin = max(4, min(bins, 12))
    width = (hi - lo) / nbin if hi != lo else 1
    counts = [0] * nbin
    for v in nums:
        i = 0 if width == 0 else min(int((v - lo) / width), nbin - 1)
        counts[i] += 1

    def edge(x):
        if fmt == "percent":
            return f"{x:.0f}%"
        if fmt == "usd":
            if abs(x) >= 1e6:
                return f"${x/1e6:.1f} million"
            return f"${x:,.0f}"
        if abs(x) >= 1000:
            return f"{x:,.0f}"
        return f"{x:.1f}" if x != int(x) else str(int(x))

    labels = []
    for i in range(nbin):
        a = lo + i * width
        b = lo + (i + 1) * width if i < nbin - 1 else hi
        labels.append(f"{edge(a)} to {edge(b)}")
    fig = _fig(
        fid, title, lede, src, "hist", fmt, unit,
        labels, [{"label": "", "data": counts, "colors": [NAVY] * nbin}],
        note, span=span,
    )
    fig["index_axis"] = "x"
    return fig


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
    enroll = sec.get("public_k12_enrollment") or {}
    enr_pts = enroll.get("trend") or []
    enr_labels, enr_values = _trend_xy(enr_pts)
    ma_enr = (enroll.get("ma") or {}).get("v")
    ma_rank = (enroll.get("ma") or {}).get("rank")
    ma_n = (enroll.get("ma") or {}).get("n")
    if enr_labels and all(v is not None for v in enr_values) and ma_enr is not None:
        peak = max(enr_pts, key=lambda p: p.get("v") or 0)
        recent = max(
            (p for p in enr_pts if (p.get("y") or 0) >= 2014),
            key=lambda p: p.get("v") or 0,
            default=peak,
        )
        rank_bit = (
            f", rank {ma_rank} of {ma_n}" if ma_rank and ma_n else ""
        )
        out.append(_fig(
            "ma-enroll",
            "Massachusetts public K-12 enrollment, Fall 1990 to Fall 2024",
            (
                f"Massachusetts public schools enrolled {ma_enr:,} students "
                f"in Fall 2024{rank_bit}. Fall {peak.get('y')} was "
                f"{peak.get('v'):,}; Fall {recent.get('y')} was "
                f"{recent.get('v'):,}."
            ),
            enroll.get("src") or "SRC-606-02",
            "line", "number", "students",
            [str(x) for x in enr_labels], _line(enr_values, "Massachusetts"),
            enroll.get("note") or (
                "NCES Digest table 203.20, public elementary and secondary "
                "enrollment."
            ),
            span=2,
        ))
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
    fin = sec.get("district_finance_fy2025") or {}
    fig = named_list(
        fin.get("top_five"), "dist-ppe-ma",
        "Highest Massachusetts district total expenditures per pupil, FY 2025",
        (
            f"{(fin.get('highest') or {}).get('name')} was highest at "
            f"${(fin.get('highest') or {}).get('v'):,}."
        ) if fin.get("highest") else "DESE district total expenditures per pupil.",
        fin.get("src") or "SRC-606-07",
        "usd", "dollars per pupil",
        "DESE / E2C district finance. Small districts sit at the top of a per-pupil ranking.",
        n=5, span=2,
    )
    if fig:
        out.append(fig)
    demo = sec.get("ma_enrollment_demographics_2026") or {}
    race = [r for r in (demo.get("race") or []) if r.get("v") is not None]
    if race:
        labels = [r["name"] for r in race]
        values = [r["v"] for r in race]
        out.append(_fig(
            "ma-race",
            "Massachusetts public-school enrollment by race, 2025-26",
            (
                f"{demo.get('total'):,} students. White {race[0]['v']} percent; "
                f"Hispanic or Latino {next((r['v'] for r in race if 'Hispanic' in r['name']), None)} percent."
            ),
            demo.get("src") or "SRC-606-08",
            "bar", "percent", "percent",
            labels, _bars(labels, values),
            demo.get("note") or "DESE / E2C statewide All Students.",
            span=2,
        ))
    selected = [r for r in (demo.get("selected") or []) if r.get("v") is not None]
    if selected:
        labels = [r["name"] for r in selected]
        values = [r["v"] for r in selected]
        li = next((r for r in selected if r["name"] == "Low income"), {})
        el = next((r for r in selected if r["name"] == "English learners"), {})
        out.append(_fig(
            "ma-selected",
            "Massachusetts selected populations, 2025-26",
            (
                f"Low income {li.get('v')} percent; English learners "
                f"{el.get('v')} percent."
            ),
            demo.get("src") or "SRC-606-08",
            "bar", "percent", "percent",
            labels, _bars(labels, values),
            "DESE / E2C selected populations. Shares are of statewide enrollment.",
            span=2,
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
    hist = (sec.get("naep_2024") or {}).get("history") or {}
    rec = (hist.get("read4") or {}).get("change_2019_2024") or {}
    rows = rec.get("rows") or []
    ma_row = next((r for r in rows if r.get("st") == "MA"), None) or {}
    ma_from, ma_to = ma_row.get("from"), ma_row.get("to")
    pairs = []
    us_hist = {p["y"]: p["v"] for p in (hist.get("read4") or {}).get("us") or [] if p.get("v") is not None}
    if 2019 in us_hist and 2024 in us_hist:
        pairs.append({"label": "National public", "from": us_hist[2019], "to": us_hist[2024], "color": INK})
    if ma_from is not None and ma_to is not None:
        pairs.append({"label": "Massachusetts", "from": ma_from, "to": ma_to, "color": GOLD})
    gain = sorted(
        [r for r in rows if r.get("st") != "MA" and r.get("from") is not None and r.get("to") is not None],
        key=lambda r: (r["to"] - r["from"]),
        reverse=True,
    )
    if gain:
        top, bot = gain[0], gain[-1]
        pairs.append({"label": top.get("name") or top.get("st"), "from": top["from"], "to": top["to"], "color": NAVY})
        if bot.get("st") != top.get("st"):
            pairs.append({"label": bot.get("name") or bot.get("st"), "from": bot["from"], "to": bot["to"], "color": GREY})
    fig = _slope(
        pairs, "naep-read4-slope",
        "NAEP grade 4 reading, 2019 to 2024",
        (
            f"{rec.get('n_up')} states rose and {rec.get('n_down')} fell. "
            f"Massachusetts went from {ma_from} to {ma_to}."
        ) if ma_from is not None else "2019 to 2024 scale-score change.",
        rec.get("src") or "SRC-607-05",
        "number", "scale score",
        "Average scale scores. National public is the published NP line when the year exists.",
    )
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
            "percent nationally. Means are not comparable across states "
            "with very different participation rates."
        ) if sat.get("ma") and sat.get("us") else None,
    )
    if fig:
        out.append(fig)
    ratio = sec.get("students_per_faculty_fall_2023") or {}
    fig = from_snap(
        ratio, "he-ratio",
        title="FTE students per FTE faculty, Fall 2023",
        lede=(
            f"Massachusetts {ratio['ma']['v']} students per faculty, rank "
            f"{ratio['ma']['rank']} of {ratio['ma']['n']}. Florida is "
            f"{(ratio.get('fl') or {}).get('v')}. The U.S. ratio is {ratio.get('us')}."
        ) if ratio.get("ma") else None,
        note="NCES Digest table 314.50. A lower ratio is fewer students per faculty member.",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("ipeds_6yr_grad_by_state_2017"), "ipeds-6yr-state",
        title="IPEDS 6-year bachelor's graduation rate, 2017 cohort",
        note="IPEDS GR2023 joined to HD2023. Completers within 150% of normal time (GRTYPE 12) divided by the adjusted bachelor's cohort (GRTYPE 8).",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("he_public4_tuition_2022_23"), "he-tuition",
        title="Public 4-year in-state tuition and fees, 2022-23",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("he_education_appropriations_fy2025"), "he-shef",
        title="Education appropriations for public higher education, FY 2025",
        skip_us=True,
        note="SHEEO SHEF FY 2025 Report Data. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("bachelors_conferred_2023_24"), "he-ba",
        title="Bachelor's degrees conferred, 2023-24",
        skip_us=True,
        note="IPEDS C2024_A first-major bachelor's degrees at degree-granting institutions. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl09(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_snap(
        sec.get("teachers_fte_fall_2022"), "teachers-fte",
        title="Public-school teachers (FTE), Fall 2022",
        skip_us=True,
        note="NCES Digest table 208.30. These are all public-school teachers, not charter staff only.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl10(ledger):
    latest = ledger.get("latest") or {}
    out = []
    stars = {}
    for r in ledger.get("rows") or []:
        v = r.get("v")
        if v is None:
            continue
        stars[int(v)] = stars.get(int(v), 0) + 1
    if stars:
        labels = [f"{s} star" + ("" if s == 1 else "s") for s in range(5, 0, -1)]
        values = [stars.get(s, 0) for s in range(5, 0, -1)]
        fig = _fig(
            "hospital-stars",
            "Rated Massachusetts hospitals by overall star rating",
            (
                f"{latest.get('n_rated')} rated, {latest.get('n_unrated')} unrated. "
                "Unrated facilities are omitted from this figure."
            ),
            "SRC-610-02",
            "hist", "number", "hospitals",
            labels, _bars(labels, values),
            "CMS overall star rating among rated facilities only.",
        )
        fig["index_axis"] = "x"
        out.append(fig)
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
        ))
    return out[:2]


def figs_dl11(ledger):
    sec = _sec(ledger)
    out = []
    types = (sec.get("type_mix") or {}).get("rows") or []
    fig = named_list(
        types,
        "type-mix",
        "Participating 340B sites by entity type",
        "Disproportionate share hospitals and community health centers are the two largest groups on the current OPAIS file.",
        "SRC-611-01",
        "number",
        "sites",
        "Currently participating 340B IDs. A parent hospital and its child sites each count.",
        n=8,
        span=1,
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("charity_care"),
        "charity-share",
        title="Hospital charity-care share of total costs, 2023",
        note="CMS Hospital Provider Cost Report PUF, Worksheet S-10. RAND TL-303 is the method citation for this series.",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("pharmacies_by_state"),
        "pharmacies",
        title="Unique active 340B contract pharmacies",
        skip_us=True,
        note="Unique pharmacyId values on an active contract. One pharmacy can contract with many covered entities.",
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
    return out


def _bed_annual_rates(trend, years=10):
    """Annual mean of published quarterly birth rates, last `years` years."""
    by_year = {}
    for r in trend:
        ma = r.get("ma_birth_rate_pct")
        us = r.get("us_birth_rate_pct")
        fl = r.get("fl_birth_rate_pct")
        if ma is None or us is None:
            continue
        y = int(str(r.get("q") or "").split()[0])
        rec = by_year.setdefault(y, {"ma": [], "us": [], "fl": []})
        rec["ma"].append(ma)
        rec["us"].append(us)
        if fl is not None:
            rec["fl"].append(fl)
    ordered = sorted(by_year)
    if not ordered:
        return []
    out = []
    for y in ordered[-years:]:
        ma = by_year[y]["ma"]
        us = by_year[y]["us"]
        fl = by_year[y]["fl"]
        rec = {
            "y": str(y),
            "ma_birth_rate_pct": round(sum(ma) / len(ma), 1),
            "us_birth_rate_pct": round(sum(us) / len(us), 1),
        }
        if fl:
            rec["fl_birth_rate_pct"] = round(sum(fl) / len(fl), 1)
        out.append(rec)
    return out


def figs_dl13(ledger):
    sec = _sec(ledger)
    out = []
    bed = sec.get("bed_births_deaths") or {}
    trend = bed.get("trend") or []
    window = _bed_annual_rates(trend, 10)
    if window:
        ma = bed.get("ma") or {}
        us = bed.get("us") or {}
        fl = bed.get("fl") or {}
        first, last = window[0], window[-1]
        series = [
            {"label": "Massachusetts", "data": [r.get("ma_birth_rate_pct") for r in window], "color": GOLD},
            {"label": "United States", "data": [r.get("us_birth_rate_pct") for r in window], "color": NAVY},
        ]
        fl_lede = ""
        if any(r.get("fl_birth_rate_pct") is not None for r in window):
            series.append({
                "label": "Florida",
                "data": [r.get("fl_birth_rate_pct") for r in window],
                "color": RUST,
            })
            fl_lede = (
                f" Florida averaged {last.get('fl_birth_rate_pct')} percent "
                f"in {last.get('y')}."
            )
        out.append(_fig(
            "bed-ma-us-rate",
            "Establishment birth rate, Massachusetts, Florida, and the United States",
            (
                f"Massachusetts averaged {last.get('ma_birth_rate_pct')} percent "
                f"in {last.get('y')}; the United States averaged "
                f"{last.get('us_birth_rate_pct')} percent."
                + fl_lede
                + (
                    f" In {first.get('y')}, the first year on this chart, "
                    f"the annual averages were {first.get('ma_birth_rate_pct')} "
                    f"and {first.get('us_birth_rate_pct')} percent."
                )
            ),
            bed.get("src") or "SRC-613-02",
            "line", "percent", "percent of establishments",
            [r["y"] for r in window],
            series,
            (
                "BLS Business Employment Dynamics, total private, seasonally "
                "adjusted. Each year is the Pioneer average of that year's "
                "published quarterly birth rates (derived, SRC-613-02). "
                "Latest quarterly Massachusetts print "
                f"{ma.get('births_as_of')}; Florida "
                f"{fl.get('births_as_of')}; United States "
                f"{us.get('births_as_of')}."
            ),
            span=2,
        ))
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
    if trend and any(r.get("fl_birth_rate_pct") is not None for r in trend):
        labels = [r["q"] for r in trend]
        fl = bed.get("fl") or {}
        ov = bed.get("fl_overlap") or {}
        out.append(_fig(
            "bed-fl-rates",
            "Florida establishment birth and death rates",
            (
                f"The birth rate was {fl.get('birth_rate_pct')} percent in "
                f"{fl.get('births_as_of')}. Deaths are published through "
                f"{fl.get('deaths_as_of')}. In {ov.get('q')}, the last "
                f"overlapping quarter, births were {ov.get('fl_birth_rate_pct')} "
                f"percent and deaths were {ov.get('fl_death_rate_pct')} percent."
            ),
            bed.get("src") or "SRC-613-02",
            "line", "percent", "percent of establishments",
            labels,
            [
                {"label": "Birth rate", "data": [r.get("fl_birth_rate_pct") for r in trend], "color": RUST},
                {"label": "Death rate", "data": [r.get("fl_death_rate_pct") for r in trend], "color": INK},
            ],
            bed.get("note") or (
                "BLS Business Employment Dynamics, total private, seasonally "
                "adjusted. Deaths lag three quarters."
            ),
            span=2,
        ))
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
    labor = sec.get("laus_labor_2026") or {}
    fig = from_snap(
        labor.get("lfpr"), "lfpr",
        title="Labor-force participation rate",
    )
    if fig:
        out.append(fig)
    return out[:2]


def figs_dl15(ledger):
    sec = _sec(ledger)
    out = []
    inds = ((sec.get("sagdp2_naics_2025") or {}).get("industries")) or {}
    labels, ma_vals, fl_vals = [], [], []
    for key, label in (
        ("manufacturing", "Manufacturing"),
        ("finance_insurance", "Finance and insurance"),
        ("information", "Information"),
        ("construction", "Construction"),
    ):
        rec = inds.get(key) or {}
        ma_v = _snap_val(rec.get("ma"))
        fl_v = _snap_val(rec.get("fl"))
        if ma_v is None:
            continue
        labels.append(label)
        ma_vals.append(ma_v * 1_000_000)
        fl_vals.append(None if fl_v is None else fl_v * 1_000_000)
    if labels:
        series = [{"label": "Massachusetts", "data": ma_vals, "color": GOLD}]
        if any(v is not None for v in fl_vals):
            series.append({"label": "Florida", "data": fl_vals, "color": RUST})
        out.append(_fig(
            "ma-industries",
            "Current-dollar GDP by industry, 2025",
            "Finance and insurance is the largest of these published Massachusetts NAICS slices. Florida is the rust series.",
            "SRC-615-03",
            "grouped", "usd", "dollars",
            labels, _grouped(series),
            "BEA SAGDP2. Values are industry GDP in current dollars. Information is suppressed in some other states.",
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
    fig = from_snap(
        sec.get("sqgdp_2026q1"), "sqgdp",
        title="Real GDP by state, 2026 Q1",
        skip_us=True,
        note="BEA SQGDP1 all-industry real GDP, millions of chained 2017 dollars. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl16(ledger):
    sec = _sec(ledger)
    out = []
    h = sec.get("fhfa_hpi_annual_change_2025") or {}
    ma = h.get("ma") if isinstance(h.get("ma"), dict) else {}
    fl = h.get("fl") if isinstance(h.get("fl"), dict) else {}
    hi = h.get("highest") or {}
    labels, values = [], []
    if hi.get("name") and hi.get("v") is not None and hi.get("st") not in ("MA", "FL"):
        labels.append(hi["name"])
        values.append(hi["v"])
    if ma.get("v") is not None:
        labels.append("Massachusetts")
        values.append(ma["v"])
    if fl.get("v") is not None:
        labels.append("Florida")
        values.append(fl["v"])
    if len(labels) >= 2:
        fl_v = fl.get("v")
        fl_bit = (
            f"Florida {'rose' if fl_v > 0 else 'fell'} {abs(fl_v)} percent, "
            f"rank {fl.get('rank')} of {fl.get('n')}"
            if fl_v is not None else ""
        )
        lede = (
            f"Massachusetts rose {ma.get('v')} percent in 2025, rank "
            f"{ma.get('rank')} of {ma.get('n')}."
            + (f" {fl_bit}." if fl_bit else "")
            + f" {hi.get('name')} was highest at {hi.get('v')} percent."
        )
        fig = _fig(
            "fhfa-hpi",
            "FHFA house-price index, annual change, 2025",
            lede,
            h.get("src") or "SRC-616-02",
            "bar", "percent", "percent",
            labels, _bars(labels, values),
            h.get("note") or (
                "FHFA does not publish a U.S. row in this state file. "
                "The index is developmental (FHFA note, March 31, 2026)."
            ),
        )
        out.append(_with_filter(fig, h))
    cs = sec.get("case_shiller_boston") or {}
    bos = {p.get("m"): p.get("v") for p in (cs.get("trend") or []) if p.get("m")}
    mia = {p.get("m"): p.get("v") for p in (cs.get("miami_trend") or []) if p.get("m")}
    months = [m for m in sorted(set(bos) | set(mia)) if bos.get(m) is not None]
    if len(months) >= 3:
        series = [{"label": "Boston MSA", "data": [bos.get(m) for m in months], "color": GOLD}]
        if any(mia.get(m) is not None for m in months):
            series.append({
                "label": "Miami MSA",
                "data": [mia.get(m) for m in months],
                "color": RUST,
            })
        yoy = cs.get("yoy_pct")
        mia_yoy = cs.get("miami_yoy_pct")
        yoy_bit = f", {yoy} percent from a year earlier" if yoy is not None else ""
        mia_bit = ""
        if cs.get("miami") is not None:
            mia_yoy_bit = (
                f", {mia_yoy} percent from a year earlier" if mia_yoy is not None else ""
            )
            mia_bit = (
                f" Miami was {cs.get('miami')} in {cs.get('miami_as_of_label')}"
                f"{mia_yoy_bit}."
            )
        out.append(_fig(
            "cs-boston",
            "Case-Shiller Boston and Miami house-price indexes",
            (
                f"Boston MSA {cs.get('boston')} in {cs.get('as_of_label')}"
                f"{yoy_bit}. January 2000 equals 100.{mia_bit}"
            ),
            cs.get("src") or "SRC-616-03",
            "line", "number", "index, January 2000 = 100",
            months, series,
            cs.get("note") or (
                "Seasonally adjusted Boston MSA series BOXRSA and Miami MSA "
                "series MIXRSA via FRED. January 2000 equals 100."
            ),
            span=2,
        ))
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
    fig = from_snap(
        sec.get("pop_age_65plus_share_2025"), "age65",
        title="Share of population age 65 and over, 2025",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("international_mig_2025"), "intl-mig",
        title="International migration, 2025",
        skip_us=True,
    )
    if fig:
        out.append(fig)
    return out


def figs_dl19(ledger):
    sec = _sec(ledger)
    out = []
    comps = ((sec.get("rpp_components_2024") or {}).get("components")) or {}
    order = [
        ("goods", "Goods"),
        ("housing", "Housing"),
        ("utilities", "Utilities"),
        ("other_services", "Other services"),
    ]
    us, ma, fl = [], [], []
    labels = []
    for key, lab in order:
        rec = comps.get(key) or {}
        if rec.get("us") is None or _snap_val(rec.get("ma")) is None:
            continue
        labels.append(lab)
        us.append(rec["us"])
        ma.append(_snap_val(rec["ma"]))
        fl.append(_snap_val(rec.get("fl")))
    if labels:
        series = [
            {"label": "United States", "data": us, "color": INK},
            {"label": "Massachusetts", "data": ma, "color": GOLD},
        ]
        if any(v is not None for v in fl):
            series.append({"label": "Florida", "data": fl, "color": RUST})
        out.append(_fig(
            "rpp-components",
            "Regional price parities by component, 2024",
            "Housing is the Massachusetts component furthest above the national index of 100. Florida is the rust series.",
            "SRC-619-02",
            "grouped", "number", "index (US = 100)",
            labels,
            _grouped(series),
            "BEA SARPP component RPPs. United States equals 100 on each line.",
            span=2,
        ))
    return out


def figs_dl20(ledger):
    sec = _sec(ledger)
    out = []
    pairs = sec.get("state_pair_flows_2022_23") or {}
    dest = pairs.get("ma_out_top") or []
    if dest:
        ma_fl = pairs.get("ma_to_fl") or {}
        top = dest[0]
        fl_bit = ""
        if ma_fl.get("returns") is not None and top.get("st") != "FL":
            fl_bit = (
                f" Massachusetts to Florida was {ma_fl['returns']:,} returns."
            )
        fig = named_list(
            [{"name": r["name"], "v": r["returns"]} for r in dest],
            "ma-destinations",
            "Where Massachusetts taxpayers moved, 2022-23",
            (
                f"{top.get('name')} was the largest destination at "
                f"{top.get('returns'):,} returns."
                + fl_bit
            ),
            pairs.get("src") or "SRC-620-01",
            "number", "returns",
            pairs.get("note") or (
                "Origin-destination returns from IRS SOI state outflow. "
                "Same-state and foreign rows are excluded."
            ),
            n=8, span=2,
        )
        if fig:
            out.append(fig)
    us = sec.get("us_county_taxpayer_migration_2022_23") or {}
    us_chart = list(us.get("chart") or [])
    if len(us_chart) > 10:
        us_chart = us_chart[:5] + us_chart[-5:]
    fig = named_list(
        us_chart, "us-county-mig",
        "Largest U.S. county taxpayer gains and losses, 2022-23",
        (
            f"{(us.get('highest') or {}).get('name')} had the largest net "
            f"inflow; {(us.get('lowest') or {}).get('name')} the largest "
            f"net outflow. {us.get('n_counties') or 0:,} counties are in the file. "
            "Massachusetts counties are marked in gold; Florida in rust."
        ) if us.get("highest") and us.get("lowest") else
        "Largest county net domestic taxpayer flows.",
        us.get("src") or "SRC-620-02",
        "number", "returns",
        us.get("note") or (
            "The five largest net gains and the five largest net losses. "
            "Net equals Total Migration-US inflow minus outflow."
        ),
        n=10, span=2,
        highlight_names=[
            r["name"] for r in (us.get("chart") or [])
            if r.get("st") in ("MA", "FL")
        ],
    )
    if fig:
        fig["height"] = "ranks"
        out.append(fig)
    mig = sec.get("ma_county_taxpayer_migration_2022_23") or {}
    ma_counties = list(mig.get("counties") or [])
    if len(ma_counties) > 10:
        ma_counties = ma_counties[:5] + ma_counties[-5:]
    fig = named_list(
        ma_counties, "county-mig",
        "Massachusetts county net domestic taxpayer migration, 2022-23",
        (
            f"{(mig.get('highest') or {}).get('name')} had the largest net "
            f"inflow; {(mig.get('lowest') or {}).get('name')} the largest "
            "net outflow."
        ) if mig.get("highest") else
        "Massachusetts county net domestic taxpayer migration.",
        mig.get("src") or "SRC-620-02",
        "number", "returns",
        mig.get("note") or "Net equals Total Migration-US inflow minus outflow. Same-state and foreign rows are excluded.",
        n=10, span=2,
    )
    if fig:
        out.append(fig)
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
    dd = sec.get("noaa_degree_days_2024") or {}
    if dd.get("ma_hdd") is not None and dd.get("us_hdd") is not None:
        labels = ["Heating degree days", "Cooling degree days"]
        out.append(_fig(
            "degree-days",
            "Heating and cooling degree days, 2024",
            (
                f"Massachusetts had {dd['ma_hdd']:,.0f} heating degree days and "
                f"{dd['ma_cdd']:,.0f} cooling degree days. The contiguous U.S. "
                f"was {dd['us_hdd']:,.0f} and {dd['us_cdd']:,.0f}."
            ),
            dd.get("src") or "SRC-623-05",
            "grouped", "number", "degree days",
            labels,
            _grouped([
                {"label": "United States", "data": [dd["us_hdd"], dd["us_cdd"]], "color": INK},
                {"label": "Massachusetts", "data": [dd["ma_hdd"], dd["ma_cdd"]], "color": GOLD},
            ]),
            "NOAA climate-at-a-glance annual totals, 2024.",
        ))
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
    # Finder card and town map carry the page. No largest-12 bars.
    return []


def figs_dl26(ledger):
    # Town map is the hero. Supporting figure is a histogram of the 351-town change, not a largest-12 bar.
    vals = [r.get("v") for r in (ledger.get("rows") or []) if r.get("v") is not None]
    fig = _histogram(
        vals, "town-change-hist",
        "Distribution of city and town population change, 2020 to 2025",
        "Every Census subcounty row. The map is the geography; the table lists every place.",
        "SRC-626-01",
        "number", "people",
        "Census vintage 2025 subcounty estimates minus 2020. Ranks are Pioneer calculations (derived).",
        bins=10,
    )
    return [fig] if fig else []


def figs_dl27(ledger):
    sec = _sec(ledger)
    bud = sec.get("boston_operating_budget_fy26") or {}
    out = []
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
    earn = sec.get("boston_top_earners_2025") or {}
    fig = named_list(
        earn.get("top"), "bos-earners",
        "Highest City of Boston earnings, calendar 2025",
        (
            f"{(earn.get('highest') or {}).get('name')} of "
            f"{(earn.get('highest') or {}).get('department')} was highest at "
            f"${(earn.get('highest') or {}).get('v'):,.0f}."
        ) if earn.get("highest") else "Named City of Boston earnings.",
        earn.get("src") or "SRC-627-01",
        "usd", "dollars",
        earn.get("note") or "City of Boston employee earnings report 2025, TOTAL GROSS.",
        n=10, span=2,
    )
    if fig:
        out.append(fig)
    trend = (sec.get("boston_payroll_trend") or {}).get("trend") or []
    if len(trend) >= 3:
        labels = [str(p["y"]) for p in trend]
        values = [p["v"] for p in trend]
        out.append(_fig(
            "bos-pay-trend",
            "City of Boston total earnings, 2015 to 2025",
            (
                f"Earnings rose from ${values[0] / 1e9:.2f} billion in {labels[0]} "
                f"to ${values[-1] / 1e9:.2f} billion in {labels[-1]}."
            ),
            "SRC-627-01",
            "line", "usd", "dollars",
            labels, _line(values, "Total earnings"),
            "Yearly CKAN dumps of the employee earnings report.",
            span=2,
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
    stc = ((sec.get("stc_ma_2025") or {}).get("ma_types")) or []
    fig = named_list(
        [t for t in stc if t.get("name") and t["name"] != "Total Taxes"],
        "stc-ma",
        "Massachusetts annual state tax collections, FY 2025",
        "Census Annual Survey of State Government Tax Collections.",
        "SRC-628-02",
        "usd", "dollars",
        "Census STC FY 2025. Amounts are published in thousands of dollars; shown in dollars.",
        n=6, span=2,
    )
    if fig:
        out.append(fig)
    return out


def figs_dl29(ledger):
    sec = _sec(ledger)
    out = []
    fig = from_snap(
        sec.get("aspep_fte_2023"), "aspep",
        title="State government FTE employment, 2023",
        skip_us=True,
        note="Census ASPEP 2023. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    stc = sec.get("stc_2025") or {}
    fig = from_snap(
        stc.get("income_share"), "stc-income-share",
        title="Individual income tax share of state collections, FY 2025",
    )
    if fig:
        out.append(fig)
    fig = from_snap(
        sec.get("aspp_holdings_2025"), "aspp-hold",
        title="Public pension cash and investments, 2025",
        skip_us=True,
        note="Census ASPP 2025 unit file, item RZ01, weighted by FINAL_WEIGHT. The U.S. total is omitted so state bars remain readable.",
    )
    if fig:
        out.append(fig)
    return out


def figs_dl30(ledger):
    sec = _sec(ledger)
    out = []
    he_rows = []
    for r in ledger.get("rows") or []:
        name = (r.get("name") or "").upper()
        if r.get("v") is None:
            continue
        if any(tok in name for tok in ("UNIVERSITY", "COMMUNITY COLLEGE", "STATE COLLEGE")):
            he_rows.append(r)
    he_rows.sort(key=lambda r: r.get("v") or 0, reverse=True)
    fig = named_list(
        he_rows, "highered-pay",
        "Massachusetts public higher-education payroll, calendar 2025",
        (
            f"{he_rows[0]['name']} was the largest public campus payroll "
            f"at ${he_rows[0]['v']:,.0f}."
        ) if he_rows else "CTHRU campus payroll.",
        "SRC-630-01",
        "usd", "dollars",
        "Departments whose published CTHRU name includes University, Community College, or State College.",
        n=8, span=2,
    )
    if fig:
        out.append(fig)
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
    sec = _sec(ledger)
    out = []
    b = sec.get("bjs_depth_2023") or {}
    fig = from_snap(
        b.get("imprisonment_rate"), "prison-rate",
        title="Imprisonment rate per 100,000 residents, 2023",
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
        span=1,
    )
    if fig:
        out.append(fig)
    return out[:2]


DISPATCH = {
    "DL-06": figs_dl06,
    "DL-07": figs_dl07,
    "DL-08": figs_dl08,
    "DL-09": figs_dl09,
    "DL-10": figs_dl10,
    "DL-11": figs_dl11,
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
    figs = [f for f in figs if f.get("type") != "map"]
    if not figs and tid not in ("DL-07", "DL-10", "DL-14", "DL-25", "DL-26", "DL-32", "DL-33"):
        fallback = from_latest(ledger)
        if fallback:
            figs = [fallback]
    return figs
