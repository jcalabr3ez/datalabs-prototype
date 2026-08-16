#!/usr/bin/env python3
"""Four audience starter questions for every live tool.

Questions are phrased for the ask box. They use only series the matching
ledger already publishes. Patents (DL-18) is in build and is omitted.
"""
from __future__ import annotations

import html

SKIP = {"DL-18"}

WHO = (
    ("public", "General public"),
    ("journalist", "Journalist"),
    ("researcher", "Researcher"),
    ("policymaker", "Policymaker"),
)

# tool_id -> {public, journalist, researcher, policymaker}
STARTERS = {
    "DL-01": {
        "public": "What is the Massachusetts top income tax rate?",
        "journalist": "Which states are considering a wealth tax?",
        "researcher": "Is Near-Term Risk a Pioneer model, and when was it last scored?",
        "policymaker": "What events should I watch on wealth and high-earner taxes?",
    },
    "DL-02": {
        "public": "What does homeowners insurance cost in Miami-Dade?",
        "journalist": "How many homes does Citizens still insure?",
        "researcher": "Does Florida publish one official statewide average premium?",
        "policymaker": "What share of nationwide homeowners lawsuits are filed in Florida?",
    },
    "DL-03": {
        "public": "Is the T back to pre-pandemic ridership?",
        "journalist": "Which MBTA mode is still furthest from June 2019 ridership?",
        "researcher": "Are MBTA ridership figures unlinked passenger trips, and why is subway reliability not on this page?",
        "policymaker": "What is MBTA farebox recovery by mode?",
    },
    "DL-04": {
        "public": "What does a household pay for electricity in the United States?",
        "journalist": "Which state has the highest residential electricity price?",
        "researcher": "Is the U.S. electricity price sales-weighted, and is it all-sector or residential?",
        "policymaker": "How do Massachusetts household electricity prices compare with the other New England states?",
    },
    "DL-05": {
        "public": "How funded is the Massachusetts Teachers retirement system?",
        "journalist": "Which Massachusetts retirement boards are the least funded?",
        "researcher": "What valuation year is the funded ratio for each Massachusetts retirement board?",
        "policymaker": "How has the State and Teacher retiree payroll changed since 2011?",
    },
    "DL-06": {
        "public": "How many students are enrolled in Massachusetts public schools?",
        "journalist": "How many Massachusetts students are in Chapter 74 vocational programs?",
        "researcher": "Is the MCAS figure the 2025 meeting-or-exceeding share for All Students?",
        "policymaker": "What share of Massachusetts students met expectations on MCAS?",
    },
    "DL-07": {
        "public": "What is the U.S. public NAEP grade 4 reading score?",
        "journalist": "Which states improved on NAEP grade 4 reading from 2019 to 2024?",
        "researcher": "Why is the high-school graduation rate on this page from 2021-22?",
        "policymaker": "How does Massachusetts per-pupil spending compare with its NAEP rank?",
    },
    "DL-08": {
        "public": "How many students are enrolled in U.S. colleges?",
        "journalist": "Which states have the highest public 4-year in-state tuition?",
        "researcher": "What share of Massachusetts graduates took the SAT, and is that the same as the national share?",
        "policymaker": "How do Massachusetts higher-education appropriations compare with in-state tuition?",
    },
    "DL-09": {
        "public": "How many students are in charter schools in the United States?",
        "journalist": "Which states have the largest charter-school enrollment?",
        "researcher": "Why is the charter ranking not out of 51 states?",
        "policymaker": "How many public-school teachers does Massachusetts employ?",
    },
    "DL-10": {
        "public": "How is Massachusetts General Hospital rated on CMS stars?",
        "journalist": "Which Massachusetts hospitals have the highest commercial relative prices?",
        "researcher": "Are CMS star ratings and CHIA relative prices from the same year?",
        "policymaker": "How many Massachusetts hospitals have a CMS overall star rating?",
    },
    "DL-11": {
        "public": "How many 340B sites are in the United States?",
        "journalist": "Which states have the most 340B contract pharmacies?",
        "researcher": "How are contract pharmacies assigned to state house districts?",
        "policymaker": "What share of hospital costs is charity care in Massachusetts?",
    },
    "DL-12": {
        "public": "How much does the United States spend on Medicaid?",
        "journalist": "Which state spends the most on Medicaid?",
        "researcher": "Is Medicaid spending on this page the state share or total-computable?",
        "policymaker": "How much did Massachusetts Medicaid fraud units recover?",
    },
    "DL-13": {
        "public": "How many new business applications were filed in the United States last month?",
        "journalist": "Did Massachusetts business applications rise or fall from a year earlier?",
        "researcher": "Are Census business applications the same as BLS establishment births?",
        "policymaker": "What is the Massachusetts establishment birth rate?",
    },
    "DL-14": {
        "public": "Which state has the highest unemployment rate?",
        "journalist": "What is the Massachusetts average weekly wage?",
        "researcher": "Is the unemployment rate seasonally adjusted, and is the wage figure from the same month?",
        "policymaker": "What is the Massachusetts labor-force participation rate?",
    },
    "DL-15": {
        "public": "What is real GDP in the United States?",
        "journalist": "Which state has the highest per capita personal income?",
        "researcher": "Is state GDP on this page in chained 2017 dollars or current dollars?",
        "policymaker": "What is Massachusetts manufacturing GDP?",
    },
    "DL-16": {
        "public": "How many housing units were authorized in the United States?",
        "journalist": "Which state authorized the most housing units?",
        "researcher": "Are housing permits completions, and is this year-to-date?",
        "policymaker": "How many housing units were authorized in Massachusetts?",
    },
    "DL-17": {
        "public": "Which state gained the most people from domestic migration?",
        "journalist": "What share of the Massachusetts population lives in metro counties?",
        "researcher": "Is domestic migration on this page the Census estimate or IRS taxpayer returns?",
        "policymaker": "What share of Massachusetts residents are age 65 and over?",
    },
    "DL-19": {
        "public": "What is the United States cost of living index?",
        "journalist": "Which state has the highest housing regional price parity?",
        "researcher": "What does a regional price parity of 100 mean?",
        "policymaker": "How does Massachusetts housing RPP compare with its all-items RPP?",
    },
    "DL-20": {
        "public": "Which state gained the most taxpayer returns?",
        "journalist": "Where did Massachusetts taxpayers move, and how many went to Florida?",
        "researcher": "Are IRS taxpayer flows the same as Census domestic migration?",
        "policymaker": "Which Massachusetts counties lost the most taxpayer returns?",
    },
    "DL-21": {
        "public": "What is adjusted gross income in the United States?",
        "journalist": "What share of Massachusetts AGI is on returns of $1 million or more?",
        "researcher": "What tax year is the AGI file, and is there a percentile-by-state table?",
        "policymaker": "Which Massachusetts county has the most AGI?",
    },
    "DL-22": {
        "public": "How many riders does the MBTA have compared with other U.S. transit agencies?",
        "journalist": "Which transit agency has the most riders?",
        "researcher": "Are these unlinked passenger trips, and is reliability on this page?",
        "policymaker": "What is FTA NTD agency operating cost and farebox recovery for the MBTA?",
    },
    "DL-23": {
        "public": "How many vehicle-miles were driven in the United States?",
        "journalist": "Which states have the highest National Risk Index scores?",
        "researcher": "Is VMT all functional systems, and is the risk score a county mean?",
        "policymaker": "How much has FEMA obligated to Massachusetts?",
    },
    "DL-24": {
        "public": "How much CO2 does the United States emit from energy?",
        "journalist": "Which states produce the most energy?",
        "researcher": "Are these EIA SEDS totals, and do they include electricity prices?",
        "policymaker": "Does Massachusetts produce more energy than it consumes?",
    },
    "DL-25": {
        "public": "What is the population of Boston?",
        "journalist": "What towns are population peers of Boston?",
        "researcher": "Are the socioeconomic peers the old Pioneer workbook?",
        "policymaker": "What is Boston median household income?",
    },
    "DL-26": {
        "public": "Is my Massachusetts town growing?",
        "journalist": "Which Massachusetts town grew the most since 2020?",
        "researcher": "Why are municipal levy and crime rankings not on this page?",
        "policymaker": "Which Massachusetts towns have the highest school spending per pupil?",
    },
    "DL-27": {
        "public": "How much is Boston city payroll?",
        "journalist": "How much is Boston Police Department payroll?",
        "researcher": "Is Boston payroll a calendar year and the operating budget a fiscal year?",
        "policymaker": "How much is the City of Boston FY26 operating appropriation?",
    },
    "DL-28": {
        "public": "How much tax did Massachusetts collect last quarter?",
        "journalist": "What share of Massachusetts tax collections is the income tax?",
        "researcher": "Is this Census QTAX or the Department of Revenue monthly report?",
        "policymaker": "How did Massachusetts tax collections change from a year earlier?",
    },
    "DL-29": {
        "public": "How much state tax did the United States collect last quarter?",
        "journalist": "Which state collected the most tax last quarter?",
        "researcher": "Are rainy-day fund totals on this page?",
        "policymaker": "How many state government employees does Massachusetts have, and how much public pension cash does Census ASPP show?",
    },
    "DL-30": {
        "public": "How much is Commonwealth payroll?",
        "journalist": "Which Commonwealth department has the largest payroll?",
        "researcher": "Is CTHRU payroll a calendar year and Comptroller spending a fiscal year?",
        "policymaker": "How much is Massachusetts quasi-public payroll?",
    },
    "DL-31": {
        "public": "How many prisoners does the United States hold?",
        "journalist": "Which state has the highest imprisonment rate?",
        "researcher": "Are youth counts on this page OJJDP custody or people 17 or younger in adult prisons?",
        "policymaker": "What is the Massachusetts imprisonment rate compared with the United States?",
    },
    "DL-32": {
        "public": "How much are the Massachusetts House Speaker and Senate President paid?",
        "journalist": "How much did Massachusetts legislators earn in 2025?",
        "researcher": "Does this file include GIC health costs or the office-expense allowance?",
        "policymaker": "What is the leadership premium over base legislator pay?",
    },
}

# Place-lens questions for fifty-state tools. {name} is the jurisdiction.
STATE_Q = {
    "DL-04": "What does a household pay for electricity in {name}?",
    "DL-06": "How many students are enrolled in {name} public schools?",
    "DL-07": "What is the {name} NAEP grade 4 reading score?",
    "DL-08": "How many students are enrolled in {name} colleges?",
    "DL-09": "How many students are in charter schools in {name}?",
    "DL-11": "How many 340B sites are in {name}?",
    "DL-12": "How much does {name} spend on Medicaid?",
    "DL-13": "How many new business applications were filed in {name} last month?",
    "DL-14": "What is the unemployment rate in {name}?",
    "DL-15": "What is real GDP in {name}?",
    "DL-16": "How many housing units were authorized in {name}?",
    "DL-17": "Is {name} gaining or losing people?",
    "DL-19": "Is {name} more expensive than the United States?",
    "DL-20": "Are taxpayers leaving {name}?",
    "DL-21": "What is adjusted gross income in {name}?",
    "DL-23": "How many vehicle-miles were driven in {name}?",
    "DL-24": "How much CO2 does {name} emit from energy?",
    "DL-29": "How much state tax did {name} collect last quarter?",
    "DL-31": "How many prisoners does {name} hold?",
}

COMPANION_JUMPS = {
    "DL-06": (
        ("Chapter 74", "#insight-ch74-seats"),
    ),
    "DL-07": (
        ("NAEP change", "#insight-naep-read4-slope"),
        ("Per-pupil spending", "#insight-npefs-ppe"),
    ),
    "DL-14": (
        ("Wages", "#insight-qcew-wage"),
        ("Participation", "#insight-lfpr"),
    ),
    "DL-15": (
        ("Industry mix", "#insight-ma-industries"),
        ("Income per person", "#insight-pcpi"),
    ),
    "DL-17": (
        ("Age 65 and over", "#insight-age65"),
        ("Metro share", "#insight-rucc"),
        ("International", "#insight-intl-mig"),
    ),
    "DL-20": (
        ("Who left Massachusetts", "#insight-ma-destinations"),
        ("County flows", "#insight-county-mig"),
    ),
    "DL-24": (
        ("Production", "#insight-seds-prod"),
        ("Consumption", "#insight-seds-cons"),
    ),
    "DL-29": (
        ("State employees", "#insight-aspep"),
        ("Pension holdings", "#insight-aspp-hold"),
        ("Income-tax share", "#insight-stc-income-share"),
    ),
}


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def starters_for(tool_id):
    if tool_id in SKIP:
        return None
    return STARTERS.get(tool_id)


def state_question(tool_id, name):
    tmpl = STATE_Q.get(tool_id)
    if not tmpl or not name:
        return ""
    return tmpl.format(name=name)


def companion_jumps(tool_id):
    return COMPANION_JUMPS.get(tool_id) or ()


def starters_html(tool_id):
    spec = starters_for(tool_id)
    if not spec:
        return ""
    chips = []
    for key, label in WHO:
        q = spec.get(key)
        if not q:
            continue
        chips.append(
            '<button type="button" class="ask-chip" data-q="'
            + esc(q)
            + '"><span class="ask-who">'
            + esc(label)
            + "</span><span class=\"ask-q\">"
            + esc(q)
            + "</span></button>"
        )
    return (
        '<section class="ask-starters" id="ask-starters" data-tool="'
        + esc(tool_id)
        + '">\n'
        '  <div class="ask-k">Ask this page</div>\n'
        '  <div class="ask-chips" role="list">'
        + "".join(chips)
        + "</div>\n"
        '  <div class="askbar">\n'
        '    <input id="toolAskQ" type="text" maxlength="400" '
        'placeholder="Ask in your own words" aria-label="Ask a question">\n'
        '    <button id="toolAskBtn" type="button">Ask</button>\n'
        "  </div>\n"
        '  <div class="ask-resp" id="toolAskResp" hidden></div>\n'
        "</section>\n"
    )
