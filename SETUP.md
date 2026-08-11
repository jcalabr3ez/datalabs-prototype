# DataLabs Prototype: Setup (GitHub + Netlify + Anthropic API)

Time: about 30 minutes. No local tools required; every step can be done in
a web browser. If you prefer the git command line, Step 2 has that path too.

## What is in this repository

    index.html                     Front door (Ask, All Tools, By Geography, Sources)
    catalog.json                   The catalog: 10 topic categories with their
                                   legacy dashboards, plus the three flagships
                                   (DL-04, DL-10, DL-12) and the archive (page copy)
    mbta/index.html                DL-12 Transportation & MBTA flagship page
    mbta/answers.json              DL-12 answer layer (derived from recovered data)
    florida-insurance/index.html   DL-10 Florida Insurance Watch flagship page
    tax-atlas/index.html           DL-04 State Tax Atlas flagship page
    netlify/functions/ask.js       The engine: holds the API key, answers or routes
    question-log.gs                Apps Script that files questions into a spreadsheet
    netlify/functions/catalog.json Engine copy of the catalog
    netlify/functions/dl12-answers.json  Engine copy of the DL-12 answer layer
    netlify/functions/fl-answers.json    DL-10 answer ledger (engine only)
    netlify.toml                   Tells Netlify where the site and functions live
    SETUP.md                       This file

Note: catalog.json and the DL-12 answers file exist in two places (page copy
and engine copy). For the prototype, edit both if you change one. The
production build script eliminates this duplication. The DL-10 ledger
(fl-answers.json) lives only in the engine.

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
1. "Is commuter rail back to 2019 levels?"  -> a sourced DL-12 ANSWER with
   (SRC-301) citations and follow-up questions.
2. "What does home insurance cost in Miami-Dade?" -> a sourced DL-10 ANSWER
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
- Coverage gaps: every question lands in the spreadsheet from Step 6,
  and the ones the engine could not answer get their own Unanswered tab.
  That tab is the research agenda input. Questions also appear in the
  ask function log (Netlify > Logs > Functions > ask) either way.

## Step 6: Capture questions in a spreadsheet (5 minutes)

Every question visitors ask can be filed into a Google Sheet you own,
with unanswered questions on their own tab. The sheet opens in Excel
any time (File > Download > Microsoft Excel, or open it from Drive).

1. Go to sheets.new and name the spreadsheet, e.g. "DataLabs question
   log". Use the Google account that should own the record.
2. Extensions > Apps Script. Delete the sample code and paste in the
   contents of question-log.gs from this repository. Save.
3. Deploy > New deployment > Web app.
      Execute as:      Me
      Who has access:  Anyone
   Authorize when prompted, then copy the web app URL it gives you.
4. Netlify > Site configuration > Environment variables > Add:
      Key:   QUESTION_LOG_URL
      Value: (the web app URL from step 3)
   Scope: all. Save, then Deploys > Trigger deploy so the function
   picks it up.
5. Test: ask the site "Is the Red Line safe?" (a scripted decline).
   Within a few seconds the question appears on both the All questions
   tab and the Unanswered tab.

Notes: the web app URL is unguessable but public, so treat it like a
key; logging is fire-and-forget and can never break the ask box; to
revoke, delete the deployment in Apps Script or remove the variable.

## Later: moving to Pioneer accounts

- GitHub: repo Settings > Transfer ownership > pioneer organization.
  History, issues, and redirects all survive.
- Netlify: site can be transferred between teams in site settings;
  reconnect the repo and re-enter the environment variable after transfer.
- Do both BEFORE circulating a custom domain publicly, or put
  datalabs.pioneerinstitute.org in front first so the move is invisible.
