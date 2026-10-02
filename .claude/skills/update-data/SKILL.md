---
name: update-data
description: Check every data source behind the Rent or Buy app for newer releases, apply verified updates, run the full check suite, and push a branch with a change report. Use for the scheduled data refresh or when asked to "update the data".
---

# Update the app's data

You are refreshing the data behind a public calculator people use for a major financial decision. Accuracy matters more than completeness: a skipped update costs nothing, while a wrong number misleads everyone who opens the app.

## Rules

1. Every value you change needs a named source, a date or release period, and a URL, recorded in the change report and `data/CHANGELOG.md`.
2. Never invent, estimate, interpolate, or carry forward a number. If you cannot find or verify a value, leave the old one in place and list it under "Not updated" in the report.
3. Verify every hand-copied number against a second source, or against a check described below. If two sources disagree, use neither and report both.
4. Change data only. Do not edit `src/engine.js`, `tests/model.py`, `src/tax.js`, or test logic, except for the tax-year steps in section 6.
5. Do not touch `data/rates.json`; a GitHub workflow updates mortgage rates weekly.
6. Do not change Washington, DC's history values in `build/metro_stats.py`; they come from a spliced series that isn't in the repo. Flag it if its sources have new data.
7. Work on a branch named `claude/data-update-YYYY-MM-DD`. Never push to `main`.
8. If nothing has a newer release than what the repo already has, make no commits and report "No new releases" with what you checked.

## Step 0: Orient

- Read `data/CHANGELOG.md` to see what is applied and from which release. Note today's date.
- Save a copy of the current presets for comparison: `cp data/presets.json /tmp/presets_before.json`
- If a network request is blocked (HTTP 403 with `host_not_allowed`), record the domain in the report and continue with the other sources.

## Step 1: Metro home prices (NAR, quarterly)

- Current file: `data/prices_nar_q2_2026.json` (keys are metro codes; Honolulu is set separately).
- Source: NAR "Metropolitan Median Area Prices" quarterly release, single-family existing-home median (nar.realtor research section). HSH.com republishes the same table and is the cross-check.
- New data: NAR publishes roughly mid-February, May, August, and November for the prior quarter. Only update when a quarter newer than the current file is published.
- Use the same metro area for each key as the current file (for example, San Diego-Chula Vista-Carlsbad). Use NAR's figure, not a listing-price or all-home-types median.
- Verify: NAR and HSH agree for every metro. Values marked preliminary are fine; say so in the note.
- Apply: write `data/prices_nar_qN_YYYY.json` with the same keys, change the path in `build/build_presets.py`, and keep the old file.

## Step 2: Honolulu price (monthly)

- Current value: `P["hon"]` in `build/build_presets.py`, plus the Honolulu note text in the same file.
- Source: Honolulu Board of Realtors (hicentral.com) monthly Oahu single-family median. Use the year-to-date median through the latest month, as the current note does, and update the note's period and values.
- Verify: the monthly report lists both the year-to-date and latest-month medians; quote both in the note, as now.

## Step 3: Rents (HUD Fair Market Rents, yearly)

- Current values: the rent column (third field) of the `M` table in `build/build_presets.py` (HUD FY2026, 3 bedrooms).
- Source: HUD USER Fair Market Rents (huduser.gov), 3-bedroom FMR for the FMR area containing each metro's principal city.
- New data: HUD's fiscal year starts October 1. FY2027 took effect October 1, 2026 and has not been applied yet.
- Verify the area choice first: look up the FY2026 3-bedroom FMR for each area you plan to use. It must equal the current value in the `M` table. If it doesn't, you have the wrong area; stop for that metro and report.
- Apply: update the rent column, change the comment `HUD FY2026 3BR rent` to the new year, and update every "FY2026" mention in `src/template.html`, `README.md`, and the Honolulu note.

## Step 4: Price and rent histories (FHFA and BLS via FRED)

- Files: `data/series/` (one per metro and series, listed in `data/series_ids.json`). Price index rows are `year q1 q2 q3 q4`; rent rows are `year annual_average`.
- Fetch each series as a CSV with no API key: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=ID` (columns: date, value). This routine has no FRED key; the key in the GitHub repository secret is only for the weekly mortgage rate workflow.
- Add only complete years: all four quarters for a price index, and BLS's published annual average for rent (compute it as the mean of the year's values only if BLS publishes no annual figure, and say so).
- Overlap check, required for every series before changing its file: compare the fetched values with every year already in the file.
  - BLS rent (not seasonally adjusted, not revised): every overlapping year must match to within 0.1%.
  - FHFA price index (revised each quarter): every overlapping quarter must match within 2%. If so, replace the whole file with the current vintage and report the largest revision. If not, you have the wrong series or a rebasing; stop for that metro and report.
  - Where `data/series_ids.json` has `null`, search FRED for the metro's series and use it only if it passes the overlap check. Then record the ID in `data/series_ids.json`.
- When every metro whose series is still published has a new complete year in both files, raise `cur=2025` in `stats()` in `build/metro_stats.py` to that year. Leave Atlanta and Tampa's price indexes alone; FHFA stopped them at 2024.
- Then run `python3 build/metro_stats.py`.

## Step 5: Property taxes, caps, and notes (yearly check)

- Values: the tax and cap fields and notes in the `M` table of `build/build_presets.py`.
- Change only on an official source (state statute, county assessor, or state revenue department), such as a new assessment-cap law or the Honolulu home exemption rising to $140,000 from July 2027. Statewide effective rates come from the Census American Community Survey via the source already cited in the notes; update them only when a newer survey year is published and every metro is updated together.

## Step 6: Income tax rules (yearly, January to February; plus Philadelphia each July)

- Values: `data/tax2026.json` (federal, state, and city), and the standard deduction and SALT cap in both `src/engine.js` and `tests/model.py`, which must stay identical.
- Sources: the IRS revenue procedure for the new tax year, the Tax Foundation's annual "State Individual Income Tax Rates and Brackets" table, and city revenue departments (Philadelphia's resident wage tax changes each July 1).
- For a new tax year: copy to `data/taxYYYY.json`, update it, and change the path in `build/build_site.py`, `tests/taxcalc.py`, and `tests/test_tax.py`. Recompute the year-specific anchors in `tests/test_tax.py` by hand from the new published tables, never by copying the code's output.
- Mark tax-year changes as needing careful review in the report.

## Step 7: Check, compare, and report

1. Rebuild and run every check; all must pass:
   ```
   python3 build/build_presets.py
   python3 build/build_site.py
   python3 tests/make_cases.py && node tests/check_engine.js
   python3 tests/check_data.py && python3 tests/test_refresh.py && python3 tests/test_tax.py
   ```
2. Compare market data: `python3 build/diff_presets.py /tmp/presets_before.json`. It exits with code 2 if any change is outside normal ranges. For each flagged row, either confirm it in a second source and explain why it moved, or revert that value and list it under "Not updated".
3. Add a dated entry at the top of `data/CHANGELOG.md`: what changed and each source.
4. Commit with a message like `Data update: NAR Q3 2026 prices, HUD FY2027 rents`, then push the branch. If the GitHub CLI is available and signed in, open a pull request against `main`; otherwise leave the branch for the owner to open one.

The report (pull request body, or your final message) has four sections:

- **Updated:** the `diff_presets.py` table, plus any tax or history changes, each with its source and release period.
- **Checked, no new release:** each source and the latest release you found.
- **Not updated:** anything you couldn't verify, sources that disagreed, and blocked domains.
- **Needs review:** flagged values you kept, and any tax-year change.
