# Agent rules

This repository deploys from `main` via Netlify. Cloud agents open **draft
pull requests**. They do not merge and they do not push `main`.

## Canonical files (edit these)

- `catalog.json`
- `netlify/functions/dl01-answers.json`
- `netlify/functions/dl02-answers.json`
- `netlify/functions/dl03-answers.json`
- Hand-authored prose: hero / methodology / source register / footer on
  `tax-atlas/index.html`, remaining Florida narrative (charts and keyed
  headlines are generated), and front-door chrome in `index.html`

`python3 scripts/inject_data.py` rewrites every `DATA:BEGIN` / `DATA:END`
block and `netlify/functions/catalog.json`. Do not hand-edit those copies.

## Recurring jobs

- **DL-01 (Monday 9:00 AM ET):** follow `scripts/dl01-research-pass.md`.
  Deep pass: five parallel agents over the full source register, not only
  sources due under the 45-day freshness gate. Update an existing PR only
  if it is a draft whose title starts with `DL-01`. Ignore every other
  open or closed PR, including the Florida export.
- **DL-02 (quarterly):** follow `scripts/dl02-research-pass.md`.
- **DL-03 (monthly):** `.github/workflows/dl03-refresh.yml` already opens
  a PR from the FTA NTD API. Do not invent a second refresh.

## House style

No em dashes. Spell out million and billion in prose. Keep `$` on figures.
Do not invent facts. Do not invent Near-Term Risk rating changes (last
scored July 28, 2026).

After ledger edits: `python3 scripts/inject_data.py`, then
`python3 scripts/check_style.py`, `python3 scripts/check_freshness.py`,
and `node --check scripts/check_engine.mjs`.

## Do not mix workstreams

The Florida standalone Netlify drop lives on
`cursor/florida-standalone-export-614f` (closed PR #2; do not reopen or
merge it). Do not fold that export into a DL-01 or DL-03 research PR.
