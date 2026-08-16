# Pioneer Institute DataLabs

Live site: [datalabsai.netlify.app](https://datalabsai.netlify.app)

Internal beta for Pioneer staff. Five flagships plus a 27-application
suite, all on one Netlify site. The ask box is on at the front door
(`?ai=0` hides it). Production deploys from `main`. Merging a pull
request is what publishes. Staff tester brief: `BETA.md`.

| Tool | Page | Canonical ledger | How it refreshes |
| --- | --- | --- | --- |
| DL-01 State Wealth Taxes | `/tax-atlas/` | `netlify/functions/dl01-answers.json` | Weekly Cursor Automation, Monday 9:00 AM ET. Runbook: `scripts/dl01-research-pass.md` |
| DL-02 Florida Homeowners Insurance | `/florida-insurance/` | `netlify/functions/dl02-answers.json` | Monthly Cursor Automation, 17th at 10:00 AM ET. Runbook: `scripts/dl02-research-pass.md` |
| DL-03 MBTA Performance | `/mbta/` | `netlify/functions/dl03-answers.json` | Monthly GitHub Action. Script: `scripts/refresh_dl03.py` |
| DL-04 Retail Electricity Prices | `/electricity/` | `netlify/functions/dl04-answers.json` | Yearly GitHub Action, October. Script: `scripts/refresh_dl04.py` |
| DL-05 Massachusetts Public Pensions | `/pensions/` | `netlify/functions/dl05-answers.json` | Monthly GitHub Action for CTHRU retirees and name search (`scripts/refresh_dl05.py`). Research pass when PERAC posts a new Investment Report: `scripts/dl05-research-pass.md`. `scripts/build_dl05.py` is the one-time compiler from the partner extracts, not a publisher refresh. |
| DL-06 to DL-32 (27 apps) | see `suite/apps.json` | `netlify/functions/dlXX-answers.json` | Monthly GitHub Action (`scripts/refresh_suite.py`). Live builders fetch public files. 340B rebuilds from a local OPAIS daily export plus CMS and Census files (`scripts/build_dl11.py`); Patents stays an in-build stub. No invented figures. |

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
