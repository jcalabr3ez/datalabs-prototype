# Charts and value: second-pass UX review

August 17, 2026. This pass is about whether every figure **finishes drawing** and whether it is **worth looking at**. The first review (`UX-REVIEW.md`) covered orientation, Ask, and lookup. Those ten items still stand. This note is the graph language and the features that would make staff actually use the pages in a brief.

Every live tool was checked against the shared Chart.js theme (`assets/chart-theme.js`, `assets/chart-labels.js`), the suite renderer (`scripts/render_suite_pages.py`), the fifty-state map (`assets/us-map.js`), and the flagship charts on MBTA, electricity, pensions, Florida, and the tax atlas.

House style: no invented figures. These are drawing, color, annotation, and layout changes on cells that already exist.

---

## What the charts already get right

- One paper theme: Roboto ticks, square bars, straight lines, hairline grids, ink tooltips. That is a real editorial voice. Do not replace it with rounded dashboard chrome.
- Zero-baseline logic in `dlValueScale` is correct: counts start at zero, NAEP scores and electricity cents do not. Keep the guard in `scripts/check_chart_scale.mjs`.
- End-of-line labels with a white halo, and a right-hand stack when several series finish on top of each other, are the right idea. MBTA's gold end-dot plus dashed 2019 average is the best figure on the site.
- Electricity's US / Massachusetts (gold) / Florida (rust) trend is the color grammar the rest of the suite should copy.
- Tile maps on unemployment, NAEP, cost of living, and imprisonment make small states readable. Geo choropleths are right for magnitudes (sites, dollars, trips).

The problems below are why a staffer still screenshots a Tableau workbook instead of Figure 1.

---

## Completeness bugs (figures that do not finish)

These are the items that make a chart look broken, not merely plain.

### 1. Florida disappears on suite trend lines

Headline trends in `render_suite_pages.py` color Massachusetts gold, the United States ink, Boston navy, and **everything else navy**, including Florida.

```javascript
function trendColor(k){
  if(k==='MA') return GOLD;
  if(k==='Boston') return BLUE;
  if(k==='US') return INK;
  return BLUE;  // Florida lands here
}
```

Electricity and the 340B charity trend already use rust `#C45C26` for Florida. Business formation, GDP, migration, housing, Medicaid, 340B sites, and the rest of the suite do not. On a three-line chart, Florida and a picked extra state are the same stroke.

Insight bars have the same hole: only Massachusetts and Boston get gold. Florida is navy, so a "Compare a state" bar that includes Florida does not mark it.

**Do this:** One color function used everywhere: US ink, MA gold, FL rust, selected extra state navy, everyone else steel. Turn the Florida outline on the geo map back on (`.fl-on`) so the map matches the line.

### 2. End labels get clipped or dropped

Line charts pad 96px on the right; horizontal bars pad 72px. The label plugin then **skips** any label that would sit on a stroke, another bar, or the canvas edge. Thin bars (`thick < 10`) are skipped on purpose.

What staff see: a last point with no number, or a `$2.46 billion` that is cut off. Monthly series (business applications from 2004, MBTA ridership from 2014) use end-only labels, so a miss means the chart has **no** figures on it.

Two-column insight charts sit in `.plot-sm` at a fixed **280px**. Grouped bars add a 36px top legend. Slope charts want 96px of right pad. The remaining plot is too small for the halo labels to land.

**Do this:**
- Measure the longest end-label and pad to that width, not a constant 96px. `$644.18 billion` needs more than `16.48¢`.
- Give every later view `.plot` (about 360 to 400px), not `.plot-sm`. Two-up grids can stay two-up; they need height, not width.
- If a label will not fit, draw it in a reserved right column (the stackEnds path) rather than omitting it.
- Stop drawing on-bar labels when there are more than about eight bars. The axis and tooltip are enough. A half-labeled bar chart looks unfinished.

### 3. Category ticks are ellipsized into nonsense

Y-axis callbacks cut names at 28 or 32 characters (`catTick`). Jump nav already truncates at 36. Hospital names, Chapter 74 programs, and Boston departments become "Massachusetts General Hospi…".

Histograms (Legislature Pay, Pensions funded ratio, Pensions returns) rotate x labels 45 to 60 degrees in 10px type. "58% to 64%" on a diagonal is readable. "$111,864 to $132,000" is not.

**Do this:** Wrap y labels to two lines, or use the short name plus a tooltip. For histograms, print the bin edge as `$112k` / `$132k` at 0° on the baseline, not a rotated range string. Mark the median with a vertical rule and a label, which is the actual story of a pay histogram.

### 4. Maps do not show the number on the geography

Geo maps have no floating tooltip. Hover writes into a "Hover" cell under the legend. On a laptop that cell is below the fold of a 400px map. On a phone there is no hover.

Tile maps print the value in the cell, which is why unemployment and NAEP feel finished and electricity's choropleth does not.

**Do this:**
- Pin the hovered (and selected) state's name, figure, and rank in a box that sits **on** the map, top-right, like Florida's county readout.
- Keep the Highest / Lowest / Massachusetts strip. Move "Hover a state" out of that strip.
- On touch, the first tap selects and pins; a second tap opens the table. Do not require hover.
- Raise `.usmap-svg` max-height from 400px to about 520px on desktop so New England is actually clickable.

### 5. Missing years look like a continuous line

`spanGaps: true` on every suite trend. Pensions funded history and NAEP state series have real gaps. The line interpolates across them. Staff read a smooth recovery that the file does not contain.

**Do this:** Draw the gap. Show a marker on years that exist. A one-line caption already says "Gaps in a line are years with no new valuation." The line should say it too.

### 6. Index charts look like percents

When United States, Massachusetts, and Florida differ by 2.5 times or more, the renderer converts the trend to "index, first year = 100." That is the right statistical choice. The y-axis title is 11px grey. Hover still shows the raw count, but the line the eye follows is an index.

Staff will quote "Massachusetts is at 108" as 108 percent.

**Do this:** Title the figure with the unit in the sentence: "Indexed to each series' first year (100 = starting level)." Put a 100 reference line across the plot, labeled "starting level." Keep the raw figure in the tooltip, in bold, before the index.

### 7. Scatter and histogram Figure 1s are unfinished

Legislature Pay opens on a 10-bin histogram of totals. Dots mode (rank vs value) uses 5px points, a reversed rank axis labeled with `Math.abs`, and no names except on hover. Neither has the end-label / callout treatment.

**Do this:** Legislature Pay's Figure 1 should be a ranked bar of the top and bottom, plus the Speaker and Senate President called out, with the histogram as a later view. If dots stay, label MA / the selected row in the plot, not only in the tooltip.

### 8. Front-door ask charts are a different drawing system

The landing page renders a few MBTA and Florida views as inline SVG (`chartSVG` in `index.html`). Those polylines do not use Chart.js, do not share the label plugin, and only exist for a handful of chart ids. Every other ask answer is text-only.

**Do this:** Stop drawing a second chart language on the front door. Link to the tool at the figure's deep link. If a preview is required, screenshot the real canvas at build time. Two visual systems for the same number trains staff to distrust one of them.

---

## Appeal: make the paper charts look like a Pioneer brief

The theme is institutional on purpose. "Appealing" here means **clear, high-contrast, and annotated**, not decorative.

### 9. One color grammar, used on every mark

| Role | Color | Use on |
| --- | --- | --- |
| United States | `#1A1A1A` ink | US line, US bar, US tile |
| Massachusetts | `#CCB26D` gold | MA line (2px), MA bar, gold outline |
| Florida | `#C45C26` rust | FL line (2px), FL bar, rust outline |
| Selected extra | `#293C5C` navy | the Place / Compare state |
| The rest | `#A9B8C8` steel | other bars in a small-n compare |
| Positive / above | `#177245` | recovery at or above 100%, net decline in a bad series |
| Negative / below | `#8C2F1B` | the inverse |

Today navy is both "the data" and "Florida" and "the extra state." Gold is Massachusetts on maps and also the MBTA 2019 reference line, which is fine if gold means "the thing to watch." Rust is defined and then left off most suite pages.

Legend swatches are 12 by 2 pixels (a hairline). Make them 12 by 8, the same as the map bins.

### 10. Choropleths need a ramp people can read

`NAVY7` is `#F1F4F7, #D2DCE6, #A9B8C8, #7D90A8, #546B86, #3A516C, #293C5C`. The first three steps are pale grey-blue on white. Adjacent states in the middle of the ranking look the same.

The legend is seven wrapping chips ("11.51 to 12.40", …), not a single ramp. Florida's county map already uses a continuous bar. Copy that.

**Do this:** Five bins, not seven, with more contrast between step 2 and step 4. One horizontal ramp under the map, low on the left, high on the right, with three labels (low, U.S. if it exists, high). Keep the gold MA outline. Turn rust FL on.

Diverging scales (migration, taxpayer net) already switch to `DIVERGE7`. Put a white zero tick in the middle of that ramp and say "net gain / net loss" once.

### 11. Lines need a last point, a fill, and fewer wiggles

Suite lines are 1.75px, no points, no fill, grey legend on top. Monthly files from 2004 are a scribble.

**Do this:**
- Gold end-dot on the highlighted series (copy MBTA).
- A 8% navy fill under a **single-series** trend (Massachusetts enrollment, Boston payroll). No fill on three-line compares.
- For monthly series longer than about 60 points, default the view to the last 36 months, with "Full series" as a control. The ledger keeps the history; the first paint should be readable.
- Year labels only on January, which the MBTA chart already does. Several suite trends still dump `2014-01, 2014-02, …` into `maxTicksLimit: 12` and hope.

### 12. Small-n bar charts should look like exhibits, not leftover Tableau

Later views are often four to eight horizontal bars (highest districts, Chapter 74 programs, top Boston earners). They share the 51-state navy, no sorting cue, truncated names, and labels that collide.

**Do this:**
- Sort explicitly and say so in the caption ("Highest ten, FY 2025").
- Full-width, one column, 22px-tall bars, names on the left untruncated.
- Direct labels at the end of the bar, never on the bar.
- Gold only for Massachusetts / the selected town / the named hospital. Do not gold-encode Boston on a Boston-only chart; every bar would be gold.

Grouped bars (heating and cooling degree days, RPP components) need the legend **above** the plot with the same colors as the bars, and a gap between groups. 280px is not enough.

### 13. Annotate the one fact the chart is for

MBTA Figure 1 works because of the dashed 2019 average and the gold end-dot. Most suite charts have no annotation. The lede restates the number in prose **under** the chart, so the eye never meets a mark that says "this is the point."

**Do this, using existing derived cells only:**
- A reference line for the U.S. value on a state bar or map ramp.
- A reference line for 100% on recovery, funded ratio, and index charts.
- One callout on the latest point: the same text as the hero number.
- On pensions Figure 1 (funded-ratio histogram), mark the 60% and 100% edges and note "13 boards below 60 percent" as a label in the plot, which the KPI already states.

Do not add decorative icons. One line and one label per figure.

### 14. Tile maps can be the handsome default for ranks

Unemployment and NAEP tiles already put the score in the cell. They look like a filled crossword: dense, equal, scannable. Geo choropleths of rank (who is 37th) waste the shape of Texas.

**Do this:** Use tiles for any namesake that is a **rate, score, index, or rank**. Use the Albers choropleth for **counts and dollars**. That is already the rule in `TILE_TOOLS` (DL-07, DL-14, DL-19, DL-31). Extend it to cost-of-living-style companions and to electricity's residential **rank**, or add a Map / Tiles toggle so staff can switch.

Give tiles a 4px gap, a stronger selected ring, and a type size that does not wrap (`29.35¢` on a 44px cell is tight). On a phone, a searchable list should replace the grid.

---

## Value: what would make staff come back

Charts that look finished still have to earn a place in a Pioneer brief. These are product moves, not new data.

### 15. A three-place strip that follows the user

Every fifty-state page already has United States, Massachusetts, and Florida in the ledger. The hero shows one Place. The KPIs show highest, lowest, and Massachusetts. Florida is a fourth thought.

**Do this:** A persistent three-cell strip under the hero: United States · Massachusetts · Florida (or the Compare state). Same number, same unit, same rank. Changing Place updates the middle cell and the map. That strip **is** the Pioneer product: MA against the country and against Florida.

Town tools get Boston · selected town · ACS peer. Pensions get Teachers · State · selected board.

### 16. Figure 1 must be slide-ready

Staff will not re-plot. They will screenshot.

**Do this:**
- A "Copy figure" control that copies PNG at 2x, with title, unit, source id, and vintage burned in under the plot (the exhibit head already has Figure N and the title).
- Print CSS that keeps the hero, the strip, Figure 1, and the cite line, and drops Ask, jump, and the register.
- Source line on Figure 1 names the publisher, not "see the register."

This is the highest-leverage "appealing" change: the chart has to survive leaving the site.

### 17. Small multiples beat one overloaded map

Electricity already has Households / All-sector / Sales / Generation as tabs on one map. That is better than four pages. It is worse than four small maps on one screen, because the staffer cannot see residential vs all-sector at the same time.

**Do this where the ledger already has two or three companion rankings:** a row of small tile maps, each with its own title and MA chip, instead of tabs that replace Figure 1. NAEP grade 4 reading vs grade 4 math is the obvious pair. Do not build a new series. Facet what is already on the page.

### 18. Lookup charts should answer "my town" in the figure

Town Profiles draws 351 polygons at 400px. Nobody clicks Wellfleet. The value is the find card (population, income, peer).

**Do this:** When a town is selected, redraw Figure 1 as that town versus its Census peer and versus Massachusetts, three bars, full labels. Keep the 351 map as a later view. Hospitals: selected hospital versus the statewide commercial average. Legislature: the member versus House median and Senate median.

The ledger already has the cells. The chart should show the comparison the user came for.

### 19. Ask should return a cited paragraph plus the live figure, not a second drawing

Once the on-page widget deep-links (item 3 of the first review), the valuable next step is a **brief-ready answer**: two sentences, the figure, the SRC id, and "Copy citation." No mini SVG. The page already has the graphic; Ask should scroll to it and highlight the exhibit (`exhibit.hl` already exists in CSS).

Declines should still name the nearest finder (retiree search, town typeahead).

### 20. Show what moved since the last vintage

Returning staff will not re-read 31 pages. Status is operator-facing.

**Do this:** On each tool, one line under the dateline: "What is new in this vintage," filled only when the refresh actually changed a headline cell (ridership month, BFS month, unemployment rate). No change means no line. The changelog can stay for engineering; the page should speak in the namesake number.

---

## Flagship-specific chart notes

**MBTA.** Keep Figure 1 as the model (2019 dashed line, gold end-dot, year ticks on January). Recovery bars already use green at or above 100%. Give farebox and cost the same direct labels and a bit more height. Reliability's four modes on one line chart with different end months needs per-series "as of" in the legend.

**Electricity.** Household vs all-sector as two small maps or a grouped bar for MA / US / FL, rather than four equal tabs. Trend already has rust Florida; copy that file's `drawTrend` into the suite renderer.

**Pensions.** Histogram of 105 boards is the right Figure 1 shape, but it needs 60% and 100% reference lines and a callout for Teachers and State, not only axis labels at 45°. The returns histogram is a second copy of the same idea; a slope of 1-year vs 5-year for the two large systems plus the selected board would tell a story the bins do not.

**Florida.** County choropleth plus readout is the second-best map on the site. Pair the two small premium charts (hFig1a / hFig1b) in a way that shares a time axis, or combine them with a dual note rather than two 240px plots. Report-card grades are not a graph; they are the most scannable exhibit on that page, keep them high.

**State Wealth Taxes.** The 51-tile grid is a chart of legal status, not a statistical map. It needs a mobile list. The sticky panel is the "tooltip." Do not force this into Chart.js.

**Town map.** 351 polygons are a texture, not a control. Demote.

---

## Suggested build order for this pass

Do these in the shared renderer and theme, then the five flagships inherit most of it.

1. Fix Florida rust and the four-role color function (trend, bars, map outline, insight compare).
2. Stop clipping: dynamic right pad, taller insight plots, stackEnds fallback, no on-bar labels past eight bars.
3. Map readout on the map; five-bin ramp; Florida outline on.
4. MBTA-style end-dot and reference line helpers in `chart-theme.js`, used on every namesake trend.
5. Index-100 title, 100-line, and tooltip that leads with the raw figure.
6. Copy-figure PNG + print CSS + publisher name on Figure 1.
7. Three-place strip (US / MA / FL) under the hero.
8. Monthly series default to the last 36 months.
9. Lookup tools: three-bar "you vs peer vs Massachusetts" as Figure 1.
10. Ask highlights the live exhibit instead of drawing SVG on the door.

Items 1 to 5 make every graph look complete. Items 6 to 10 make the complete graph useful in a Pioneer week.
