#!/usr/bin/env python3
"""Inventory every live tool's published claims and charts.

This is the deterministic half of the overnight platform audit. It does not
fetch publisher files and it does not invent figures. It walks the catalog,
recomputes ranks from published rows, checks generated prose against ledger
cells, and lists later-view series that have numbers but no insight chart.

Write a JSON report (and optional markdown) for the Cursor Automation in
scripts/platform-audit-pass.md. Exit 0 unless --strict is set and a hard
failure remains.

Do not fold this into a DL-01, DL-02, DL-05, or suite-refresh pull request.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from insight_figures import insight_figures  # noqa: E402
from page_voice import (  # noqa: E402
    SKIP_VOICE,
    flagship_voice,
    uses_national_lens,
    voice_for,
)
from suite_common import ledger_path, load_apps  # noqa: E402

# Same exceptions as render_suite_pages: finder, town, hist, and tools
# whose Figure 1 already carries the namesake series.
SKIP_INSIGHT_REQUIRED = {
    "DL-07", "DL-10", "DL-16", "DL-25", "DL-26", "DL-32", "DL-33",
}
FLAGSHIP_SLUG = {
    "DL-01": "tax-atlas",
    "DL-02": "florida-insurance",
    "DL-03": "mbta",
    "DL-04": "electricity",
    "DL-05": "pensions",
}
VERTICALS = {
    "Education": ["DL-06", "DL-07", "DL-08", "DL-09"],
    "Healthcare": ["DL-10", "DL-11", "DL-12", "DL-33"],
    "Economic Opportunity": [
        "DL-13", "DL-14", "DL-15", "DL-16", "DL-17", "DL-18", "DL-19", "DL-04",
    ],
    "Citizenship: tax and payroll": [
        "DL-01", "DL-20", "DL-21", "DL-28", "DL-29", "DL-05", "DL-27", "DL-30", "DL-32",
    ],
    "Citizenship: place and infrastructure": [
        "DL-02", "DL-03", "DL-22", "DL-23", "DL-24", "DL-25", "DL-26", "DL-31",
    ],
}
SRC_RE = re.compile(r"SRC-[A-Z0-9]+(?:-[A-Z0-9]+)*")
BOLD_RE = re.compile(r"<b>(.*?)</b>", re.I | re.S)
YEAR_OK = set(range(1990, 2036))
SKIP_KEYS = {
    "url", "scope", "exclusions", "vintage_note", "heritage", "note",
    "q", "supports", "cite", "link", "html", "prompt",
}
LIMIT_MARKERS = (
    "remain pending",
    "not published",
    "not posted",
    "not in this",
    "not a published",
    "listed as a later view",
    "stay pending",
    "keep declining",
)


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text or "")


def parse_display_number(text):
    """Turn a published fragment into a float. None when it is not a figure."""
    raw = strip_tags(text).replace("\u2212", "-").replace("\xa0", " ").strip()
    if not raw or raw.lower() in ("derived", "n/a", "na"):
        return None
    m = re.search(
        r"(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)\s*(trillion|billion|million)",
        raw,
        re.I,
    )
    if m:
        scale = {"trillion": 1e12, "billion": 1e9, "million": 1e6}[m.group(2).lower()]
        return float(m.group(1).replace(",", "")) * scale
    m = re.search(
        r"(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d+|-?\d+)",
        raw.replace("$", ""),
    )
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def close_to(a, b, rel=0.0025, abs_tol=0.08):
    if a is None or b is None:
        return False
    if abs(a - b) <= abs_tol:
        return True
    if b != 0 and abs(a - b) / abs(b) <= rel:
        return True
    for scale in (1e3, 1e6, 1e9, 1e12):
        if abs(a * scale - b) <= max(abs_tol * scale, abs(b) * rel):
            return True
        if abs(b * scale - a) <= max(abs_tol * scale, abs(a) * rel):
            return True
    return False


def collect_numbers(obj, out, skip_text=True):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append(float(obj))
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if skip_text and k in SKIP_KEYS:
                continue
            collect_numbers(v, out, skip_text=skip_text)
        return
    if isinstance(obj, list):
        for item in obj:
            collect_numbers(item, out, skip_text=skip_text)


def known_source_ids(ledger):
    ids = set((ledger.get("source_id_map") or {}).keys())
    for key in ("source_id", "cost_source_id"):
        val = ledger.get(key)
        if isinstance(val, str) and val.startswith("SRC-"):
            ids.add(val)
    for match in SRC_RE.findall(json.dumps(ledger.get("source_id_map") or {})):
        ids.add(match)

    def walk(node):
        if isinstance(node, dict):
            src = node.get("src") or node.get("source_id")
            if isinstance(src, str) and src.startswith("SRC-"):
                ids.add(src)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(ledger.get("derived") or {})
    walk(ledger.get("latest") or {})
    return ids


def catalog_tools():
    catalog = load_json("catalog.json")
    apps = {a["id"]: a for a in load_apps()}
    out = []
    for row in catalog:
        tid = row.get("id")
        if not isinstance(tid, str) or not tid.startswith("DL-"):
            continue
        app = apps.get(tid) or {
            "id": tid,
            "slug": FLAGSHIP_SLUG.get(tid) or (row.get("url") or "").strip("/"),
            "title": row.get("t") or tid,
            "wave": "live" if row.get("st") == "live" else "build",
            "vertical": row.get("group") or "",
        }
        out.append((tid, row, app))
    return out


def page_path(tid, app):
    slug = FLAGSHIP_SLUG.get(tid) or app.get("slug")
    if not slug:
        return None
    return ROOT / slug / "index.html"


def skip_claim_number(n, fragment):
    if n is None:
        return True
    low = (fragment or "").lower()
    if n == int(n) and int(n) in YEAR_OK and "$" not in fragment and "%" not in fragment:
        if "rank" in low or "of " in low or re.search(r"\b(19|20)\d{2}\b", fragment):
            if abs(n) < 2100:
                return True
    if "rank" in low and 1 <= n <= 60 and n == int(n):
        return True
    return False


def extract_bold_claims(text):
    claims = []
    for m in BOLD_RE.finditer(text or ""):
        frag = m.group(1)
        n = parse_display_number(frag)
        if n is None or skip_claim_number(n, frag):
            continue
        claims.append({"text": strip_tags(frag).strip(), "v": n})
    return claims


def extract_lede_numbers(text):
    claims = []
    cleaned = SRC_RE.sub("", text or "")
    cleaned = re.sub(r"\b(?:19|20)\d{2}-\d{2}\b", " ", cleaned)
    for m in re.finditer(
        r"(?<![\d.])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d+|-\d+|\d+)(?:\s*(trillion|billion|million))?",
        cleaned.replace("$", ""),
        re.I,
    ):
        n = float(m.group(1).replace(",", ""))
        if m.group(2):
            n *= {"trillion": 1e12, "billion": 1e9, "million": 1e6}[m.group(2).lower()]
        frag = m.group(0)
        if skip_claim_number(n, frag):
            continue
        claims.append({"text": frag.strip(), "v": n})
    return claims


def number_in_pool(n, pool):
    return any(close_to(n, x) for x in pool)


def fig_values(fig):
    vals = []
    for series in fig.get("series") or []:
        if isinstance(series, dict):
            collect_numbers(series.get("data"), vals, skip_text=False)
        else:
            collect_numbers(series, vals, skip_text=False)
    collect_numbers(fig.get("rows"), vals, skip_text=False)
    return vals


def is_pending_snap(snap):
    if not isinstance(snap, dict):
        return True
    if snap.get("pending") is True:
        return True
    text = " ".join(str(snap.get(k) or "") for k in ("note", "label", "status", "lede"))
    low = text.lower()
    return any(m in low for m in LIMIT_MARKERS) and not is_chartable(snap, require_numbers=True)


def is_chartable(snap, require_numbers=False):
    if not isinstance(snap, dict):
        return False
    trend = snap.get("trend") or []
    if isinstance(trend, list) and len(trend) >= 3:
        return True
    rows = snap.get("rows") or snap.get("district_rows") or []
    scored = [r for r in rows if isinstance(r, dict) and r.get("v") is not None]
    if len(scored) >= 3:
        return True
    ma = snap.get("ma")
    ma_v = ma.get("v") if isinstance(ma, dict) else ma
    us = snap.get("us")
    us_v = us.get("v") if isinstance(us, dict) else us
    hi = (snap.get("highest") or {}).get("v") if isinstance(snap.get("highest"), dict) else None
    if ma_v is not None and (us_v is not None or hi is not None):
        return True
    if require_numbers:
        return False
    return False


def recommend_chart(snap):
    trend = snap.get("trend") or []
    if isinstance(trend, list) and len(trend) >= 3:
        return "line of the published trend"
    rows = snap.get("rows") or []
    if any(isinstance(r, dict) and r.get("from") is not None and r.get("to") is not None for r in rows):
        return "slope of the two published years"
    if len(rows) >= 40:
        return "from_snap bar of MA, FL, high, and low (hex map is Figure 1 when the file is fifty-state)"
    if snap.get("ma") is not None:
        return "from_snap bar of the published cells"
    return "named_list bar of the published rows"


def fig_covers_snap(fig, key, snap):
    snap_vals = []
    collect_numbers(snap, snap_vals)
    overlap = sum(1 for v in fig_values(fig) if number_in_pool(v, snap_vals))
    if overlap >= 2:
        return True
    blob = " ".join(
        str(x or "") for x in (fig.get("id"), fig.get("title"), fig.get("lede"), fig.get("src"))
    ).lower()
    tokens = [t for t in re.findall(r"[a-z0-9]{4,}", key.lower()) if t not in ("from", "with", "that")]
    if tokens and sum(1 for t in tokens if t in blob) >= max(1, len(tokens) // 2):
        return True
    label = str(snap.get("label") or "").lower()
    words = [w for w in re.findall(r"[a-z]{5,}", label) if w not in ("united", "states", "public")]
    if words and sum(1 for w in words if w in blob) >= 2:
        return True
    return False


def _ranks_monotonic(scored, higher_is_better):
    """True when a strictly better value always has a strictly better rank.

    Ties may use competition or sequential ranks; those are not failures.
    """
    for a in scored:
        for b in scored:
            if a is b:
                continue
            if a["v"] == b["v"]:
                continue
            a_better = a["v"] > b["v"] if higher_is_better else a["v"] < b["v"]
            if a_better and a["rank"] > b["rank"]:
                return False
    return True


def check_rank_table(rows, where):
    scored = [
        r for r in (rows or [])
        if isinstance(r, dict) and r.get("v") is not None and r.get("rank") is not None
    ]
    if len(scored) < 8:
        return None
    if _ranks_monotonic(scored, True) or _ranks_monotonic(scored, False):
        return None
    sample = []
    ordered = sorted(scored, key=lambda r: r["v"], reverse=True)
    for i, r in enumerate(ordered[:6]):
        label = r.get("st") or r.get("name") or "?"
        sample.append(f"{label} v={r['v']} rank={r['rank']}")
    return f"{where}: ranks are not monotonic in either direction ({'; '.join(sample)})"


def tool_voice(tid, app, ledger):
    if tid in SKIP_VOICE:
        return None
    if tid in FLAGSHIP_SLUG and tid not in {a["id"] for a in load_apps()}:
        if tid in ("DL-03", "DL-04", "DL-05"):
            return flagship_voice(tid, ledger)
        return None
    if app.get("id") in {a["id"] for a in load_apps()}:
        return voice_for(app, ledger)
    if tid in ("DL-03", "DL-04", "DL-05"):
        return flagship_voice(tid, ledger)
    return None


def audit_tool(tid, row, app):
    rec = {
        "id": tid,
        "title": app.get("title") or row.get("t") or tid,
        "slug": FLAGSHIP_SLUG.get(tid) or app.get("slug"),
        "wave": app.get("wave") or row.get("st") or "",
        "status": None,
        "failures": [],
        "gaps": [],
        "notes": [],
        "claims": 0,
        "claim_misses": 0,
        "figures": [],
        "uncharted": [],
    }
    path = ledger_path(tid)
    page = page_path(tid, app)
    if not path.exists():
        rec["failures"].append("missing ledger")
        return rec
    ledger = json.loads(path.read_text(encoding="utf-8"))
    rec["status"] = ledger.get("status") or app.get("wave")
    rec["as_of"] = ledger.get("as_of")
    if rec["status"] in ("build", "pending") or app.get("wave") == "build":
        rec["notes"].append("stub or in-build; no live claim audit")
        return rec
    if ledger.get("status") != "live":
        rec["notes"].append(f"ledger status {ledger.get('status')}")
        return rec
    if page is None or not page.exists():
        rec["failures"].append("missing page")
        return rec
    html = page.read_text(encoding="utf-8")

    pool = []
    collect_numbers(ledger, pool)
    src_ids = known_source_ids(ledger)

    rank_err = check_rank_table(ledger.get("rows"), "latest rows")
    if rank_err:
        rec["failures"].append(rank_err)
    latest = ledger.get("latest") or {}
    if isinstance(latest.get("states"), list):
        rank_err = check_rank_table(latest.get("states"), "latest.states")
        if rank_err:
            rec["failures"].append(rank_err)
    sec = (ledger.get("derived") or {}).get("secondary") or {}
    for key, snap in sec.items():
        if not isinstance(snap, dict):
            continue
        rank_err = check_rank_table(snap.get("rows"), f"secondary.{key}")
        if rank_err:
            rec["failures"].append(rank_err)

    voice = tool_voice(tid, app, ledger)
    prose_bits = []
    if voice:
        answer = voice.get("answer") or {}
        if not (answer.get("value") or "").strip() and tid != "DL-01":
            rec["failures"].append("empty hero number")
        hero_v = parse_display_number(answer.get("value") or "")
        if hero_v is not None and pool and not number_in_pool(hero_v, pool):
            rec["failures"].append(f"hero {answer.get('value')!r} is not a ledger cell")
        cat_ma = row.get("ma") or ""
        voice_ma = voice.get("ma") or ""
        if cat_ma and voice_ma and cat_ma != voice_ma:
            rec["failures"].append("catalog ma line does not match generated voice")
        for take in voice.get("takeaways") or []:
            prose_bits.append(take)
        lead = voice.get("lead") or voice.get("page_lead") or ""
        if lead:
            prose_bits.append(lead)
        for kpi in voice.get("kpis") or []:
            if isinstance(kpi, dict):
                prose_bits.append(str(kpi.get("v") or ""))
                prose_bits.append(str(kpi.get("note") or ""))
    if ledger.get("lead"):
        prose_bits.append(str(ledger.get("lead")))

    figs = []
    if tid not in SKIP_VOICE and app.get("id") in {a["id"] for a in load_apps()}:
        figs = insight_figures(app, ledger)
    rec["figures"] = [
        {
            "id": f.get("id"),
            "title": f.get("title"),
            "type": f.get("type"),
            "src": f.get("src"),
            "n": len(fig_values(f)),
        }
        for f in figs
    ]
    if (
        tid not in SKIP_INSIGHT_REQUIRED
        and tid not in FLAGSHIP_SLUG
        and not figs
    ):
        rec["gaps"].append("no insight figures; add charts from existing ledger cells")
    for fig in figs:
        vals = fig_values(fig)
        if not vals:
            rec["failures"].append(f"insight {fig.get('id')} has an empty series")
        src = fig.get("src") or ""
        if src.startswith("SRC-") and src_ids and src not in src_ids:
            rec["failures"].append(f"insight {fig.get('id')} cites unknown {src}")
        for claim in extract_lede_numbers(fig.get("lede") or ""):
            rec["claims"] += 1
            if not number_in_pool(claim["v"], vals + pool):
                rec["claim_misses"] += 1
                rec["gaps"].append(
                    f"figure {fig.get('id')} lede {claim['text']!r} is not in the series or ledger"
                )
        prose_bits.append(fig.get("lede") or "")
        prose_bits.append(fig.get("note") or "")

    for bit in prose_bits:
        for sid in SRC_RE.findall(bit):
            if src_ids and sid not in src_ids and tid not in ("DL-01", "DL-02", "DL-03"):
                rec["failures"].append(f"prose cites unknown {sid}")
        for claim in extract_bold_claims(bit):
            rec["claims"] += 1
            if pool and not number_in_pool(claim["v"], pool):
                rec["claim_misses"] += 1
                rec["gaps"].append(f"bold claim {claim['text']!r} is not a ledger cell")

    namesake = (ledger.get("metric") or "").lower()
    namesake_label = (ledger.get("metric_label") or "").lower()
    for key, snap in sec.items():
        if not isinstance(snap, dict) or not is_chartable(snap):
            continue
        if is_pending_snap(snap) and not is_chartable(snap, require_numbers=True):
            continue
        if key.lower() in namesake or (namesake_label and namesake_label in str(snap.get("label") or "").lower()):
            continue
        if any(fig_covers_snap(f, key, snap) for f in figs):
            continue
        rec["uncharted"].append({
            "key": key,
            "label": snap.get("label") or key,
            "recommend": recommend_chart(snap),
            "src": snap.get("src") or "",
        })
        rec["gaps"].append(
            f"secondary.{key} has published cells but no insight chart ({recommend_chart(snap)})"
        )

    if uses_national_lens(tid, ledger):
        if 'id="chRank"' not in html or "hex" not in html:
            rec["failures"].append("national-lens page is missing hex Figure 1")
    if tid == "DL-01":
        if 'id="chRank"' not in html:
            rec["failures"].append("tax-atlas is missing hex Figure 1")
        captions = ledger.get("captions") or {}
        if not (captions.get("current") or "").strip():
            rec["failures"].append("tax-atlas current caption is empty")
    if tid == "DL-02":
        if 'id="answerQ"' not in html:
            rec["failures"].append("florida-insurance is missing the finding hero")

    rec["failures"] = sorted(set(rec["failures"]))
    rec["gaps"] = sorted(set(rec["gaps"]))
    return rec


def render_markdown(report):
    lines = [
        f"# Platform audit {report['as_of']}",
        "",
        "Deterministic pass. Does not fetch publisher files. Does not invent figures.",
        "",
        f"Tools audited: **{report['n_tools']}**. "
        f"Live: **{report['n_live']}**. "
        f"Hard failures: **{report['n_failures']}**. "
        f"Chart or claim gaps: **{report['n_gaps']}**.",
        "",
        "## Failures (fix from the ledger, do not invent)",
        "",
    ]
    fails = [t for t in report["tools"] if t["failures"]]
    if not fails:
        lines.append("None.")
        lines.append("")
    else:
        for t in fails:
            lines.append(f"### {t['id']} {t['title']}")
            for f in t["failures"]:
                lines.append(f"- {f}")
            lines.append("")
    lines += ["## Chart and claim gaps (existing cells only)", ""]
    gaps = [t for t in report["tools"] if t["gaps"] or t["uncharted"]]
    if not gaps:
        lines.append("None.")
    else:
        for t in gaps:
            lines.append(f"### {t['id']} {t['title']}")
            for g in t["gaps"]:
                lines.append(f"- {g}")
            lines.append("")
    lines += ["## By vertical", ""]
    for name, ids in VERTICALS.items():
        subset = [t for t in report["tools"] if t["id"] in ids]
        n_fail = sum(len(t["failures"]) for t in subset)
        n_gap = sum(len(t["gaps"]) for t in subset)
        lines.append(f"- **{name}**: {len(subset)} tools, {n_fail} failures, {n_gap} gaps")
    lines += [
        "",
        "## Stubs",
        "",
    ]
    stubs = [t for t in report["tools"] if t.get("status") in ("build", "pending") or "stub" in " ".join(t.get("notes") or [])]
    if not stubs:
        lines.append("None.")
    else:
        for t in stubs:
            lines.append(f"- {t['id']} {t['title']}: {'; '.join(t.get('notes') or [t.get('status') or 'build'])}")
    lines += [
        "",
        "## Deploy",
        "",
        "Draft PR only. Title must start with `Platform audit`. "
        "Do not merge. Do not push main. Do not fold into a DL-01, DL-02, DL-05, or suite-refresh PR.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_path", help="Write the JSON report here")
    parser.add_argument("--md", dest="md_path", help="Write the markdown report here")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when a hard failure remains")
    parser.add_argument("--tool", action="append", help="Limit to one or more tool ids")
    args = parser.parse_args()

    wanted = set(args.tool or [])
    tools = []
    for tid, row, app in catalog_tools():
        if wanted and tid not in wanted:
            continue
        tools.append(audit_tool(tid, row, app))

    n_fail = sum(len(t["failures"]) for t in tools)
    n_gap = sum(len(t["gaps"]) for t in tools)
    n_live = sum(1 for t in tools if t.get("status") == "live")
    report = {
        "as_of": date.today().isoformat(),
        "n_tools": len(tools),
        "n_live": n_live,
        "n_failures": n_fail,
        "n_gaps": n_gap,
        "verticals": VERTICALS,
        "tools": tools,
    }

    md = render_markdown(report)
    print(md)
    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")
    if args.md_path:
        out = Path(args.md_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md + "\n", encoding="utf-8")
        print(f"wrote {out}")

    if args.strict and n_fail:
        print(f"\nplatform audit: {n_fail} hard failure(s)", file=sys.stderr)
        return 1
    print(f"\nplatform audit: {n_live} live tools, {n_fail} failures, {n_gap} gaps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
