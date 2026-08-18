# Overnight platform audit (every live tool)

This is the canonical prompt for a **platform-wide claim and chart audit**.
A Cursor Automation should follow this file overnight. A human can also
paste it into a Cloud Agent.

This is **not** a data refresh. Do not run `refresh_suite.py`,
`refresh_dl03.py`, `refresh_dl04.py`, `refresh_dl05.py`, or
`build_dl11.py`. Those jobs already open their own pull requests. Do not
invent a second fetch. Do not invent figures. Do not mark a stub `live`.
Do not change Near-Term Risk ratings (last scored July 28, 2026).

## Paste this into the Cursor Automation

Create the Automation at [cursor.com/automations/new](https://cursor.com/automations/new).
Scheduled triggers default to **no repository**; attach
`jcalabr3ez/datalabs-prototype` on branch `main` or the agent cannot edit
code or open a PR.

**Name:** Platform overnight claim and chart audit

**Trigger:** Scheduled. Cron (preferred, stays at 2:00 AM Eastern through DST):

    CRON_TZ=America/New_York 0 2 * * *

If the UI rejects `CRON_TZ`, use UTC and change it when the clocks change:

    0 6 * * *    # 2:00 AM EDT (mid-March through early November)
    0 7 * * *    # 2:00 AM EST (early November through mid-March)

Confirm the first fire time in the UI. Scheduled runs may be late; they
should not start early. This job must not collide with DL-01 (Monday
9:00 AM ET) or DL-02 (the 17th at 10:00 AM ET).

**Repository:** `jcalabr3ez/datalabs-prototype`, branch `main`.

**Model:** the most capable model in the picker. Automations always get
that model's maximum context window.

**Tools:** Pull request creation on (default). Memories on (default).
Computer use on (default) so vertical agents can open source URLs. Do
not enable merge or any "push to main" action.

**Prompt to paste:**

    Follow scripts/platform-audit-pass.md exactly. This is the overnight
    platform audit for Pioneer DataLabs. It validates every published
    claim and checks that each live tool has the insight charts its
    ledger can already support.

    Do not refresh publisher files. Do not run refresh_suite.py,
    refresh_dl03.py, refresh_dl04.py, refresh_dl05.py, or build_dl11.py.
    Do not invent figures. Do not mark Patents (DL-18) live. Do not
    change Near-Term Risk ratings.

    Run python3 scripts/audit_platform.py --json /tmp/platform-audit.json
    --md /tmp/platform-audit.md. Then launch five parallel agents, one
    per Pioneer vertical in that report. Each agent fixes hard failures
    from existing ledger cells and adds insight charts only from
    published secondary series. After the five briefs return, run
    python3 scripts/inject_data.py, then python3 scripts/check_style.py,
    python3 scripts/check_freshness.py, python3 scripts/check_answers.py,
    and node --check scripts/check_engine.mjs.

    Open a DRAFT pull request against main whose title starts with
    Platform audit. Use the PR body template in this runbook. Update an
    existing PR only if it is a draft whose title starts with Platform
    audit. Ignore every other open or closed PR, including DL-01, DL-02,
    DL-05, suite-refresh, and the Florida export.

    Memories: store the open PR URL, tools that stayed clean, and any
    unreachable source notes so the next night does not duplicate work.

## Goal

Every live tool (DL-01 through DL-33, skipping in-build stubs) should
end the night with:

1. **Claims that recompute.** Hero numbers, bold takeaways, figure ledes,
   catalog `ma` lines, and rank tables match a cell in that tool's
   ledger. Ranks recompute from the published rows.
2. **Charts that earn their keep.** Figure 1 still answers the public
   question (hex cartogram on fifty-state tools). Each later-view series
   that already has published cells gets an insight figure when the
   existing helpers in `scripts/insight_figures.py` can draw it. Pending
   or unpublished series stay captioned as missing. Do not invent a
   series to fill a hole.

The product rule from `NEW-TOOL-CHECKLIST.md` still holds: verification
is the work. A prettier chart that is not a ledger cell is a different
product.

## Hard rules

1. **Open a draft pull request. Do not merge. Do not push `main`.**
   Production deploys from `main` via Netlify.
2. **Do not invent a second refresh.** If a source URL looks newer than
   the ledger vintage, write it under Unreachable / newer vintage. Leave
   the figure in place. The Monday DL-01 pass, the 17th DL-02 pass, the
   monthly Actions, and the PERAC board pass are the fetches.
3. **Edit canonical files only.** Ledgers, `scripts/insight_figures.py`,
   `scripts/page_voice.py` when generated prose drifted, then
   `python3 scripts/inject_data.py`. Do not hand-edit `DATA:BEGIN` blocks.
4. **Do not invent figures.** Chart additions use `from_snap`,
   `named_list`, `_slope`, or `_fig` against cells that already exist
   under `latest`, `rows`, or `derived.secondary`.
5. **Do not fold this into another workstream.** Update an existing PR
   only if it is a draft whose title starts with `Platform audit`.
6. **Florida:** any edit to the Florida page or `dl02-answers.json` must
   set `page.revised` to today (`Mon D, YYYY`) and run inject.
7. **House style:** no em dashes. Spell out million and billion in
   prose. Keep `$` on figures.
8. **Patents (DL-18) stays a stub.** Do not mark it `live`.

## What the deterministic script already checks

`python3 scripts/audit_platform.py` walks `catalog.json` and every
`dlXX-answers.json`:

- Hero number is a ledger cell
- Catalog `ma` line matches generated voice
- Rank tables recompute (`rank_rows` / `rank_named`, either direction)
- Bold takeaway numbers appear in the ledger
- Insight figure series are non-empty and cite a known `SRC-` id
- Figure ledes match the series or a ledger cell
- National-lens pages still ship hex Figure 1
- Each chartable `derived.secondary` key either has an insight figure
  or is listed as uncharted with a recommended chart type

The script does not open the public web. Vertical agents do that.

## Depth: five parallel agents

Launch **five** agents in parallel after the JSON report exists. Give
each agent the slice of `/tmp/platform-audit.json` for its tool ids,
the matching ledgers, and `scripts/insight_figures.py` for those tools.
Each agent returns a structured brief: tool, failure or gap, what
changed, or why it was left.

### Agent 1: Education (DL-06, DL-07, DL-08, DL-09)

### Agent 2: Healthcare (DL-10, DL-11, DL-12, DL-33)

### Agent 3: Economic Opportunity (DL-04, DL-13, DL-14, DL-15, DL-16, DL-17, DL-18, DL-19)

DL-18 is a stub. Confirm it is still in build. Do not compile patents.

### Agent 4: Citizenship, tax and payroll (DL-01, DL-05, DL-20, DL-21, DL-27, DL-28, DL-29, DL-30, DL-32)

Do not change Near-Term Risk ratings or the July 28, 2026 score date.
DL-01 chart work is the hex map and captions only; do not rebuild the
atlas register (that is Monday's job).

### Agent 5: Citizenship, place and infrastructure (DL-02, DL-03, DL-22, DL-23, DL-24, DL-25, DL-26, DL-31)

Do not refresh the FTA NTD file. If a Florida ledger or page field
changes, set `page.revised` to today.

Each vertical agent should:

1. Fix hard failures first. Drifted hero text, a wrong `SRC-` id, or a
   rank that does not recompute is a ledger or voice bug, not a new
   fetch.
2. For each uncharted secondary series, add a figure in
   `scripts/insight_figures.py` from those cells. Prefer the recommended
   type in the report (line for a trend, slope for two published years,
   `from_snap` bar for MA / FL / high / low). Do not draw a U.S. bar
   that dwarfs the states when `_us_dwarfs` would hide it.
3. HEAD or open each `SRC-` URL on the tools you touch. If the page is
   gone or a newer vintage is posted, record it. Do not replace the
   figure.
4. Leave pending / not-published notes as notes. Tableau heritage holes
   in `scripts/tableau-coverage.md` stay pending until a named public
   file is compiled by the suite refresh.

## After the five briefs return

1. Re-run `python3 scripts/audit_platform.py --json /tmp/platform-audit.json --md /tmp/platform-audit.md`.
   Failures you can fix from the ledger should be gone. Remaining gaps
   belong in the PR under Checked, no change or Unreachable.
2. Run `python3 scripts/inject_data.py`.
3. If Florida changed, confirm `page.revised` is today.
4. Run `python3 scripts/check_style.py`, `python3 scripts/check_freshness.py`,
   `python3 scripts/check_answers.py`, and `node --check scripts/check_engine.mjs`.
   Fix failures you introduced.
5. Commit on a feature branch. Push. Open a **draft** pull request
   against `main` whose title starts with `Platform audit`.

## Pull request body (required)

```markdown
## Platform audit (YYYY-MM-DD)

Overnight claim and chart pass. Deterministic inventory, then five
vertical agents. Live tools: N. Failures fixed: N. Charts added: N.

### Changed
- DL-XX … (old → new). Source: SRC-… (existing cell)

### Checked, no change
- DL-XX secondary.foo stays pending (file not published).

### Unreachable / newer vintage (do not fetch here)
- SRC-… URL returned 404 / a newer year is posted.

### Charts
- Added / kept. Every new figure cites a ledger cell.

### Deploy
- Draft PR only. Merge to `main` to publish on Netlify.
```

## Local one-off (same depth, no Automation)

```bash
python3 scripts/audit_platform.py --json /tmp/platform-audit.json --md /tmp/platform-audit.md
# Then follow the five-agent section and the after-brief steps.
```

A failing rank or an empty hero is a real bug. An uncharted later view
is a chart opportunity, not a license to invent a series.
