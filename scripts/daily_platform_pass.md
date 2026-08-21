# One daily platform pass

This is the canonical prompt for the **one daily job** that covers the
whole Pioneer DataLabs platform: every public-file ledger, the State
Wealth Taxes atlas (bills, hearings, dockets), and Florida Homeowners
Insurance.

Create one Cursor Automation. After it has run clean, delete the older
clocks listed at the bottom. Do not invent a second daily pass next to
this one.

## Paste this into the Cursor Automation

Create the Automation at cursor.com/automations/new. Scheduled triggers
default to no repository. Attach `jcalabr3ez/datalabs-prototype` on
branch `main`.

**Name:** Platform daily pass

**Trigger:** Scheduled. Cron (stays on 9:00 AM Eastern through DST):

    CRON_TZ=America/New_York 0 9 * * *

UTC fallback: `0 13 * * *` during EDT, `0 14 * * *` during EST.

**Repository:** `jcalabr3ez/datalabs-prototype`, branch `main`.

**Model:** the most capable model. Computer use on. Pull request
creation on. Do not enable merge or push to main.

**Prompt to paste:**

    Follow scripts/daily_platform_pass.md exactly. This is the one daily
    pass for Pioneer DataLabs. It covers every live ledger.

    1. File half. Run python3 scripts/daily_platform.py. That refreshes
    MBTA (DL-03), CTHRU retirees (DL-05), the suite (DL-06 to DL-34),
    and electricity (DL-04) in October. It does not invent figures. If
    a public file is missing, fail that tool and keep the last verified
    figure.

    2. State Wealth Taxes (DL-01). Recheck every source in the atlas
    register for a newer official page, bill, hearing, docket, SOS
    posting, or news report of a new filing. Edit
    netlify/functions/dl01-answers.json as the source of truth. Do not
    invent Near-Term Risk rating changes (last scored July 28, 2026).
    Follow the hard rules in scripts/dl01-research-pass.md. Use
    parallel research agents when many sources moved.

    3. Florida Homeowners Insurance (DL-02). Recheck every source in
    the Florida register: Citizens month-end PIF, OIR quarterlies,
    litigation, takeouts, risk transfer, statutory results. Edit
    netlify/functions/dl02-answers.json. Follow the hard rules in
    scripts/dl02-research-pass.md. Say policies in force, not homes.
    If no new file exists, keep the last verified figure and say so.

    4. Pension boards (DL-05). Only if PERAC posted a new Investment
    Report or funded-ratio table. Follow scripts/dl05-research-pass.md.
    Do not rebuild CTHRU retirees by hand.

    Then run python3 scripts/inject_data.py, python3
    scripts/check_style.py, python3 scripts/check_freshness.py,
    python3 scripts/check_answers.py, and DATALABS_CHECK_REGISTER=1
    python3 scripts/check_latest_release.py.

    Open or update ONE draft pull request against main on branch
    auto/daily-platform. Title must start with "Platform daily". Do
    not merge. Do not push main. Do not open a second PR for DL-01
    or DL-02. Ignore the Florida standalone export branch.

## Hard rules

1. One draft PR. Never merge. Never push main.
2. Edit canonical ledgers. Run inject. Do not hand-edit DATA:BEGIN blocks.
3. Do not invent figures, Near-Term Risk changes, or a second refresh.
4. House style: no em dashes. Spell out million and billion.

## What to delete after this job is the only clock

Do not delete these until a Platform daily PR has landed on main and
the human has turned this Automation on.

GitHub Actions (cron only; keep `workflow_dispatch` until the first
clean week, then delete the files):

- `.github/workflows/dl03-refresh.yml`
- `.github/workflows/dl04-refresh.yml`
- `.github/workflows/dl05-refresh.yml`
- `.github/workflows/suite-refresh.yml`

Cursor Automations:

- DL-01 weekly deep research pass (Monday 9:00 AM ET)
- DL-02 monthly full research pass (17th, 10:00 AM ET)

Keep:

- `.github/workflows/daily-platform.yml` (file half, same clock) until
  the Automation is proven, then leave it as `workflow_dispatch` only
  or delete it if the Automation is the only runner.
- `.github/workflows/checks.yml` on pull requests (not a refresh).
- `.github/workflows/eval.yml` (golden questions, not a refresh).
- `scripts/dl01-research-pass.md`, `scripts/dl02-research-pass.md`,
  and `scripts/dl05-research-pass.md` as the research runbooks this
  pass calls. Do not schedule them separately.
