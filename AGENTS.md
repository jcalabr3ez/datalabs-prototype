# Agent rules

This repository deploys from `main` via Netlify. Cloud agents open **draft
pull requests**. They do not merge and they do not push `main`.

## Canonical files (edit these)

- `catalog.json`
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

- **DL-01 (Monday 9:00 AM ET):** follow `scripts/dl01-research-pass.md`.
  Deep pass: five parallel agents over the full source register, not only
  sources due under the 45-day freshness gate. Update an existing PR only
  if it is a draft whose title starts with `DL-01`. Ignore every other
  open or closed PR, including the Florida export.
- **DL-02 (17th, 10:00 AM ET):** follow `scripts/dl02-research-pass.md`.
  Monthly full pass over the Florida register. Update an existing PR
  only if it is a draft whose title starts with `DL-02`. Do not fold
  this into the weekly DL-01 PR.
- **DL-03 (monthly):** `.github/workflows/dl03-refresh.yml` already opens
  a PR from the FTA NTD API. Do not invent a second refresh.
- **DL-04 (yearly, October):** `.github/workflows/dl04-refresh.yml` already
  opens a PR from EIA Form EIA-861, EIA-923, EIA-860, and Census
  population. Do not invent a second refresh.
- **DL-05 retirees (monthly):** `.github/workflows/dl05-refresh.yml`
  already opens a PR from `scripts/refresh_dl05.py` (live CTHRU API plus
  last-name shards under `pensions/search/`). Do not invent a second
  retiree fetch.
- **DL-05 boards (when PERAC posts):** follow
  `scripts/dl05-research-pass.md`. Update an existing PR only if it is a
  draft whose title starts with `DL-05`. Do not invent a fetch for the
  Investment Report; that source is a PDF.

## House style

No em dashes. Spell out million and billion in prose. Keep `$` on figures.
Do not invent facts. Do not invent Near-Term Risk rating changes (last
scored July 28, 2026).

After ledger edits: `python3 scripts/inject_data.py`, then
`python3 scripts/check_style.py`, `python3 scripts/check_freshness.py`,
and `node --check scripts/check_engine.mjs`.

Any change to the Florida page or `dl02-answers.json` must set
`page.revised` to today's date (`Mon D, YYYY`, e.g. `Aug 14, 2026`)
and run inject. The hero dateline and footer Revised line are generated
from that field. Do not ship a Florida edit with a stale revised date.

## Do not mix workstreams

The Florida standalone Netlify drop lives on
`cursor/florida-standalone-export-614f` (closed PR #2; do not reopen or
merge it). Do not fold that export into a DL-01, DL-02, or DL-03
research PR.
