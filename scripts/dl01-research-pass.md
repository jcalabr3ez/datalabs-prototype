# DL-01 weekly research pass (Monday 9:00 AM ET)

This is the canonical prompt for the **weekly deep update** of the Pioneer Institute DataLabs wealth-tax atlas (DL-01). A Cursor Automation should follow this file every Monday at 9:00 AM Eastern. A human can also paste it into a Cloud Agent. Read `AGENTS.md` first for deploy and house-style rules.

## Paste this into the Cursor Automation

Create the Automation at [cursor.com/automations/new](https://cursor.com/automations/new). Scheduled triggers default to **no repository**; attach `jcalabr3ez/datalabs-prototype` on branch `main` or the agent cannot edit code or open a PR.

**Name:** DL-01 weekly deep research pass

**Trigger:** Scheduled. Cron (preferred, stays on 9:00 AM Eastern through DST):

    CRON_TZ=America/New_York 0 9 * * 1

If the UI rejects `CRON_TZ`, use UTC and change it when the clocks change:

    0 13 * * 1    # 9:00 AM EDT (mid-March through early November)
    0 14 * * 1    # 9:00 AM EST (early November through mid-March)

Confirm the first fire time in the UI. Scheduled runs may be late; they should not start early.

**Repository:** `jcalabr3ez/datalabs-prototype`, branch `main`.

**Model:** the most capable model in the picker. Automations always get that model's maximum context window.

**Tools:** Pull request creation on (default). Memories on (default). Computer use on (default) so the agent can open dockets and SOS pages. Do not enable merge or any "push to main" action.

**Prompt to paste:**

    Follow scripts/dl01-research-pass.md exactly. This is the weekly deep
    research pass for the Pioneer DataLabs State Tax Atlas (DL-01).

    Launch five parallel research agents and recheck every source in the
    atlas register, not only sources due under the 45-day freshness gate.
    The August 11, 2026 pass (five agents, then a 47-source register; the
    register is now 48) is the depth reference.

    Edit netlify/functions/dl01-answers.json as the source of truth. Run
    python3 scripts/inject_data.py. Then update the hand-authored hero
    dateline, methodology state of play, source-register table, and footer
    so they match the new as_of. Run python3 scripts/check_style.py,
    python3 scripts/check_freshness.py, and node --check
    scripts/check_engine.mjs.

    Open a DRAFT pull request against main using the PR body template in
    the runbook. Do not merge. Do not push main. Production deploys from
    main via Netlify; the human merges when they want the site to update.

    Do not invent Near-Term Risk rating changes. Ratings were last scored
    July 28, 2026. Update an existing PR only if it is a draft whose
    title starts with DL-01. Ignore the Florida export branch. If no
    DL-01 draft exists, open a new one.

    Memories: store the open PR URL, unreachable sources, and any
    "checked, no change" notes so next Monday does not duplicate work.

## Goal

Do the **deepest possible** research pass over the full source register. Check **every** cited source for a newer official page, statute, forecast, filing, or news report. Update the ledger and the hand-authored atlas copy so the live page can be redeployed after human review.

This is **not** a freshness-only pass. Do not stop at "due in 45 days." Recheck sources that were verified last week. The August 11, 2026 pass is the depth reference: five parallel research agents, then a 47-source (now 48-source) register.

## Hard rules

1. **Open a draft pull request. Do not merge. Do not push `main`.** Production deploys from `main` via Netlify. The human reviews the changelog and merges when they want the site to update.
2. **Edit `netlify/functions/dl01-answers.json` as the source of truth.** Then run `python3 scripts/inject_data.py`. Do not hand-edit generated `DATA:BEGIN` / `DATA:END` blocks in `tax-atlas/index.html` or `index.html`.
3. **Hand-authored copy is not generated.** After inject, update the hero dateline, methodology "state of play," source-register table (count, vintages, URLs), and footer so they match the new `as_of`.
4. **Do not invent Near-Term Risk tier changes.** Ratings were last scored July 28, 2026. Keep that date. Recalibrate only if the human later asks for a model rescore.
5. **Do not invent facts.** If a source is unreachable, say so and keep the last verified figure. Prefer official pages (legislature, SOS, DOR, courts, CBO, OECD) over press. News is allowed when it is the only public record of a new filing or forecast.
6. **House style:** no em dashes. Spell out million and billion in prose. Keep `$` on figures. Use `YYYY-MM-DD` in the ledger.
7. **Schema:** 51-jurisdiction atlas (`states`, `events.phases`, `meta`, `captions`, `default_sources`, `state_sources`, `derived`). Do not revert to the older 16-state events-array schema.
8. **Update an existing PR only if it is a draft whose title starts with `DL-01`.** Ignore every other open or closed PR, including the Florida standalone export on `cursor/florida-standalone-export-614f`. If no DL-01 draft exists, open a new one.

## Schedule and trigger

- **When:** every Monday at 9:00 AM America/New_York.
- **Cron (if the UI accepts a timezone):** `CRON_TZ=America/New_York 0 9 * * 1`
- **Cron (UTC fallback while Eastern Daylight Time is in effect, March–November):** `0 13 * * 1`
- **Cron (UTC fallback while Eastern Standard Time is in effect, November–March):** `0 14 * * 1`
- Confirm the first fire time in the Automation UI. Scheduled triggers may run late. They should not run early.
- Attach repository `jcalabr3ez/datalabs-prototype`, branch `main`.
- Turn **Pull request** on (default). Turn **Memories** on so later runs reuse open-PR and source notes.

## Depth: five parallel research agents

Launch **five** research agents in parallel. Each agent must open every URL in its category, follow "see also" / newer-year links, and search for 2026–2027 updates. Return a structured brief: source, last verified date, what changed, new URL if any, confidence.

### Agent 1: Rates, brackets, enacting legislation

Check every jurisdiction that has a rate, exemption, or surcharge in the ledger:

- Washington SB 6346 / chaptered statute / DOR implementation and first-year collection estimates
- Massachusetts millionaires tax (Question 1, 2022) statutory text and DOR administration
- California Prop 30 (2012) / Prop 55 and any 2026 successor (Prop 40 / 41 / 42)
- New York PIT top rate and NYC local PIT
- New Jersey GIT millionaire's tax
- Oregon personal income tax top rate
- Minnesota top rate and any 2025–26 surcharge bills
- Connecticut, Vermont, Maine, Hawaii, D.C. top rates
- Any new 2026 enactment in the other 40 jurisdictions (explicitly search "wealth tax" / "millionaire tax" / "pied-à-terre" / "exit tax" / "mark-to-market")

Also re-read `default_sources` rate rows and each `state_sources` rate citation.

### Agent 2: Ballot measures and elections

- California Prop 40 / 41 / 42: committee filings, cash on hand, qualification status, Legislative Analyst fiscal
- Massachusetts Question 5 / Amendment 62F: conference committee, ballot title, SOS status
- Colorado Initiative 195 and 232: signature counts, sufficiency deadline, title board
- Washington I-645: PIID, county ballot deadlines, Supreme Court appeal
- Missouri November 2026 measures (official SOS certification vs unofficial tallies)
- Any newly qualified 2026–27 wealth, millionaire, property, or capital-gains measure in all 50 states plus D.C.

Primary homes: Ballotpedia, state SOS election divisions, campaign-finance portals (Cal-Access, OCPF, TRACER, PDC).

### Agent 3: Litigation

- Washington I-645 / PIID at the Washington Supreme Court
- New York City pied-à-terre tax: TRO, appeal, hearing dates, supplemental roll
- Rhode Island second-home / nonresident property suits
- Any new complaint, injunction, or opinion on wealth, millionaire, or exit taxes
- Petter and other named cases in the register: docket check, no-ruling is a finding

Primary homes: state court dockets, Justia, CourtListener, official county clerk notices.

### Agent 4: Revenue data and ballot-access structure

- Washington DOR collection estimates and September official forecast
- Massachusetts DOR FY2026 year-end certification (do not replace the July 20 figure until the official release exists)
- California BOE / FTB / LAO fiscal estimates for Props 40–42
- CBO, Tax Foundation, ITEP, OECD wealth-tax comparative notes used in the register
- Signature thresholds, geographic-distribution rules, and filing deadlines for 2026–27 cycles

### Agent 5: Proposal tracking and model notes

- Active bills that have not become law (keep them in events / captions, not as enacted rates)
- Federal proposals only if they affect the atlas narrative
- Near-Term Risk model: report whether facts have moved enough that a human should rescore. **Do not change ratings or the July 28, 2026 score date.**

## After the five briefs return

1. Set `meta.as_of` (and any `DL01D.as_of`) to today's date (`YYYY-MM-DD`).
2. Update ledger fields that have a verified change. Bump the matching `state_sources` / `default_sources` `as_of` and URL.
3. Increment the source-register count only when a **new** distinct source is added. Replacing a URL with a newer official page of the same document does not add a source.
4. Rewrite captions and event text that would otherwise contradict the new facts.
5. Run `python3 scripts/inject_data.py`.
6. Update hand-authored copy in `tax-atlas/index.html` (and the front-door snippet if it exposes the dateline):
   - Hero: `Verified Month D, YYYY`
   - Methodology state of play
   - Source register heading and table vintages
   - Footer
7. Run `python3 scripts/check_style.py`, `python3 scripts/check_freshness.py`, and `node --check scripts/check_engine.mjs`. Fix failures you introduced.
8. Commit on a feature branch. Push. Open a **draft** pull request against `main`.

## Pull request body (required)

Use this shape so the human can scan in two minutes:

```markdown
## DL-01 weekly research pass (YYYY-MM-DD)

Deep pass. Five parallel agents. Register: N sources. Ledger `as_of`: YYYY-MM-DD.

### Changed
- WA … (old → new). Source: URL
- CA Prop 40 … Source: URL

### Checked, no change
- MA DOR FY2026 year-end still pending. July 20 certification stands.
- Petter: no ruling as of YYYY-MM-DD.

### Unreachable / unverified
- Missouri official SOS certification still not posted.

### Risk model
- No rating changes. Last scored July 28, 2026.
- Human rescore suggested: yes/no. Why.

### Deploy
- Draft PR only. Merge to `main` to publish on Netlify.
```

## Local one-off (same depth, no Automation)

```bash
# In a Cloud Agent or local checkout of main:
# 1. Follow this file.
# 2. python3 scripts/inject_data.py
# 3. python3 scripts/check_style.py && python3 scripts/check_freshness.py
# 4. Open a draft PR. Do not merge.
```

DL-01 is editorial. There is no GitHub Actions scraper for this atlas. DL-03 (MBTA) is the automated API refresh.
