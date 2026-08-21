# Agent rules

This repository deploys from `main` via Netlify. Cloud agents open **draft
pull requests**. They do not merge and they do not push `main`.

## Canonical files (edit these)

- `catalog.json`
- `suite/apps.json` (the suite registry; do not invent an app without a source)
- `netlify/functions/dl01-answers.json`
- `netlify/functions/dl02-answers.json`
- `netlify/functions/dl03-answers.json`
- `netlify/functions/dl04-answers.json`
- `netlify/functions/dl05-answers.json`
- Hand-authored prose: hero / methodology / source register / footer on
  `tax-atlas/index.html`, remaining Florida, electricity, and pensions
  narrative (charts and keyed headlines are generated), and front-door
  chrome in `index.html`

`python3 scripts/inject_data.py` rewrites every `DATA:BEGIN` / `DATA:END`
block and `netlify/functions/catalog.json`. Do not hand-edit those copies.

## Recurring jobs

- **One daily platform pass:** follow `scripts/daily_platform_pass.md`.
  File half is `python3 scripts/daily_platform.py` and
  `.github/workflows/daily-platform.yml` (MBTA, CTHRU retirees, suite,
  electricity in October). Editorial half is the same job: the wealth-tax
  atlas register (bills, hearings, dockets) and the Florida insurance
  register. One draft PR on `auto/daily-platform`. Do not merge. Do not
  invent a second daily pass.
- **DL-01 / DL-02 / DL-05 runbooks** stay as
  `scripts/dl01-research-pass.md`, `scripts/dl02-research-pass.md`, and
  `scripts/dl05-research-pass.md`. The daily pass calls them. Do not
  schedule those files on their own once the daily Automation is on.
- **Older clocks to delete** after the daily pass is the only clock:
  `dl03-refresh.yml`, `dl04-refresh.yml`, `dl05-refresh.yml`,
  `suite-refresh.yml`, the Monday DL-01 Automation, and the 17th DL-02
  Automation. See the list in `scripts/daily_platform_pass.md`.
- **340B (DL-11)** still rebuilds from a local OPAIS export plus CMS and
  Census files (`scripts/build_dl11.py`). Patents stays a stub. Do not
  invent figures.

## House style

No em dashes. Spell out million and billion in prose. Keep `$` on figures.
Do not invent facts. Do not invent Near-Term Risk rating changes (last
scored July 28, 2026).

After ledger edits: `python3 scripts/inject_data.py`, then
`python3 scripts/check_style.py`, `python3 scripts/check_freshness.py`,
`node --check scripts/check_engine.mjs`, and
`node scripts/check_page_payload.mjs`.

Any change to the Florida page or `dl02-answers.json` must set
`page.revised` to today's date (`Mon D, YYYY`, e.g. `Aug 14, 2026`)
and run inject. The hero dateline and footer Revised line are generated
from that field. Do not ship a Florida edit with a stale revised date.

## Do not mix workstreams

The Florida standalone Netlify drop lives on
`cursor/florida-standalone-export-614f` (closed PR #2; do not reopen or
merge it). Do not fold that export into a DL-01, DL-02, or DL-03
research PR.
