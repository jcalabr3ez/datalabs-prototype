# Pioneer Institute DataLabs

Live site: [datalabsai.netlify.app](https://datalabsai.netlify.app)

One-month internal prototype for Pioneer staff, August 16 through
September 16, 2026. Five flagships plus a 29-application suite, all
on one Netlify site. The ask box is on at the front door (`?ai=0`
hides it). Production deploys from `main`. Merging a pull request is
what publishes. Staff tester brief: `BETA.md`.

| Tool | Page | Canonical ledger | How it refreshes |
| --- | --- | --- | --- |
| DL-01 State Wealth Taxes | `/tax-atlas/` | `netlify/functions/dl01-answers.json` | Daily platform pass. Atlas register (bills, hearings, dockets). Runbook: `scripts/daily_platform_pass.md` |
| DL-02 Florida Homeowners Insurance | `/florida-insurance/` | `netlify/functions/dl02-answers.json` | Daily platform pass. Florida register. Runbook: `scripts/daily_platform_pass.md` |
| DL-03 MBTA Performance | `/mbta/` | `netlify/functions/dl03-answers.json` | Daily platform pass. Script: `scripts/refresh_dl03.py` |
| DL-04 Retail Electricity Prices | `/electricity/` | `netlify/functions/dl04-answers.json` | Daily platform pass, EIA fetch in October. Script: `scripts/refresh_dl04.py` |
| DL-05 Massachusetts Public Pensions | `/pensions/` | `netlify/functions/dl05-answers.json` | Daily platform pass for CTHRU retirees (`scripts/refresh_dl05.py`). Boards when PERAC posts: `scripts/dl05-research-pass.md`. |
| DL-06 to DL-34 (29 apps) | see `suite/apps.json` | `netlify/functions/dlXX-answers.json` | Daily platform pass (`scripts/refresh_suite.py`). 340B rebuilds from a local OPAIS export (`scripts/build_dl11.py`). Patents stays a stub. No invented figures. |

Public ops pages: [`/status/`](https://datalabsai.netlify.app/status/) (vintage and freshness) and [`/changelog/`](https://datalabsai.netlify.app/changelog/). Chart.js 4.4.1 (MIT) is vendored at `assets/chart.umd.min.js`.

## Edit and deploy

1. Edit a canonical file (`catalog.json` or a `dlXX-answers.json`). Do not
   hand-edit generated `DATA:BEGIN` / `DATA:END` blocks.
2. Run `python3 scripts/inject_data.py`.
3. Open a pull request against `main`. Do not push `main` directly.

How the platform is built, with diagrams: `ARCHITECTURE.md`.
First-time GitHub + Netlify setup: `SETUP.md`.
Adding a new tool: `NEW-TOOL-CHECKLIST.md`.
Rules for cloud agents: `AGENTS.md`.
