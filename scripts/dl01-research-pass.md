# DL-01 research pass: local runbook

The State Tax Atlas is editorial data; its refresh is a research job, not a
script. Run it locally in Claude Code from the repository root, roughly every
four to six weeks (the checks workflow will start failing freshness once the
ledger's as_of ages past 45 days). No API key ever goes to GitHub; the pass
runs on your machine and everything lands as an ordinary reviewed commit.

Paste this prompt into Claude Code:

    Run the scheduled research pass for the Pioneer DataLabs State Tax Atlas
    (DL-01). The canonical ledger is netlify/functions/dl01-answers.json; the
    page's source register (tax-atlas/index.html, "Data Sources" section)
    lists every source with its cadence, current vintage, and next expected
    release.

    1. Read the ledger's as_of date and the source register.
    2. Identify sources whose next-release date has passed or whose tracked
       events (hearings, rulings, certifications, elections) were dated
       before today.
    3. For each, check the source and determine what changed.
    4. Apply factual updates to netlify/functions/dl01-answers.json ONLY
       where you have a verifiable source: status changes, resolved events,
       new filings. Update as_of. Never invent figures; anything unverified
       is described as pending. House style: no em dashes anywhere, every
       figure names its instrument or source.
    5. Run: python3 scripts/inject_data.py
    6. Show me the diff with each change tied to its source URL, plus
       anything due that you could NOT verify, before committing. Do not
       push; pushing deploys.

Review the diff, then commit and push to deploy. The August 11, 2026
re-verification (5 parallel research agents, 47 register sources) is the
reference for how deep a full pass goes; routine passes are smaller.
