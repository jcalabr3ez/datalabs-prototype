# DataLabs usability and design review

Internal beta, August 17, 2026. Walkthrough of the front door, the ask box, all five flagships, the 27-app suite, Status, and Changelog. Live site is behind staff auth, so this is from the current compiled pages and interaction code, not a public session.

The product already has a strong editorial spine: one public question, one large number, a matching first figure, a source on every cell, and Pioneer chrome. The gaps below are mostly orientation, consistency, and the last mile of lookup tools. They are the difference between "a catalog of verified pages" and "the thing Pioneer staff reach for in a brief."

House style in this note: no invented figures. Recommendations are product and interface, not ledger changes.

## What already works

- The finding-first layout (question, number, context, cite) is the right pattern for a research institute. Staff can quote a page without hunting.
- Copy citation, source ids, mixed-vintage banners, and "what this page does not cover" build trust. Keep those; they are the product.
- Fifty-state maps with a Place control, a Massachusetts gold outline, and a Compare pin are a coherent grammar once you learn one page.
- Flagships that needed a different shape kept it: State Wealth Taxes is a policy atlas, Florida is a briefing with audience views, Pensions has a public-record name search.
- The four Pioneer verticals on the front door match how the Institute talks about its work.

## How to use this note

Items are tagged **Now**, **This month**, or **Later**. Now items are the ones that will show up in the first 15 minutes of a staff tester's session (see `BETA.md`). This month is still inside the September 16 window. Later can wait for a public launch.

---

## 1. Front door

The landing page is currently a dark masthead, an empty ask field, two New Releases tiles, and a closed catalog. That is too little orientation for 31 live applications.

### The catalog starts closed

Every application lives inside four `<details>` verticals, all collapsed. A first-time visitor sees "Every application," a search box, place chips, and four headings. The actual tools are one click away and easy to miss.

**Now:** Open Education by default, or open the vertical that matches the staffer's last visit. Even better: show the first two rows of each vertical as a preview, with "Show all N applications" expanding the rest.

**This month:** Remember which vertical was open. Deep links like `/#area-education` already open a section; the Catalog nav item should land there with Education open, not at a closed list.

### New Releases only features two tools

Florida Homeowners Insurance and State Wealth Taxes are the only tiles. MBTA, electricity, and pensions are equally flagship and more Massachusetts-native. Two dark tiles after a dark masthead also make the page feel unfinished rather than curated.

**Now:** Four tiles, or a "Start here" row of five flagships with one sentence each. Keep Florida and the tax atlas if those are the briefing priorities, but do not hide the T, household power prices, and teacher funding.

**This month:** Rotate the tiles from the question log. If staff keep asking unemployment and migration, those should surface here.

### The ask box has almost no teaching

The field is a Google-style pill with a rotating placeholder (T ridership, Miami-Dade premiums, Massachusetts electricity, Massachusetts unemployment). There are no visible example questions, no "what we can answer," and no hint that a check of the sources takes several seconds.

A staffer who types "What should I write about education this week?" will get a decline. A staffer who types the placeholder will wait 6 to 15 seconds with only "Checking the sources…" and a spinner.

**Now:**
- Put three tappable starter questions under the box (reuse the BETA.md list).
- Add a one-line bound: "Answers come from the 31 live applications. We do not advise, forecast, or invent a number."
- After about three seconds, change the wait copy to "Still checking the ledgers. This usually takes under 15 seconds."

**This month:** Show a short "We can answer" strip that cycles real questions with their tool names. Log declines, but also show two follow-ups when you decline, the way the engine already can.

### Search and place filters are good, then undercut

Catalog search and the All / Massachusetts / 50 States / Florida / Boston chips work. Two problems:

1. Each row shows only the first geography in the catalog record. MBTA Performance is MA and US but the row reads "Massachusetts." College Enrollment is US, MA, and FL but the row reads "50 States." Staff scanning for Florida coverage will miss tools that list US first.
2. The coverage line is the catalog `q`, which often names later views ("with MCAS, attendance, dropouts… as later views"). That is accurate and dense. On a closed accordion it never appears.

**Now:** Show every place as small tags (MA · US), not one label. Keep the coverage line to one clause; move "later views" to the tool page.

**This month:** Let search match the Massachusetts snapshot (`ma` in the catalog), so "915,932" or "Teachers 58.7%" finds the row. Testers will search the number they remember.

### Information architecture vs Pioneer language

About says four verticals: Education, Healthcare, Economic Opportunity, American Citizenship. The catalog.json topics underneath are twelve buckets (340B, Your City & Town, Crime & Justice, and so on) that get remapped. Housing is injected after Economy & Jobs in code, not as a first-class topic in the catalog file.

That is fine if the four doors stay the only navigation. It is confusing when a tool's group ("340B," "Your City & Town") never appears as a heading.

**This month:** Either label the inner groups when a vertical has more than one (Healthcare: 340B, then hospitals and Medicaid), or drop the inner groups from the mental model and keep one flat list per vertical.

### Small front-door friction

- Nav order is Catalog, New releases, About, Status. Testers will hit Catalog first and find it empty. Put New releases first, or rename Catalog to "All 31 applications."
- Changelog is in the footer of Status but not on the front-door nav. Staff who report an error will want to see whether it was already fixed.
- The ASK badge on the two tiles is insider chrome. "Ask this" in sentence case is enough.
- Dismiss (×) on an answer is hover-only. Keyboard and touch users cannot find it. Keep it visible.
- Answers replace the previous result. HISTORY is kept for the model, but the page looks like a single shot. A compact "You asked / Answer" pair, with Clear answer, is enough. Do not build a chat transcript.
- `?ai=0` is documented on Status, not on the box. Fine for beta. For launch, a "Hide ask" control belongs in the masthead.

---

## 2. Ask, on the door and on the tool

The engine is the distinctive feature. The interface does not yet sell it.

### Two ask experiences that do not match

| | Front door | Tool page |
| --- | --- | --- |
| Look | Pill on navy | Square bar under chips |
| Starters | Rotating placeholder | Four audience chips |
| Answer | Text, optional SVG, source, deep link | Text and source only |
| Route to another tool | Linked matches | Reason text, often no link |
| Charts | Mini SVG for a few DL-01/02/03 kinds | None; user must already be on the page |

A staffer who asks on MBTA Performance "What does a household pay for electricity in Massachusetts?" should get a link to Retail Electricity Prices. Today the tool widget often prints a routing sentence without the URL. The front door does this better.

**Now:** Give the tool widget the same "Open the application" link the front door uses. If the answer is on this page, scroll to the deep link (`#view-…`) instead of only printing text.

**This month:** One shared ask component. Same field, same wait copy, same answer card. The navy pill can stay on the front door; the internals should not fork.

### Audience chips teach the wrong lesson

Each tool shows four questions labeled General public, Journalist, Researcher, Policymaker. Pioneer staff are usually one person wearing all four hats. The labels make the chips look like audience filters, not examples.

The researcher chip is often a methodology question ("Are ridership figures unlinked passenger trips…"). That is valuable, and it should not be the second thing a journalist sees.

**Now:** Drop the role labels, or keep one "Try a question" heading and four unlabeled questions. Lead with the public namesake, then a comparison, then a method bound.

**This month:** Make the chips set the field without auto-submitting, so people can edit "Massachusetts" to "Florida" before they wait 10 seconds. Auto-submit is fine as an option, not the only path.

### Declines and scope

The product is right to decline advice, forecasts, and unpublished cells. The decline copy ("We do not cover this yet. Your question has been logged…") is honest and a bit dead.

**This month:** Name the nearest live page: "We do not estimate a household's future premium. Florida Homeowners Insurance has March 2026 averages by county." That is still a decline. It is a useful one.

Pensions already tells the truth: the ask box will not look up a retiree name. Put that same pattern on Legislature Pay, Boston payroll, and hospital lookup. If the page has a find field, the decline should point at it.

---

## 3. Shared tool spine (DL-06 to DL-32, plus electricity, MBTA, pensions chrome)

Most live tools share one shell: sitebar, title, dateline, jump nav, finding, Place, KPIs, map or trend, ask chips, later views, related apps, source register, footer disclaimer.

That consistency is an asset. The spine is also overloaded.

### Too many controls stacked on fifty-state pages

Retail Electricity Prices, 340B, Housing Permits, State Unemployment, and the other US tools can show, in order:

1. Place (51-jurisdiction select)
2. Copy citation
3. Mixed-vintage note
4. Three KPIs
5. Map tabs (Households / All-sector / Sales / Generation / Table)
6. Census region chips
7. Compare (second state)
8. Show: All / Above U.S. / Below U.S. / Top 10 / Bottom 10

That is a statistics package, not a briefing. A staffer who wanted "what does Massachusetts pay" has already been answered in the hero. The rest is for exploration, and it competes with the finding.

**Now:** Keep Place next to the hero number. Move region, compare, and top/bottom behind an "Explore the map" disclosure, default open on desktop and closed on a phone.

**This month:** Clicking a state on the map should set Place, not only open the table. The hero question and number should follow the map. Today Place and the map can tell two stories.

### Jump nav truncates and hides

On a phone the jump is a `<details>` labeled "On this page." On a laptop the links wrap. Later-view titles longer than 36 characters are cut with an ellipsis ("Massachusetts legislator payroll b…", "Participating 340B sites by entity…"). `JUMP_SHORT` already has good short names for schools; most later views do not.

**Now:** Finish the short-name list. "Pay components," "Entity mix," "Charity-care share," "Top earners."

**This month:** Make the jump sticky under the sitebar. Long suite pages (Massachusetts Schools, 340B, College Enrollment) are easy to get lost in.

### Ask chips sit below the first figure

On suite pages the namesake question is at the top, Figure 1 comes next, and "Ask this page" is after that. On State Wealth Taxes and Florida, ask is above the distinctive UI, which is better.

**Now:** Put "Ask this page" directly under the hero number, before Figure 1. People who want the chart will scroll. People who want a sentence will not hunt.

### Finders are duplicated

Massachusetts Hospitals has "Look up a hospital" (proof card) and later "Find a hospital" on the full table. Town Profiles has the same pair. Legislature Pay has a jump-to-row field on the table, which is the right control, plus a histogram that is not the job.

**Now:** One find field per page, at the top for lookup tools. The table filter can be the same field, not a second one.

### Town Profiles opens on Boston

The public question is "What is the population of Boston?" For a Pioneer municipal tool, the first act should be typing a town. Boston as the default number is defensible (largest, cited often). The lookup still sits below the KPIs and a choropleth of 351 places that is hard to click.

**Now:** Promote "Type a city or town" into the hero. Keep Boston as the empty-state example.

**This month:** A searchable combobox with typeahead, not a free-text field that fails on "St. " vs "Saint." Peers (Beverly as Boston's ACS peer) are a distinctive feature; show them on the find card, not only in a KPI.

### Later views feel like leftover Tableau sheets

Massachusetts Schools stacks Chapter 74, CTE programs, MCAS, district spending, race, selected populations, per-pupil spending. 340B stacks sites, charity care, legislative mapping, entity mix, pharmacies. Each chart is honest. Together they read as "we had to park the old workbooks somewhere."

**This month:** Group later views under labeled subheads ("In Massachusetts," "School finance") and collapse all but the first. Or turn later views into tabs on Figure 1, the way electricity already does for Households / All-sector.

Do not invent new series. This is layout, not coverage.

### Related applications are a quiet win

Suite pages link three peers. Flagships do not. MBTA should point to Transit Systems. Electricity should point to State Energy Emissions. Pensions should point to Legislature Pay and State Payroll. Florida should point to Housing Permits.

**Now:** Add the same related block to the five flagships.

### Source register is excellent and buried

Cadence, vintage, next release, and exclusions are the reason a researcher will trust the page. They sit in a collapsed fold at the bottom, after a long disclaimer.

**This month:** One persistent "Data through {vintage} · {N} sources" line under the dateline, linking to the register. Keep the fold. Do not make people scroll past every chart to see whether the file is 2022 or 2025.

### "see the register" on Figure 1

Several trend source lines say "Source: see the register" instead of the publisher name. The hero is more precise. Figure 1 is what gets screenshotted into a slide.

**Now:** Print the same source name the KPI already uses.

---

## 4. Flagships, one by one

### State Wealth Taxes (`/tax-atlas/`)

This is the richest interface in the catalog: five views (Current Policy, Active Proposals, Ballot Access, Near-Term Risk, Events), a 51-tile grid, a sticky detail panel, a filterable legend, and a 26-event watch list.

What to keep: the tile plus panel pattern. Selecting a state without leaving the map is the right interaction for a 51-jurisdiction legal record.

What to change:

- **Now:** The 12-column tile grid has `min-width: 640px`. On a phone it is a horizontal scroll of squares. Use the same 51-cell tile map the suite already has (`us-map.js` Option B), or a two-column list grouped by status.
- **Now:** Sitebar omits Status (Florida does too). Add the same three links every other tool has: catalog, About, Status.
- **This month:** Near-Term Risk is a Pioneer model last scored July 28, 2026. That bound is in the lede. It should also be a visible badge on the Risk view, because tiles will be read as predictions.
- **This month:** Events is a long accordion of prose. Add a filter by state and a "resolved / upcoming" chip. Missouri already has a resolved August 4 item mixed into a November heading.
- **Later:** Gold hover on links, gold tab underline, gold footer stripe. Suite pages use navy underline and no gold footer rule. Pick one accent language. Gold as Massachusetts-and-risk, navy as chrome, is enough.

The ask chips sit above the views, which is correct. Wiring "Which states are considering a wealth tax?" to the Active Proposals view (not only an answer card) would make the atlas feel like one product.

### Florida Homeowners Insurance (`/florida-insurance/`)

This is a briefing, not a dashboard: homeowner / policymaker / report card views, a county map, focus-group pull quotes, reform grades.

What to keep: audience views that actually change the page, the county readout, the report-card grades.

What to change:

- **Now:** Same sitebar as the suite (Status is missing). Same ask-to-map wiring: asking Miami-Dade should select Miami-Dade on the map.
- **Now:** The homeowner view opens on a long prose block before the KPI strip. For staff in a hurry, put the three takeaways first, then the Tampa quote.
- **This month:** County finder is a `<select>` of 67 counties. Typeahead would match how people think ("Dade," "Miami"). The map tooltip is custom and fine; make sure it works on touch (tap to pin, not hover-only).
- **This month:** Report card grades (A–I) need a one-line legend at the top of that view. "I" as incomplete is easy to read as a low grade.
- **Later:** Gold vs navy inconsistency with the suite, same as the tax atlas.

### MBTA Performance (`/mbta/`)

Clear namesake (88.1 percent of June 2019), mode recovery, service vs riders, reliability with an honest subway exclusion, cost per trip.

What to keep: the exclusion for subway Excess Trip Time. The math disclosure under Figure 1.

What to change:

- **Now:** Catalog and standfirst must keep saying that other U.S. agencies live on Transit Systems. Add a related link at the bottom. Staff will search "ridership" and land on the wrong page.
- **This month:** Reliability vintages differ by mode (bus through May 2026, The RIDE through July 2025). A small "as of" on each reliability chart would prevent a false apples-to-apples read.
- **This month:** Jump links are the cleanest in the catalog (The finding, Ridership, Service, Reliability, Costs). Use this as the template for suite short names.

### Retail Electricity Prices (`/electricity/`)

This is the suite pattern at its best and its most crowded. Household vs all-sector is the important distinction, and the map tabs encode it.

**Now:** Default Place can stay United States, but Massachusetts staff will change it immediately. A "Massachusetts" chip next to Place would save a 51-item dropdown.

**This month:** Collapse the explore stack (region, compare, bands) as in section 3. Keep Households / All-sector as tabs. Sales and Generation are later views; they do not need equal weight with the namesake.

### Massachusetts Public Pensions (`/pensions/`)

Two products on one URL: a 105-board funded-status briefing, and a CTHRU last-name search of 133,563 State and Teacher retirees.

What to keep: the explicit note that ask will not look up a name. The public-record framing.

What to change:

- **Now:** Put Name search in the hero jump as a button-weight control, not the fourth link. Testers who come for a person will not find it under "The finding."
- **Now:** Last-name search has no submit button and no example result until you type. Show "Try Manning" as a ghost example, and a visible Search button for accessibility.
- **This month:** Board selector on the funded-ratio trend is a long `<select>`. Typeahead, with State and Teachers pinned at the top.
- **This month:** The page mixes January 2023 valuations, 2023 returns, 2025 payroll, and 2026 year-to-date names. The dateline already lists them. Repeat that mix in the vintage banner used on suite pages, so it is not only in 12-point gray under the title.

---

## 5. Suite tools that need a different shape

Most suite pages can stay on the spine. These should not.

### Lookup tools (treat as finders, not rankings)

- **Massachusetts Town Profiles** and **Town Rankings:** type-a-town first. The 351-polygon map is a supporting exhibit.
- **Massachusetts Hospitals:** type-a-hospital first. CMS stars as a distribution chart second.
- **Legislature Pay:** type-a-member first. The Speaker/President $223,720 hero is a good headline; the job is the table.
- **Boston City Payroll** and **Massachusetts State Payroll:** department or name search first. Top earners as a later view is correct.

### Split pairs that staff will mix up

| Pair | Why it breaks |
| --- | --- |
| MBTA Performance vs Transit Systems | Both say ridership. One is the T, one is 518 agencies. |
| State Migration vs Taxpayer Migration | Census people vs IRS returns. Catalog coverage lines are close. |
| Massachusetts Tax Collections vs State Tax Collections | Same QTAX figure, one is MA-only. |
| Town Profiles vs Town Rankings | Profile vs change ranking is a fine split if the catalog says so in six words. |
| Retail Electricity Prices vs State Energy Emissions | Price vs CO2. Related, not duplicates. |
| Charter Enrollment vs Massachusetts Schools | National charters vs DESE. The charter page's teacher charts are all public schools, which the coverage line already warns about and the page still makes easy to misread. |

**Now:** One extra clause on each catalog row that names the sibling: "Not the MBTA-only page." "IRS returns, not Census population."

### Housing Permits

House-price charts were removed (changelog, August 16) and the ask ledger still knows FHFA and Case-Shiller. The page title and standfirst are only permits. That is honest. The catalog should not imply a housing-market dashboard.

**This month:** If staff keep asking prices, either restore a later view from the existing ledger cells or decline with a pointer to the source. Do not leave a ghost feature only the model knows about.

### Vehicle-Miles Traveled (`/roads-risk/`)

The namesake is VMT. FEMA, the National Risk Index, and degree days are later views. The URL still says `roads-risk`. Staff who remember the Tableau "risk" workbook will look for a risk hero and get miles driven.

**This month:** Rename the URL only if you must; for beta, lead the standfirst with "Miles driven, then FEMA risk as a later view."

### 340B Drug Discounts

Three former workbooks on one page (sites, charity care, legislative mapping). The mixed-vintage banner is doing real work (OPAIS daily vs CMS FY 2023 vs 2024 districts).

**This month:** Three jump-level sections with their own findings, not one hero (64,413 U.S. sites) and a scroll of unlike charts. Legislative mapping is a different question from site counts.

### Patents by State

The only in-build page still looks like a live tool: same sitebar, same footer, dateline "pending · Revised 15 August 2026." A Tableau card is the only content.

**Now:** A single in-build banner at the top: "No DataLabs figures yet. The USPTO workbook remains on usdatalabs.org." Dim the chrome that implies a finding. Do not load Chart.js on a page with no chart.

### Cost of Living, State GDP, Business Formation, State Unemployment

These are the spine at its cleanest. Prioritize Place chips for MA and FL, then the explore disclosure. No special layout required.

---

## 6. Status and Changelog

### Status

Useful for operators, opaque for testers. "Within gate (596d / 700d)" next to electricity's 2024 vintage looks like a stale error. The About page already explains that an old vintage can be the latest official file. Status undoes that reassurance.

**Now:** Two columns humans care about: Data through (in words) and Last compiled. Move gate math and GitHub Action names behind "For maintainers."

**Now:** Drop `?ai=0` from the public Status lede. Testers do not need the kill switch in the first paragraph.

### Changelog

August 16 has dozens of entries, many of them engineering ("Ask can answer a named-state participation rate," "Insight bars draw again"). A staffer checking "did you fix the thing I reported?" cannot scan this.

**This month:** Group by day, then by tool. Lead with user-visible changes (catalog names, missing charts, citation). Collapse "Ledgers were not rebuilt" hygiene into one line.

---

## 7. Accessibility, mobile, and visual system

### Contrast and type

- Masthead deck ("One-month internal beta…") is `#8DA0B5` on `#293C5C`. That pairing is likely under 4.5:1. Lighten the steel or darken the navy overlay.
- Gold `#CCB26D` on navy for Beta, ASK, and chip borders fails for 10px uppercase. Use gold for large serif or for rules, not for 10px labels.
- Catalog tiles `#CAD3E2` with navy type are fine at rest. Hover `#859DC1` with navy is tighter. A hairline, not a fill change, would be safer.
- `--mono` is Roboto, the same as UI sans. Source ids and math would read more clearly in a real tabular mono.
- Libre Bodoni at clamp 36–52px for the hero number is handsome. On electricity, `16.48¢` in sans tabular is more readable. Keep Bodoni for titles; use Roboto for the number.

### Keyboard and screen readers

- Focus rings exist (`focus-visible` on navy or gold). Tax atlas uses gold; suite uses navy. Pick navy everywhere on white, white on the navy bar.
- Map states are clickable; confirm they are in the tab order with a name and value. Tile maps (`usmap.is-tile`) are better for keyboard than SVG paths.
- Chart.js canvases have no data table alternative except the Table tab. Keep that tab, and make sure a state click actually opens it (electricity copy says it does).
- Ask answer region on the front door has `aria-live="polite"`. The tool widget does not.
- No skip-to-content link. The sitebar is short, so this is Later, not Now.
- Hover-only dismiss and hover-only map highlights fail on touch and on fine-pointer settings.

### Mobile

- Front-door ask pill is fine. Catalog chips wrap. Verticals as full-width accordions are the right mobile pattern if at least one is open.
- Tax atlas grid and Florida county SVG need a list fallback under 700px.
- Sticky detail panel on the tax atlas (`max-height: calc(100vh - 28px)`) is desktop-only thinking; on mobile it should sit under the selected tile, not in a second column.
- Suite KPI strips become a vertical stack. Three KPIs plus a full-width source cell is a lot of repeated SRC lines. One source line under the strip is enough (several pages already do this).

### Motion and wait

- `scroll-behavior: smooth` on the front door is fine. Respect `prefers-reduced-motion`.
- 6 to 15 second asks need a determinate cue if you can (even a 15-second CSS bar). A looping spinner feels hung at second eight.

### Print and cite

Staff will print or PDF a finding into a briefing. There is no print stylesheet. Hero, Figure 1, source line, and cite text should survive "Save as PDF." Hide the sitebar, ask box, and related links.

**This month:** `@media print` on the shared CSS. This is high leverage for the actual job.

---

## 8. Consistency checklist (chrome drift)

These are small and they add up to "is this one product?"

| Element | Front door | Suite / MBTA / pensions / electricity | Tax atlas / Florida |
| --- | --- | --- | --- |
| Sitebar links | Catalog, New releases, About, Status | Catalog, About, Status | Catalog, About (no Status) |
| Link hover | Underline, ink | Underline, navy | Gold |
| Tab/toggle underline | n/a | Navy | Gold |
| Footer gold rule | No | No | Yes (3px) |
| Ask UI | Navy pill | Square bar | Square bar |
| Finding block | n/a | Question + number | Audience views, no shared hero |
| Changelog link | Footer of About only | Some footers | Florida feedback box |

**Now:** One sitebar component. One footer. One hover color on white pages (navy). Reserve gold for Massachusetts marks, Beta, and the tax atlas risk tiles.

Also: tax-atlas and Florida still duplicate large CSS that already lives in `datalabs.css` and `suite.css`. That is a maintenance issue that becomes a visual drift issue.

---

## 9. Suggested sequence for the rest of the beta

Do not try to restyle the institute. The paper look is working. Sequence by tester pain:

1. **Orientation (day one of remaining tests)**
   - Open a catalog vertical by default.
   - Starter questions under the front-door ask box, plus honest wait copy.
   - In-build banner on Patents.
   - Related links on the five flagships.
   - Status + Changelog in every sitebar.
   - Place tags for every geography on a catalog row.

2. **Ask as a product**
   - Tool-page answers get deep links and route links.
   - Chips do not auto-submit; drop role labels.
   - Declines name the nearest page or on-page finder.

3. **Lookup tools behave like lookup tools**
   - Town, hospital, legislator, retiree name: one field at the top, typeahead, example query.
   - Pensions name search visible from the hero.

4. **Calm the fifty-state spine**
   - Place stays. Region / compare / bands move into Explore.
   - Map click sets Place.
   - Jump short names and a sticky jump.
   - Figure 1 source line names the publisher.

5. **Staff-facing ops**
   - Status in words, not gate ratios.
   - Changelog grouped by tool.
   - Print stylesheet for the finding + Figure 1.

6. **Flagship mobile and a11y**
   - Tax atlas list fallback.
   - Florida takeaways first.
   - Contrast on masthead steel and gold-on-navy labels.
   - Visible dismiss controls.

---

## 10. What not to do in this beta

- Do not add a download portal. BETA.md is clear. Print/PDF and copy citation cover the brief.
- Do not turn ask into a chatbot with a persistent thread. One question, one cited answer, one link is the brand.
- Do not invent a U.S. total, a Near-Term Risk rescore, or a Patents figure to make a page feel finished.
- Do not merge the Florida standalone export or reopen that workstream.
- Do not put five more New Releases tiles that look like marketing cards. Two or five flagship briefings, set in the same type as the catalog, is enough.
- Do not hide SRC ids. Researchers want them. You can move them to the meta line and off the 52px number.

The bar for public launch is not more applications. It is: a staffer can land, ask one real question, reach the page, change Place to Massachusetts, copy a citation, and trust the vintage, in under a minute, on a laptop and a phone.
