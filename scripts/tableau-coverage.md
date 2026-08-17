# Tableau substance coverage

Inventory of the original Pioneer Tableau suite (US DataLabs, MA DataLabs, Boston DataLabs, and the 340B pages) against what each live DataLabs tool actually publishes. The question is substance, not title: does the page answer the same first questions the old dashboard answered.

Source of the 118 named dashboards: `catalog.json` before the partner-link drop (`cde9943^`). One live US DataLabs topic was never in that list: Higher Education Finance. Retail electricity is a flagship (DL-04), not a suite row.

Do not invent figures. A gap stays a gap until a named public file is compiled into a ledger.

## Score

| Status | Meaning |
| --- | --- |
| Covered | The live ledger publishes the namesake series at the same geography |
| Partial | Some of the substance is on the page; a companion series or the state cut is missing |
| Pending | The ledger already names the gap and declines it |
| Missing | The old dashboard's question is not on any live page |
| Leave | Stale, duplicate of a flagship, or not a data series (do not rebuild) |

The 118 catalog rows plus Higher Education Finance (119). Most namesake series are already on a live page. The holes are companions the heritage line promised and then declined: college faculty, staff, and finance; Pioneer-method indexes; DLS town-finance rankings; FBI crime rates; NASBO PDFs; and Patents still in build.

The build list below is those holes, not a second catalog.

## What the College page is missing (the example)

US DataLabs Higher Education has five topics. College Enrollment (DL-08) covers two of them and only part of two more.

| Old dashboard | Live today | Gap |
| --- | --- | --- |
| College Enrollment | Covered. Fall enrollment by state, 2012-2022, state picker | None |
| College Admissions | Covered as SAT mean and participation by state | ACT and admissions-rate files were not compiled |
| Faculty and Staff | National faculty headcount and rank/sex only | No state faculty, no state staff, no student-to-faculty ratio. Digest table 314.50 has public FTE staff and faculty by state |
| Student Data | National 6-year bachelor's graduation rate only | No state graduation, retention, or completions. IPEDS has state aggregates |
| Finance | Missing. Live on US DataLabs; never entered the catalog | No tuition, revenue, or spending. IPEDS Finance / Digest 334.x |

Plan for DL-08: keep the enrollment line as Figure 1. Add three later views from published files, do not invent a Digest state column that does not exist.

1. Faculty and staff by state from Digest 314.50 (public FTE staff, FTE faculty, students per faculty).
2. Student outcomes by state from IPEDS Graduation Rates and Retention, state rollup, not a college-ranking product.
3. Finance by state from IPEDS Finance or Digest 334 (revenue and expense per FTE, tuition and fees). Rename the tool only if the page then answers more than enrollment.

## Wave 1. Same public files, later views on existing tools

These close the largest substance holes without a new application. Each item is one builder pass on an existing ledger.

| Tool | Old dashboard | Add | Public file |
| --- | --- | --- | --- |
| DL-08 College Enrollment | Faculty and Staff | State public FTE faculty, FTE staff, students per faculty | NCES Digest 314.50 |
| DL-08 College Enrollment | Student Data | State 6-year graduation and retention | IPEDS GR / EF state tables |
| DL-08 College Enrollment | Higher Education Finance (uncatalogued) | State revenue, expense, and tuition per FTE | IPEDS Finance or Digest 334 |
| DL-07 State School Scores | Discipline & Security | More than one OSS year; add expulsion if the Digest table has it | Digest 233.40 and siblings |
| DL-06 Massachusetts Schools | MA Demographics | District race, English learner, and low-income shares | DESE / E2C enrollment by subgroup |
| DL-09 Charter Enrollment | Education Staff | Staff beyond teachers if Digest 213.20 / 208.40 is state-cut | NCES Digest staff tables |
| DL-14 State Unemployment | Employment and Wages | CES or full QCEW industry employment, not one weekly-wage stub | BLS CES / QCEW |
| DL-17 State Migration | US Demographics | Age and race of the state population | Census vintage or ACS |
| DL-21 Taxpayer Income | Tracking Wealth | Keep size-of-AGI stubs; do not invent a percentile file | Already compiled; say so on the page |
| DL-23 Vehicle-Miles Traveled | FEMA, NRI, degree days | Already in `derived.secondary`; make them first-class figures after VMT | OpenFEMA, NRI, NOAA (already sourced) |
| DL-27 Boston City Payroll | Boston DataLabs | Named top earners and a payroll trend from 2011; revenue by source from the FY26 file | data.boston.gov (already used) |
| DL-29 State Tax Collections | State & local expenses and revenues | Census of Governments state-and-local totals, not only QTAX | Census ASLG / COG |
| DL-31 State Imprisonment | Juvenile Incarceration | OJJDP custody if a stable state file exists; do not stretch the adult-prison youth count | OJJDP EZACJRP or Census of Juveniles |

## Wave 2. Named public files that the ledger already declines

The page already tells the truth. Compile the file or keep declining. Do not substitute a different series.

| Tool | Old dashboard | Why it is pending | Path |
| --- | --- | --- | --- |
| DL-12 State Medicaid Spending | State Health Expenses | NASBO health chapter is PDF-only | Wait for a machine-readable NASBO table, or transcribe with a two-path check |
| DL-19 Cost of Living | State Dependency, Tariff Impacts, Defense Impact | Pioneer-method indexes; methods are not in this repo | Restore only from the original method notes. Do not substitute a Census dump |
| DL-21 Taxpayer Income | Tax Statistics-Municipalities | Municipal SOI extract is not posted | Keep declining until IRS posts it |
| DL-26 Massachusetts Town Rankings | Crime, Debt, Financial Strength, Revenues, Taxes | DLS files are not a stable public CSV | Keep declining, or add a one-time DLS extract with a vintage note |
| DL-28 Massachusetts Tax Collections | Tax Credits; DOR monthly | mass.gov workbooks 403 from this environment | Fetch DOR from a reachable mirror; do not invent credits |
| DL-29 State Tax Collections | Rainy-day funds | NASBO Fiscal Survey is PDF | Same rule as health expenses |
| DL-29 State Tax Collections | Party Dominance | No stable public party-control file in the ledger | Ballotpedia-class files are editorial; only compile if Pioneer owns a dated table |
| DL-31 State Imprisonment | Crime Rates; Internet Crime | FBI CDE and IC3 do not post a stable state CSV on the last pass | Retry FBI CDE downloads; IC3 stays pending if still PDF |

## Wave 3. Missing substance with no home on a live page

| Old dashboard | Views (old catalog) | Proposed home | File |
| --- | --- | --- | --- |
| Higher Education Finance | (not in catalog; live on US DataLabs) | DL-08 later view | IPEDS Finance / Digest 334 |
| US Public Pensions | 646 | New later view on DL-29, not a second pensions flagship | Census Annual Survey of Public Pensions |
| Government Organizations | 470 | DL-29 later view | Census of Governments organization counts |
| Financial Transparency | 300 | DL-29 later view only if the old measure is a public index with a method | Do not invent a transparency score |
| Labor Demographics | 23 | DL-14 later view | BLS CPS or LAUS demographics if posted by state |
| Taxation Rates (archived) | 3,412 | Not DL-01. DL-01 is wealth and surtax vehicles | A statutory rate table is a new tool or a later view on DL-01. Only from a named rate file |
| Patents by State and Sector | 452 | DL-18 (in build) | PatentsView state and class counts |
| Boston Budget (revenue and initiatives) | inside Boston DataLabs | DL-27 later view | data.boston.gov operating budget |

## Leave archived

Do not rebuild these. They are stale, duplicated by a flagship, or not a series.

| Dashboard | Why leave |
| --- | --- |
| State & Teacher Retirees | Covered by DL-05 name search and retiree payroll |
| Pensions Performance | Covered by DL-05 board funded status and returns |
| MBTA (madatalabs.org/mbta) | Covered by DL-03 |
| MCAS Legacy | Superseded by MCAS NEXTGEN on DL-06 |
| Tracking COVID-19 | Closed series |
| Industry Clusters; NAICS Code Detail | 2020 vintage, low use |
| Employment and Establishments (MA) | Marked lagging; 5 views |
| Energy Storage | Narrow; DL-24 already has production, consumption, and CO2 |
| Inventory of Dams; Rail, Air and Water | Out of the current infrastructure scope (VMT, FEMA, NRI, transit) |
| School Districts-District Directory | DL-09 exclusions already decline a national directory |
| Peer Finder | A product, not a published series. Town peers already sit on DL-25 |
| Rankings-Local Public Employees | Same DLS problem as the other town rankings |

## Flagships (already the successor)

| Old dashboard | Live tool |
| --- | --- |
| Retail-Price Electricity | DL-04 |
| Pensions Overview / Performance / Retirees | DL-05 |
| 340B Program Growth, Charity Care, Legislative Mapping | DL-11 |
| State Wealth Taxes is new | DL-01 (not a Tableau successor) |
| Florida Homeowners Insurance is new | DL-02 |
| Legislature Pay is new | DL-32 |
| Family Healthcare Costs is new | DL-33 |

## What not to do

- Do not rename a tool until the missing series is on the page. College Enrollment should stay that name until faculty, students, and finance are compiled.
- Do not invent Pioneer indexes (dependency, tariff, defense) from a different file.
- Do not mark Patents live without a compiled PatentsView ledger.
- Do not reopen partner Tableau links on live tools. Coverage means figures in the ledger.
- Do not fold this work into a DL-01 or DL-02 research pass.

## Suggested order

1. DL-08 faculty, student outcomes, and finance (closes the example the user named).
2. DL-06 demographics; DL-07 fuller discipline; DL-09 fuller staff.
3. DL-18 Patents, so the last in-build suite row goes live.
4. DL-27 Boston earners and budget revenue.
5. DL-29 Census of Governments and public pensions.
6. Retry FBI crime rates and NASBO only when a machine-readable file is in hand.
7. Leave Pioneer-method indexes and DLS town-finance rankings until the method or a stable CSV exists.
