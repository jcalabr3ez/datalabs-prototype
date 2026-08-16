#!/usr/bin/env python3
"""Four audience starter questions for every live tool except DL-01 and DL-02.

Questions are phrased for the ask box. They use only series the matching
ledger already publishes (or will publish after the residential-price and
taxpayer-pair compiles). Patents (DL-18) is in build and is omitted.
"""
from __future__ import annotations

import html

SKIP = {"DL-01", "DL-02", "DL-18"}

WHO = (
    ("public", "General public"),
    ("journalist", "Journalist"),
    ("researcher", "Researcher"),
    ("policymaker", "Policymaker"),
)

# tool_id -> {public, journalist, researcher, policymaker}
STARTERS = {
    "DL-03": {
        "public": "Is the T back to pre-pandemic ridership?",
        "journalist": "Which MBTA mode is still furthest from June 2019 ridership?",
        "researcher": "Are MBTA ridership figures unlinked passenger trips, and why is subway reliability not on this page?",
        "policymaker": "What is MBTA farebox recovery by mode?",
    },
    "DL-04": {
        "public": "What does a household pay for electricity in Massachusetts?",
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
        "public": "What share of Massachusetts students met expectations on MCAS?",
        "journalist": "Which Massachusetts districts spend the most per pupil?",
        "researcher": "Is the MCAS figure the 2025 meeting-or-exceeding share for All Students?",
        "policymaker": "How many Massachusetts students are in Chapter 74 vocational programs?",
    },
    "DL-07": {
        "public": "What is the Massachusetts NAEP grade 4 reading score?",
        "journalist": "Which states improved on NAEP grade 4 reading from 2019 to 2024?",
        "researcher": "Why is the high-school graduation rate on this page from 2021-22?",
        "policymaker": "How does Massachusetts per-pupil spending compare with its NAEP rank?",
    },
    "DL-08": {
        "public": "What is public 4-year in-state tuition in Massachusetts?",
        "journalist": "Which states have the highest public 4-year in-state tuition?",
        "researcher": "What share of Massachusetts graduates took the SAT, and is that the same as the national share?",
        "policymaker": "How do Massachusetts higher-education appropriations compare with in-state tuition?",
    },
    "DL-09": {
        "public": "How many students are in charter schools in Massachusetts?",
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
        "public": "How many 340B sites are in Massachusetts?",
        "journalist": "Which states have the most 340B contract pharmacies?",
        "researcher": "How are contract pharmacies assigned to state house districts?",
        "policymaker": "What share of hospital costs is charity care in Massachusetts?",
    },
    "DL-12": {
        "public": "How much does Massachusetts spend on Medicaid?",
        "journalist": "Which state spends the most on Medicaid?",
        "researcher": "Is Medicaid spending on this page the state share or total-computable?",
        "policymaker": "How much did Massachusetts Medicaid fraud units recover?",
    },
    "DL-13": {
        "public": "How many new business applications were filed in Massachusetts last month?",
        "journalist": "Did Massachusetts business applications rise or fall from a year earlier?",
        "researcher": "Are Census business applications the same as BLS establishment births?",
        "policymaker": "What is the Massachusetts establishment birth rate?",
    },
    "DL-14": {
        "public": "What is the unemployment rate in Massachusetts?",
        "journalist": "How many UI initial claims did Massachusetts file last week?",
        "researcher": "Is the unemployment rate seasonally adjusted, and is the wage figure from the same month?",
        "policymaker": "What is the Massachusetts labor-force participation rate?",
    },
    "DL-15": {
        "public": "What is Massachusetts real GDP?",
        "journalist": "Which state has the highest per capita personal income?",
        "researcher": "Is state GDP on this page in chained 2017 dollars or current dollars?",
        "policymaker": "What is Massachusetts manufacturing GDP?",
    },
    "DL-16": {
        "public": "How many housing units were authorized in Massachusetts?",
        "journalist": "Where did house prices rise fastest last year?",
        "researcher": "Are housing permits completions, and is FHFA the same as Case-Shiller?",
        "policymaker": "What is the Case-Shiller Boston house price index?",
    },
    "DL-17": {
        "public": "Is Massachusetts gaining or losing people?",
        "journalist": "How many Census-estimated births and deaths did Massachusetts have in 2025?",
        "researcher": "Is domestic migration on this page the Census estimate or IRS taxpayer returns?",
        "policymaker": "What share of Massachusetts residents are age 65 and over?",
    },
    "DL-19": {
        "public": "Is Massachusetts more expensive than the United States?",
        "journalist": "Which state has the highest housing regional price parity?",
        "researcher": "What does a regional price parity of 100 mean?",
        "policymaker": "How does Massachusetts housing RPP compare with its all-items RPP?",
    },
    "DL-20": {
        "public": "Are taxpayers leaving Massachusetts?",
        "journalist": "Where did Massachusetts taxpayers move, and how many went to Florida?",
        "researcher": "Are IRS taxpayer flows the same as Census domestic migration?",
        "policymaker": "Which Massachusetts counties lost the most taxpayer returns?",
    },
    "DL-21": {
        "public": "What is Massachusetts adjusted gross income?",
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
        "public": "How many vehicle-miles were driven in Massachusetts?",
        "journalist": "Which states have the highest National Risk Index scores?",
        "researcher": "Is VMT all functional systems, and is the risk score a county mean?",
        "policymaker": "How much has FEMA obligated to Massachusetts?",
    },
    "DL-24": {
        "public": "How much CO2 does Massachusetts emit from energy?",
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
        "public": "Who is the highest paid Boston city employee?",
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
        "public": "Which state collected the most tax last quarter?",
        "journalist": "What share of Massachusetts state tax is the individual income tax?",
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
        "public": "How many prisoners does Massachusetts hold?",
        "journalist": "Which state has the highest imprisonment rate?",
        "researcher": "Are youth counts on this page OJJDP custody or people 17 or younger in adult prisons?",
        "policymaker": "What is the Massachusetts imprisonment rate compared with the United States?",
    },
    "DL-32": {
        "public": "How much is the Massachusetts House Speaker paid?",
        "journalist": "How much did Massachusetts legislators earn in 2025?",
        "researcher": "Does this file include GIC health costs or the office-expense allowance?",
        "policymaker": "What is the leadership premium over base legislator pay?",
    },
}

COMPANION_JUMPS = {
    "DL-06": (
        ("MCAS", "#insight-mcas-2025"),
        ("Chapter 74", "#insight-ch74-seats"),
        ("District spending", "#insight-dist-ppe-ma"),
    ),
    "DL-07": (
        ("NAEP change", "#view-rank"),
        ("Graduation", "#insight-acgr"),
        ("Suspension", "#insight-oss"),
    ),
    "DL-14": (
        ("Wages", "#insight-qcew-wage"),
        ("UI claims", "#insight-ui-claims"),
        ("Participation", "#insight-lfpr"),
    ),
    "DL-15": (
        ("Industry mix", "#insight-ma-industries"),
        ("Income per person", "#insight-pcpi"),
    ),
    "DL-17": (
        ("Births", "#insight-births"),
        ("Deaths", "#insight-deaths"),
        ("Age 65 and over", "#insight-age65"),
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
