# Pioneer Institute DataLabs

Live site: [datalabsai.netlify.app](https://datalabsai.netlify.app)

Browse-first front door plus four tools on one Netlify site. The ask
box is off by default (`?ai=1` still previews it). Production deploys from
`main`. Merging a pull request is what publishes.

| Tool | Page | Canonical ledger | How it refreshes |
| --- | --- | --- | --- |
| DL-01 State Tax Atlas | `/tax-atlas/` | `netlify/functions/dl01-answers.json` | Weekly Cursor Automation, Monday 9:00 AM ET. Runbook: `scripts/dl01-research-pass.md` |
| DL-02 Florida Insurance Watch | `/florida-insurance/` | `netlify/functions/dl02-answers.json` | Monthly Cursor Automation, 17th at 10:00 AM ET. Runbook: `scripts/dl02-research-pass.md` |
| DL-03 Transportation & MBTA | `/mbta/` | `netlify/functions/dl03-answers.json` | Monthly GitHub Action. Script: `scripts/refresh_dl03.py` |
| DL-04 Retail Electricity Prices | `/electricity/` | `netlify/functions/dl04-answers.json` | Yearly GitHub Action, October. Script: `scripts/refresh_dl04.py` |

## Edit and deploy

1. Edit a canonical file (`catalog.json` or a `dlXX-answers.json`). Do not
   hand-edit generated `DATA:BEGIN` / `DATA:END` blocks.
2. Run `python3 scripts/inject_data.py`.
3. Open a pull request against `main`. Do not push `main` directly.

First-time GitHub + Netlify setup: `SETUP.md`.
Adding a fourth tool: `NEW-TOOL-CHECKLIST.md`.
Rules for cloud agents: `AGENTS.md`.
