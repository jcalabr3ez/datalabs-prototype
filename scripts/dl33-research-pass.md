# DL-33 research pass (after each CHIA MHIS release)

This is the runbook for Family Healthcare Costs. CHIA fields the
Massachusetts Health Insurance Survey every two years. The 2025 report
and detailed tables published on December 11, 2025. The next survey is
expected in 2027. A human can paste this into a Cloud Agent when CHIA
posts a newer file.

## Goal

Rebuild `netlify/functions/dl33-answers.json` from the newest public
MHIS detailed tables. Do not invent a dollar average. Do not mix in
MEPS, CMS NHE, hospital relative prices, 340B, or Medicaid program
spend.

## Source register

1. Report PDF:
   https://www.chiamass.gov/wp-content/uploads/docs/r/survey/MHIS-2025/2025-MHIS-Report.pdf
2. Detailed tables (the ledger file):
   https://www.chiamass.gov/wp-content/uploads/docs/r/survey/MHIS-2025/2025-MHIS-Detailed-Tables.xlsx
3. Methodology:
   https://www.chiamass.gov/wp-content/uploads/docs/r/survey/MHIS-2025/2025-MHIS-Methodology.pdf
4. Landing page (to confirm a newer vintage):
   https://www.chiamass.gov/insights-analysis/access/massachusetts-health-insurance-survey/

If CHIA posts a 2027 (or later) folder, update those four URLs in
`suite/apps.json` and in `scripts/suite_later.py` (`MHIS_XLSX` and the
`VERIFY_MHIS` printed cells).

## What to recompute

Run the existing builder. It fetches the Excel, locks the first matching
outcome on each sheet, and fails if a printed cell moved:

    python3 -c "import sys; sys.path.insert(0,'scripts'); from suite_common import load_apps, write_ledger; from suite_later import build_healthcare_costs; app=next(a for a in load_apps() if a['id']=='DL-33'); write_ledger(build_healthcare_costs(app))"

Namesake cell: table E.4 high out-of-pocket-to-income ratio (above 5
percent of income below 200 percent FPL, or above 10 percent at or
above 200 percent FPL). Income-group rows come from E.4-5.

Later views stay on the same file: D.1 affordability, D.2 unmet need,
E.1 bills, E.2 debt, F.1 share-of-income buckets, B.1 coverage, B.3
high-deductible plans, G.2 behavioral-health visits paid entirely out
of pocket.

If a sheet name or outcome label changes, edit `_mhis_parse` calls in
`build_healthcare_costs`. Do not keep a stale VERIFY_MHIS number.

## After the ledger

    python3 scripts/inject_data.py
    python3 scripts/check_style.py
    python3 scripts/check_freshness.py
    node --check scripts/check_engine.mjs

Set `page.revised` to today. Open a draft pull request against main.
Do not merge. Do not push main. Do not edit State Wealth Taxes or
Florida Homeowners Insurance.
