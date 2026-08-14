# DataLabs Prototype: Setup (GitHub + Netlify + Anthropic API)

Time: about 30 minutes. No local tools required; every step can be done in
a web browser. If you prefer the git command line, Step 2 has that path too.

## What is in this repository

    index.html                     Front door (Ask, All Tools, By Geography, Sources)
    catalog.json                   CANONICAL catalog: topic categories, legacy
                                   dashboards, the three flagships, the archive
    mbta/index.html                DL-03 Transportation & MBTA flagship page
    florida-insurance/index.html   DL-02 Florida Insurance Watch flagship page
    tax-atlas/index.html           DL-01 State Tax Atlas flagship page
    netlify/functions/ask.js       The engine: one Sonnet 5 call reads the
                                   catalog, every tool's scope, and a
                                   selected payload of ledgers (full
                                   modelSlice on a trigger hit, coreSlice
                                   otherwise), then answers, routes, or
                                   declines under a JSON schema. Holds the key.
                                   There is no router: a two-stage handoff
                                   was tried and failed eval.
    netlify/functions/tools.js     Per-tool manifests. Adding an AI-enabled tool
                                   = one dataset JSON + one entry here
                                   (scope, triggers, coreSlice, modelSlice).
    netlify/functions/catalog.json GENERATED copy of the root catalog
    netlify/functions/dl03-answers.json  CANONICAL DL-03 (MBTA) ledger
    netlify/functions/dl02-answers.json  CANONICAL DL-02 (Florida) ledger
    netlify/functions/dl01-answers.json  CANONICAL DL-01 (Tax Atlas) ledger
    scripts/inject_data.py         Build step: regenerates every embedded page
                                   copy from the canonical ledgers (see below)
    scripts/refresh_dl03.py        Recomputes the DL-03 ledger from the live
                                   FTA NTD API; run by the monthly workflow
    scripts/check_freshness.py     Fails when a ledger ages past its cadence
    scripts/check_style.py         House-style lint (no em dashes) plus the
                                   Florida page's ledger-sentinel checks
    scripts/eval_engine.mjs        Golden-question eval against the live engine
    scripts/check_engine.mjs       Offline payload checks: trigger recall and
                                   coreSlice size (no API key)
    scripts/dl01-research-pass.md  Runbook: weekly DL-01 deep research pass
                                   (Cursor Automation, Monday 9:00 AM ET)
    scripts/dl02-research-pass.md  Runbook: Florida quarterly refresh (local)
    NEW-TOOL-CHECKLIST.md          The playbook for adding a DL-XX tool
    .github/workflows/             GitHub Actions (DL-03, checks, eval; Step 7)
    netlify.toml                   Site, functions, and the build command
    SETUP.md                       This file

Single source of truth: the canonical files above are the only ones you edit.
Everything marked GENERATED, and every DATA:BEGIN/END block inside the pages,
is rewritten by scripts/inject_data.py, which runs locally (python3
scripts/inject_data.py) and as the Netlify build command on every deploy, so
pages can never ship out of sync with the ledgers. Edit a canonical file,
run the script (or just push; the build runs it), and every copy follows.

## Step 1: Get an Anthropic API key (5 minutes)

1. Go to console.anthropic.com and sign in or create an account.
2. Billing: add a payment method, then set a MONTHLY SPEND LIMIT
   (Settings > Limits). Recommended: 10 to 25 dollars for the prototype.
   This is the hard cost ceiling; usage stops at the cap.
3. API Keys > Create Key. Name it datalabs-prototype. Copy the key
   somewhere safe (a password manager). You will paste it into Netlify in
   Step 3. NEVER put it in this repository.

## Step 2: Put this repository on GitHub (5 minutes)

Browser path (no tools needed):
1. github.com > New repository. Name: datalabs-prototype. Private is fine.
2. On the empty repo page choose "uploading an existing file" and drag the
   entire contents of this folder in (keep the folder structure: the
   netlify/functions folder must arrive intact). Commit.

Command line path:
    cd datalabs-prototype
    git init && git add -A && git commit -m "DataLabs prototype"
    git remote add origin https://github.com/YOURNAME/datalabs-prototype.git
    git push -u origin main

## Step 3: Deploy on Netlify (10 minutes)

1. app.netlify.com > Add new site > Import an existing project > GitHub.
   Authorize Netlify to see the repository and select datalabs-prototype.
2. Build settings: leave the build command EMPTY; publish directory "." .
   netlify.toml handles the rest. Deploy.
3. Site configuration > Environment variables > Add a variable:
      Key:   ANTHROPIC_API_KEY
      Value: (paste the key from Step 1)
   Scope: all. Save.
4. Deploys > Trigger deploy > Deploy site (so the function picks up the
   variable).
5. Your site is live at https://SOMETHING.netlify.app (rename under
   Site configuration > Site details > Change site name, e.g.
   datalabs-prototype.netlify.app).

## Step 4: Test the three behaviors (5 minutes)

Open the site, Ask tab:
1. "Is commuter rail back to 2019 levels?"  -> a sourced DL-03 ANSWER with
   (SRC-301) citations and follow-up questions.
2. "What does home insurance cost in Miami-Dade?" -> a sourced DL-02 ANSWER
   with (SRC-FL-01) citations and a link into /florida-insurance/.
3. "Is my town safe?"                        -> ROUTES to Your City & Town.
4. "Is the Red Line safe?"                   -> honest DECLINE (out of the
   dataset's scope), logged.
5. Click through to /mbta/, /florida-insurance/, and /tax-atlas/ and check
   each flagship loads.

If the answer box says the engine hit a snag: check the function log
(Netlify > Logs > Functions > ask) and confirm the environment variable is
set and a redeploy happened after setting it.

## Step 5: Watch cost and usage

- Anthropic console > Usage: each question is roughly a cent; the spend
  limit from Step 1 is the ceiling.
- Netlify > Usage: the free plan is credit-capped; the prototype's traffic
  is negligible, but know that exceeding the cap pauses the site until the
  next month rather than billing you.
- Coverage gaps: every question lands in the Excel workbook from Step 6,
  and the ones the engine could not answer get their own Unanswered tab.
  That tab is the research agenda input. Questions also appear in the
  ask function log (Netlify > Logs > Functions > ask) either way.

## Step 6: Capture questions in an Excel workbook (10 minutes)

Every question visitors ask is filed into an Excel workbook in your
OneDrive or SharePoint, with unanswered questions on their own tab.
This uses Power Automate to receive the site's webhook; the flow's
HTTP trigger requires a Power Automate premium license on work
accounts. If you do not have one, say so and the engine can write to
Microsoft Graph directly instead.

Part A, the workbook:
1. In OneDrive (or a SharePoint library), create a workbook named
   "DataLabs question log.xlsx".
2. On Sheet1, enter headers in row 1: When (UTC), Question, Outcome,
   Tool, Engine note. Select them, Insert > Table (my table has
   headers). On the Table Design tab, name the table: AllQuestions
3. Add a second sheet. Headers: When (UTC), Question, Engine note.
   Insert > Table, and name it: Unanswered

Part B, the flow:
1. Go to make.powerautomate.com > Create > Instant cloud flow >
   skip, then choose the trigger "When an HTTP request is received".
   Set "Who can trigger the flow" to Anyone.
2. In the trigger, paste this Request Body JSON Schema:

       {"type":"object","properties":{
        "at":{"type":"string"},"q":{"type":"string"},
        "type":{"type":"string"},"tool":{"type":"string"},
        "note":{"type":"string"}}}

3. Add a step: Excel Online (Business) > "Add a row into a table".
   Pick the workbook and the AllQuestions table, and map the columns
   to the trigger's dynamic content: at, q, type, tool, note.
4. Add a Condition: type is equal to none. In the If yes branch, add
   another "Add a row into a table" for the Unanswered table, mapping
   at, q, and note.
5. Save. Open the trigger step and copy the HTTP POST URL it
   generated. The URL contains its own signature, so treat it like a
   key.

Part C, connect the site:
1. Netlify > Site configuration > Environment variables > Add:
      Key:   QUESTION_LOG_URL
      Value: (the HTTP POST URL from Part B)
   Scope: all. Save, then Deploys > Trigger deploy.
2. Test: ask the site "Is the Red Line safe?" (a scripted decline).
   Within a few seconds the question appears on both tables, and the
   flow's run history shows a green run.

Notes: logging is fire-and-forget with a short timeout and can never
break the ask box; to revoke, turn the flow off or remove the
variable.

## Step 7: The automation (5 minutes, no secrets on GitHub)

The Anthropic API key lives in exactly one place: Netlify. GitHub holds no
secrets. The only configuration is one PUBLIC repository variable so the
eval can find the site: GitHub repo > Settings > Secrets and variables >
Actions > Variables tab > New repository variable, name SITE_URL, value
https://YOUR-SITE.netlify.app (the site URL is public anyway).

    dl03-refresh.yml   Monthly. Refetches MBTA ridership from the FTA NTD
                       API, recomputes the ledger, and opens a PULL REQUEST.
                       Review the diff (historical revisions show up there),
                       merge, and the deploy carries the new data. First
                       run: Actions tab > DL-03 monthly refresh > Run
                       workflow.
    checks.yml         Weekly and on every PR. Fails when a ledger ages past
                       its publisher cadence, when a generated page block is
                       out of sync with its canonical ledger, or when the
                       engine manifests do not load.
    eval.yml           Weekly. POSTs golden questions to the LIVE site's ask
                       endpoint and asserts each routes to the right tool
                       with a cited, linked answer. The key stays in
                       Netlify; the workflow only needs SITE_URL, and skips
                       politely until that variable exists. This is the
                       regression net for prompt edits.

    The DL-01 research pass is editorial (hearings, ballots, dockets,
    citations). It is deliberately NOT a GitHub Actions scraper. Schedule
    it as a Cursor Automation that follows scripts/dl01-research-pass.md,
    opens a draft pull request, and never merges. The checks workflow's
    45-day freshness gate is only the backstop; the weekly pass rechecks
    every register source, not just the ones that are due.

    Create the Automation (paid Cursor plan; billed as cloud-agent usage):

    1. Open cursor.com/automations/new (or Agents Window > Automations,
       or type /automate in a local Agent chat).
    2. Trigger: Scheduled. Cron:
           CRON_TZ=America/New_York 0 9 * * 1
       That is Monday 9:00 AM Eastern, including DST. If the UI rejects
       CRON_TZ, crons are UTC: use 0 13 * * 1 during EDT and 0 14 * * 1
       during EST. Confirm the first fire time. Runs may be late, never
       early.
    3. Repository: attach jcalabr3ez/datalabs-prototype, branch main.
       Scheduled triggers default to no repository; without a repo the
       agent cannot edit code or open a PR.
    4. Model: pick the most capable model. Automations always get max
       context.
    5. Tools: Pull request creation on, Memories on, Computer use on.
    6. Paste the prompt from the top of scripts/dl01-research-pass.md.
    7. Save and activate. The next Monday run should open a draft PR.
       Review the changelog, then merge to main to deploy.

    A human can still run the same pass on demand by pasting that prompt
    into a Cloud Agent. Either way: do not push main; merge the PR.

Nothing in the automation pushes to main; refreshes land as pull requests a
person reviews. Merging to main is what deploys.

## Later: moving to Pioneer accounts

- GitHub: repo Settings > Transfer ownership > pioneer organization.
  History, issues, and redirects all survive.
- Netlify: site can be transferred between teams in site settings;
  reconnect the repo and re-enter the environment variable after transfer.
- Do both BEFORE circulating a custom domain publicly, or put
  datalabs.pioneerinstitute.org in front first so the move is invisible.
