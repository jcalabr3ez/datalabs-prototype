#!/usr/bin/env python3
"""Compile household electricity prices and IRS taxpayer pair flows.

Patches the existing DL-04 and DL-20 ledgers. Does not rebuild flagship
cells that are already verified. Does not touch DL-01 or DL-02.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_dl04 import URL_HS861, attach_sector_prices, fetch, load_hs861
from suite_common import ROOT
from suite_later import commify, sec_state_pair_flows

DL04 = ROOT / "netlify" / "functions" / "dl04-answers.json"
DL20 = ROOT / "netlify" / "functions" / "dl20-answers.json"


def patch_dl04():
    ledger = json.loads(DL04.read_text(encoding="utf-8"))
    us_all = ((ledger.get("latest") or {}).get("us") or {}).get("price_cents")
    hs861 = load_hs861(fetch(URL_HS861))
    year = ledger.get("data_year")
    got = (hs861.get((year, "US")) or {}).get("price_cents")
    if us_all is None or got is None or abs(got - us_all) > 0.011:
        sys.exit(f"FATAL: HS861 U.S. total {got} != ledger {us_all}")
    attach_sector_prices(ledger, hs861)
    ledger.setdefault("page", {})["revised"] = "Aug 16, 2026"
    src401 = (ledger.get("source_id_map") or {}).get("SRC-401") or {}
    if src401.get("what") and "residential" not in src401["what"].lower():
        src401["what"] = (
            "All-sector, residential, commercial, and industrial average "
            "retail prices (cents per kWh) and retail sales (MWh) by state, "
            "including the U.S. Total row"
        )
    DL04.write_text(json.dumps(ledger, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")
    res = (ledger.get("latest") or {}).get("residential") or {}
    print(
        "DL-04 residential "
        f"US {res.get('us', {}).get('price_cents')} "
        f"MA {res.get('ma', {}).get('price_cents')} "
        f"rank {res.get('ma', {}).get('rank')}"
    )


def _append_lead(lead, sentence):
    lead = " ".join((lead or "").split())
    marker = sentence[:48]
    if marker and marker in lead:
        return lead
    return (lead + " " + sentence).strip()


def patch_dl20():
    ledger = json.loads(DL20.read_text(encoding="utf-8"))
    pairs = sec_state_pair_flows()
    sec = ledger.setdefault("derived", {}).setdefault("secondary", {})
    sec["state_pair_flows_2022_23"] = pairs
    ma_fl = pairs["ma_to_fl"]
    top = (pairs.get("ma_out_top") or [{}])[0]
    sentence = (
        f"The largest destination for Massachusetts filers was "
        f"<b>{top.get('name')}</b> at <b>{commify(top.get('returns'))}</b> "
        f"returns"
        + (
            ""
            if top.get("st") == "FL"
            else f". Massachusetts to Florida was <b>{commify(ma_fl['returns'])}</b> returns"
        )
        + " (SRC-620-01)."
    )
    ledger["lead"] = _append_lead(ledger.get("lead"), sentence)
    scope = ledger.get("scope") or ""
    if "origin-destination" not in scope.lower() and "destination" not in scope.lower():
        ledger["scope"] = (
            scope.rstrip(".")
            + ", and origin-destination pair flows from the same IRS SOI "
            "state files (including Massachusetts to Florida)."
        )
    ledger.setdefault("page", {})["revised"] = "Aug 16, 2026"
    note = ledger.get("vintage_note") or ""
    if "pair" not in note.lower():
        ledger["vintage_note"] = (
            note.rstrip(".")
            + ". Origin-destination pairs compiled Aug 16, 2026 from "
            "stateoutflow2223.csv."
        )
    DL20.write_text(json.dumps(ledger, ensure_ascii=True, indent=1) + "\n", encoding="utf-8")
    print(
        "DL-20 pairs "
        f"MA->FL {ma_fl.get('returns')} "
        f"top {top.get('st')} {top.get('returns')}"
    )


def main():
    patch_dl04()
    patch_dl20()


if __name__ == "__main__":
    main()
