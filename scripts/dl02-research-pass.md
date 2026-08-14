# DL-02 refresh pass: local runbook (quarterly)

Why this is a runbook and not a workflow: the DL-02 sources are not
machine-readable the way NTD is. OIR's QUASR statewide summaries are
Excel files behind a form-driven portal, Citizens' filings are PDFs, and
the litigation shares come through NAIC MCAS as published by OIR. Fetching
them needs a person (or a Cloud Agent); verifying them needs
judgment. The checks workflow's freshness gate (160-day limit on the DL-02
as_of) signals when this pass is due, roughly once a quarter.

The canonical ledger is netlify/functions/dl02-answers.json. Running
python3 scripts/inject_data.py regenerates the flagship charts, the
dateline, the Citizens policies-in-force headline, the county-change
ranking sentence, and the front-door Florida series. Remaining narrative
(report-card grades, methodology folds, source-register notes that quote
a figure) is still hand-authored. CI sentinels require the page to carry
the ledger's latest Citizens count and as_of month, so a ledger refresh
without those headlines fails.

Paste this prompt into a Cloud Agent:

    Run the quarterly refresh pass for Pioneer DataLabs Florida Insurance
    Watch (DL-02). The canonical ledger is netlify/functions/dl02-answers.json;
    the flagship page florida-insurance/index.html documents every source
    with its cadence in its register.

    1. Read the ledger's as_of and each series' latest period.
    2. Check the sources for newer publications:
       - Citizens policies in force: Citizens' monthly policy count reports
         (citizensfla.com, policy and exposure filings).
       - County premiums: OIR QUASR statewide summary by company and policy
         type, the next quarterly file.
       - Litigation shares: NAIC MCAS as published or cited by OIR.
       - Risk transfer: Citizens audited statements and Gallagher Re
         Florida Market Watch.
    3. Update dl02-answers.json ONLY with figures you verified against the
       source documents; recompute derived values (citizens_key_facts,
       county_rankings) from the new series. Update as_of. House style: no
       em dashes, every figure keeps its source id.
    4. Run: python3 scripts/inject_data.py
       Charts, dateline, the Citizens PIF headline, and the county-change
       ranking sentence update from the ledger. Do not hand-edit those
       DATA:BEGIN blocks.
    5. Update remaining hand-authored prose that still quotes a figure
       (report card, methodology folds, source-register vintages, any
       paragraph that names a number inject does not own). Then run
       python3 scripts/check_style.py until clean.
    6. Show the diff with each change tied to its source. Open a draft
       pull request against main. Do not merge. Do not push main.
       Merging to main is what deploys.

The quarterly OIR file drops lag the quarter end by roughly two months;
Citizens monthly counts run about one month behind. If only Citizens has
new data, a Citizens-only update is fine; note the mixed vintages in the
ledger notes the way the current file does.
