# DL-05 research pass (when PERAC posts)

This is the canonical prompt for updating the **board** half of
Massachusetts Public Pensions (DL-05): funded ratios and investment
returns. PERAC's Investment Report is a PDF and the funded-ratios table
is a Mass.gov portal. There is no machine-readable refresh that can
replace a transcription of those sources.

The **retiree** half (CTHRU payroll, top pensions, departments, and the
last-name search shards) is already fetched by `scripts/refresh_dl05.py`
and `.github/workflows/dl05-refresh.yml`. Do not invent a second retiree
fetch. Do not commit TWBX files or a named-retiree extract.

Read `AGENTS.md` first. Edit `netlify/functions/dl05-answers.json` as the
source of truth for board cells. Then run `python3 scripts/inject_data.py`.

## Paste this into a Cursor Automation or Cloud Agent

**Name:** DL-05 pensions research pass

**Repository:** `jcalabr3ez/datalabs-prototype`, branch `main`.

**Prompt to paste:**

    Follow scripts/dl05-research-pass.md exactly. This is the research
    pass for Pioneer DataLabs Massachusetts Public Pensions (DL-05),
    board half only.

    Edit netlify/functions/dl05-answers.json as the source of truth.
    Do not rebuild retiree totals or pensions/search/ by hand; those
    come from scripts/refresh_dl05.py. Run python3 scripts/inject_data.py.
    Then run python3 scripts/check_style.py, python3 scripts/check_freshness.py,
    and node --check scripts/check_engine.mjs (or node scripts/check_engine.mjs).

    Update an existing PR only if it is a draft whose title starts with
    DL-05. Ignore every other open or closed PR. Do not push main.

    House style: no em dashes, spell out million and billion, keep $ on
    figures. Set page.revised to today's date (Mon D, YYYY).

## What to update

1. **Board funded status (SRC-501).** Open
   https://www.mass.gov/info-details/funded-ratios and
   https://www.mass.gov/doc/2024-investment-report/download (or the
   newer Investment Report if PERAC has posted one). For each board,
   replace `funded_pct`, `valuation_year`, and unfunded liability when
   the new print differs. Recompute `funded_recomputed_pct` as
   `round((1 - ual / aal) * 100, 1)` and fail the pass if any board
   is more than 0.6 points off. Rebuild `latest`, `derived`, ranks,
   and `funded_history` for any board that gained a new valuation year.

2. **Returns (SRC-502).** Transcribe one-year, five-year, ten-year, and
   since-inception returns from the latest PERAC Investment Report.
   Set `returns_year` to that calendar year. The 2023 extract labeled
   its one-year column 2022; do not repeat that. The printed year on
   the report is the vintage.

3. **State and Teacher retirees (SRC-503).** Leave this block to
   `scripts/refresh_dl05.py`. If the monthly workflow has not run and
   CTHRU is obviously stale, run that script once. Do not invent a
   second retiree fetch. Do not commit the named-retiree file. Keep
   CTHRU counts separate from PERAC actuarial recipient counts (pending
   CTHRU-VS-PERAC-HEADCOUNT).

4. **Clear or keep pending flags.** PERAC-2024-IR clears when the 2024
   Investment Report and the live funded-ratios table are in the
   ledger. Add a new pending row if a later report exists but could
   not be fully transcribed.

5. **as_of** is the newest month in the ledger, usually the CTHRU
   fetch month (`YYYY-MM`). Do not roll it backward to a valuation year.

## What not to do

- Do not invent a fetch that pretends Mass.gov PDFs are an API. A
  future compiler is fine only if PERAC posts a real CSV.
- Do not look up named retirees in the ask box. The page search is
  the lookup. The ask box still answers "who is paid the most" from
  `top_pensions`.
- Do not fold this into a DL-01, DL-02, DL-03, or DL-04 PR.
- Do not ship Tableau.
