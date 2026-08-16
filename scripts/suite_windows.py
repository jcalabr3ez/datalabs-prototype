"""Precomputed trailing-window ranks for the ask engine.

coreSlice ships these snapshots. The period cube stays on modelSlice.
Ranks cite (derived, SRC-...). Never invent a cell the file does not publish.
"""
from __future__ import annotations

from suite_common import RANKED, STATE_NAMES, fl_cell, rank_rows


def period_key(pt):
    if not isinstance(pt, dict):
        return None
    return pt.get("m") or pt.get("q") or pt.get("y")


def period_value(pt):
    if not isinstance(pt, dict):
        return None
    v = pt.get("v")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def sort_points(series):
    pts = [p for p in (series or []) if period_key(p) is not None]
    pts.sort(key=lambda p: str(period_key(p)))
    return pts


def trailing_mean(series, n, end=None):
    """Mean of the last `n` published points ending at `end` (inclusive).

    Returns (end_key, mean) or None when the window is incomplete.
    """
    pts = [p for p in sort_points(series) if period_value(p) is not None]
    if end is not None:
        end = str(end)
        pts = [p for p in pts if str(period_key(p)) <= end]
        if not pts or str(period_key(pts[-1])) != end:
            return None
    if len(pts) < n:
        return None
    window = pts[-n:]
    mean = sum(period_value(p) for p in window) / n
    return str(period_key(window[-1])), mean


def compact_rank(rec):
    if not rec:
        return None
    return {"st": rec.get("st"), "name": rec.get("name"), "v": rec.get("v"), "rank": rec.get("rank")}


def window_snapshot(values_by_st, *, src, label, end, n_periods, unit,
                    us_val=None, higher_is_better=True, window_id=None):
    """Compact rank snapshot for one trailing window."""
    ranked = rank_rows(values_by_st, higher_is_better=higher_is_better)
    if not ranked:
        return None
    ma = next((r for r in ranked if r.get("st") == "MA"), None)
    if not ma:
        return None
    hi, lo = ranked[0], ranked[-1]
    out = {
        "id": window_id,
        "label": label,
        "src": src,
        "unit": unit,
        "end": end,
        "n_periods": n_periods,
        "higher_is_better": higher_is_better,
        "us": us_val,
        "ma": {"v": ma["v"], "rank": ma["rank"], "n": ma["n"]},
        "highest": {"st": hi["st"], "name": hi["name"], "v": hi["v"]},
        "lowest": {"st": lo["st"], "name": lo["name"], "v": lo["v"]},
        "n_ranked": ma["n"],
        "ranked": [{"st": r["st"], "v": r["v"], "rank": r["rank"]} for r in ranked],
    }
    fl = fl_cell(ranked)
    if fl:
        out["fl"] = fl
    out["rows"] = [
        {"st": r["st"], "name": r["name"], "v": r["v"], "rank": r["rank"], "n": r["n"]}
        for r in ranked
    ]
    if window_id:
        out["id"] = window_id
    return out


def windows_from_trend(trend, *, src, unit, ns, label_stem, higher_is_better=True,
                       named_ends=None, prefix="headline"):
    """Build trailing-window snapshots from a {st: [{m|q|y, v}, ...]} cube.

    `ns` is a list of period counts (for example [4, 9] or [12]).
    `named_ends` is an optional list of period keys to pin, besides the latest.
    """
    if not isinstance(trend, dict) or "MA" not in trend:
        return {}
    pts_ma = sort_points(trend.get("MA"))
    if not pts_ma:
        return {}
    latest_end = str(period_key(pts_ma[-1]))
    ends = [latest_end]
    for e in named_ends or []:
        e = str(e)
        if e not in ends:
            ends.append(e)
    out = {}
    for n in ns:
        for end in ends:
            values = {}
            us_val = None
            for st, series in trend.items():
                got = trailing_mean(series, n, end=end)
                if not got:
                    continue
                _, mean = got
                mean = round(mean, 4)
                if st == "US":
                    us_val = mean
                elif st in RANKED:
                    values[st] = mean
            if "MA" not in values or len(values) < 40:
                continue
            for st, v in list(values.items()):
                values[st] = round(v, 2) if abs(v) >= 1 else round(v, 3)
            if us_val is not None:
                us_val = round(us_val, 2) if abs(us_val) >= 1 else round(us_val, 3)
            end_slug = str(end).lower().replace(" ", "").replace("-", "")
            wid = f"{prefix}_t{n}_{end_slug}"
            label = f"{label_stem}, trailing {n} periods ending {end}"
            snap = window_snapshot(
                values, src=src, label=label, end=end, n_periods=n,
                unit=unit, us_val=us_val, higher_is_better=higher_is_better,
                window_id=wid,
            )
            if snap:
                out[wid] = snap
    return out


def attach_windows(ledger, windows, note=None):
    """Merge window snapshots onto ledger.derived.windows."""
    if not windows:
        return ledger
    derived = ledger.setdefault("derived", {})
    bucket = derived.setdefault("windows", {})
    if note:
        bucket["note"] = note
    elif "note" not in bucket:
        bucket["note"] = (
            "Prefer these over recomputing. Window means and ranks cite "
            "(derived) plus the source id on each snapshot."
        )
    for key, snap in windows.items():
        if snap:
            bucket[key] = snap
    return ledger


def slim_note():
    return (
        "Prefer latest and derived.windows over recomputing. "
        "Ranks and trailing-window means cite (derived) plus the source id."
    )
