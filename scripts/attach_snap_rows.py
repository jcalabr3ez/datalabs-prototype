#!/usr/bin/env python3
"""Attach full jurisdiction rows to companion snaps that only kept highlights.

Does not rebuild namesake rankings. Does not touch DL-01 or DL-02.
When a fresh builder snap matches the published highlights, only `rows`
is copied onto the existing object.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from suite_common import LEDGER_DIR, STATE_NAMES, ledger_path, load_apps

SKIP = {"DL-01", "DL-02"}


def tool_id_from_path(path):
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    return f"DL-{int(digits):02d}"


def looks_like_snap(obj):
    if not isinstance(obj, dict) or not (obj.get("ma") or obj.get("highest")):
        return False
    n = obj.get("n_ranked")
    if isinstance(n, int) and n >= 40:
        return True
    ma = obj.get("ma")
    return isinstance(ma, dict) and isinstance(ma.get("n"), int) and ma["n"] >= 40


def cell_v(node):
    if isinstance(node, dict):
        return node.get("v")
    return node


def rows_from_list(items, n_ranked=None):
    rows = []
    for r in items or []:
        if not isinstance(r, dict) or r.get("st") is None or r.get("v") is None:
            continue
        st = r["st"]
        rows.append({
            "st": st,
            "name": r.get("name") or STATE_NAMES.get(st, st),
            "v": r["v"],
            "rank": r.get("rank"),
            "n": r.get("n") or n_ranked,
        })
    return rows


def fill_from_local(obj, stats):
    if not isinstance(obj, dict):
        return
    if looks_like_snap(obj):
        existing = obj.get("rows") or []
        if len(existing) < 40:
            src = obj.get("ranked") or obj.get("states") or []
            rows = rows_from_list(src, obj.get("n_ranked"))
            if len(rows) >= 40:
                obj["rows"] = rows
                stats["local"] += 1
    for v in obj.values():
        if isinstance(v, dict):
            fill_from_local(v, stats)
        elif isinstance(v, list) and len(v) < 20:
            for item in v:
                if isinstance(item, dict):
                    fill_from_local(item, stats)


def snap_n(obj):
    n = obj.get("n_ranked")
    if isinstance(n, int):
        return n
    ma = obj.get("ma")
    if isinstance(ma, dict) and isinstance(ma.get("n"), int):
        return ma["n"]
    return None


def highlights_match(old, new):
    if not looks_like_snap(old) or not looks_like_snap(new):
        return False
    if snap_n(old) != snap_n(new):
        return False
    if cell_v(old.get("ma")) != cell_v(new.get("ma")):
        return False
    if (old.get("highest") or {}).get("st") != (new.get("highest") or {}).get("st"):
        return False
    if cell_v(old.get("highest")) != cell_v(new.get("highest")):
        return False
    return True


def merge_rows(old, new, stats, path):
    if looks_like_snap(old) and looks_like_snap(new) and new.get("rows"):
        if len(old.get("rows") or []) < 40:
            if highlights_match(old, new):
                old["rows"] = new["rows"]
                if old.get("n_ranked") is None and new.get("n_ranked") is not None:
                    old["n_ranked"] = new["n_ranked"]
                if old.get("fl") is None and new.get("fl") is not None:
                    old["fl"] = new["fl"]
                stats["merged"] += 1
                stats["paths"].append(path)
            else:
                stats["mismatch"].append(
                    f"{path} old_ma={cell_v(old.get('ma'))} new_ma={cell_v(new.get('ma'))}"
                )
    if not isinstance(old, dict) or not isinstance(new, dict):
        return
    for k, nv in new.items():
        if k in old:
            merge_rows(old[k], nv, stats, f"{path}.{k}" if path else k)


def load_ledger(tid):
    path = ledger_path(tid)
    return path, json.loads(path.read_text(encoding="utf-8"))


def write_ledger(path, data):
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def apply_fresh(tid, fresh, stats):
    path, data = load_ledger(tid)
    if data.get("status") != "live":
        return
    derived = data.setdefault("derived", {})
    existing = derived.setdefault("secondary", {})
    merge_rows(existing, fresh, stats, f"{tid}.secondary")
    write_ledger(path, data)


def main():
    stats = {"local": 0, "merged": 0, "mismatch": [], "paths": [], "errors": []}

    for path in sorted(LEDGER_DIR.glob("dl*-answers.json")):
        tid = tool_id_from_path(path)
        if tid in SKIP:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        fill_from_local(data, stats)
        write_ledger(path, data)
    print(f"local rows attached: {stats['local']}", flush=True)

    print("fetch DL-14 LAUS 2026-06 ...", flush=True)
    try:
        from suite_hollow import sec_laus_labor
        apply_fresh("DL-14", {"laus_labor_2026": sec_laus_labor(pin=(2026, 6))}, stats)
    except Exception as e:
        stats["errors"].append(f"DL-14 LAUS: {e}")
        traceback.print_exc()

    try:
        from suite_later import SECONDARY
        from suite_public_later import MORE_SECONDARY
    except Exception as e:
        stats["errors"].append(f"import builders: {e}")
        traceback.print_exc()
        print(json.dumps(stats, indent=2))
        return

    for source in (SECONDARY, MORE_SECONDARY):
        for tid, fn in source.items():
            if tid in SKIP:
                continue
            print(f"fetch {tid} ...", flush=True)
            try:
                apply_fresh(tid, fn(), stats)
            except Exception as e:
                stats["errors"].append(f"{tid}: {e}")
                traceback.print_exc()

    print(json.dumps({
        "local": stats["local"],
        "merged": stats["merged"],
        "mismatch": stats["mismatch"],
        "paths": stats["paths"],
        "errors": stats["errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
