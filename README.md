# Rent or Buy

An interactive model that compares buying a home with renting and investing the difference, using sourced data for 18 US metros and 2026 federal, state, and city income tax rules. Both households spend the same cash each month; whichever path is cheaper invests the rest. The result is each household's net worth if they sold in any given year, after selling costs, the remaining mortgage, and taxes.

The site is a single self-contained page (`site/index.html`) built from a template and data files, then published with GitHub Pages.

## Repository layout

```
src/template.html        Page template (layout, styles, interface code) with placeholders for data
src/engine.js            The calculation engine used by the page
src/tax.js               Turns household income into the federal bracket, state and local income tax, and capital gains rate
data/presets.json        One entry per metro: price, rent, tax, cap, price-to-rent gap, growth, source note
data/rates.json          Current Freddie Mac mortgage rates and their dates
data/tax2026.json        2026 federal, state, and city income tax rules, and which state and city each market uses
data/series/             Raw FHFA price index and BLS rent index histories behind the gaps
data/prices_nar_q2_2026.json   NAR single-family median prices used for the presets
build/build_site.py      Builds site/index.html from the template and data
build/metro_stats.py     Recomputes each metro's price-to-rent gap and growth rates from data/series/
build/build_presets.py   Assembles data/presets.json (prices, rents, taxes, caps, notes live here)
build/refresh_rates.py   Pulls the latest Freddie Mac rates from FRED into data/rates.json
build/diff_presets.py    Compares two versions of data/presets.json and flags implausible changes
data/series_ids.json     The FRED series behind each metro's history files
data/CHANGELOG.md        What data changed, when, and from which source
.claude/skills/update-data/SKILL.md   The playbook a Claude Code routine follows to refresh the data
CLAUDE.md                Orientation for Claude Code sessions in this repo
tests/                   Reference model and checks run before every deploy
spreadsheet/             Excel version of the model (not rebuilt automatically)
```

## Publish it on GitHub Pages

1. Create a new repository on GitHub and push this folder to its `main` branch.
2. In the repository, open **Settings > Pages** and set **Source** to **GitHub Actions**.
3. Open the **Actions** tab. The "Test and deploy" workflow runs on every push to `main`. It builds the page, runs every check, and publishes only if all of them pass.
4. Your site appears at `https://<your-username>.github.io/<repository-name>/`.

To preview locally: `python build/build_site.py`, then open `site/index.html` in a browser.

## Turn on weekly mortgage rate updates

1. Get a free FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html
2. In the repository, open **Settings > Secrets and variables > Actions** and add a repository secret named `FRED_API_KEY`.
3. Open **Settings > Actions > General** and, under workflow permissions, allow GitHub Actions to create pull requests.
4. Every Friday, "Refresh mortgage rates" fetches Freddie Mac's latest 30-year and 15-year rates, rebuilds the page, runs all checks, and opens a pull request. Merge it to publish. You can also run it by hand from the Actions tab.

The refresh refuses to update, and changes nothing, if the two rates come from different weeks, a value is implausible, the data is older than what's already there, or the 30-year rate moved more than one point in a single update.

The FRED request itself has not been tested against the live API (the update logic is tested offline in `tests/test_refresh.py`). Run the workflow once by hand after adding the key and check the result.

## Monthly data refresh with a Claude Code routine

A Claude Code routine can check every source each month and open a pull request with verified updates, following `.claude/skills/update-data/SKILL.md`. Nothing goes live until you merge.

1. At https://claude.ai/code/routines, click **New routine**.
2. Name: `Rent or Buy data refresh`. Repository: this repo.
3. Prompt: `Follow .claude/skills/update-data/SKILL.md to check every data source for newer releases and apply verified updates. Finish with the report described in that skill.`
4. Environment: create one with **Network access** set to **Custom**, keep the default package list, and allow: `api.stlouisfed.org`, `fred.stlouisfed.org`, `www.huduser.gov`, `www.nar.realtor`, `www.hsh.com`, `www.hicentral.com`, `taxfoundation.org`, `www.irs.gov`, `www.phila.gov`, `www.freddiemac.com`. Add your FRED key as an API credential or environment variable named `FRED_API_KEY`.
5. Connectors: remove all of them; the routine doesn't need any.
6. Trigger: monthly. Pick the closest preset in the form, then run `/schedule update` in the Claude Code CLI and set the cron expression `0 9 15 * *` (9am on the 15th).
7. Click **Run now** once to test it. A green status only means the session ran; open the run to read the report.

If a run reports a blocked domain, add it to the environment's allowed domains.

## Updating the rest of the data by hand

Everything below needs a person to read the source, because none of it has a clean API or it calls for judgment. After editing, run the build and tests (or just push; the deploy workflow runs them).

| When | What | Source | Where to change it |
|---|---|---|---|
| Every quarter (Feb, May, Aug, Nov) | Metro home prices | NAR Metropolitan Median Area Prices, single-family | `data/prices_nar_q2_2026.json` (rename for the new quarter and update the path in `build/build_presets.py`) |
| Every quarter | Honolulu price | Honolulu Board of Realtors, Oahu single-family median | `P["hon"]` in `build/build_presets.py` |
| Every year, October | Rents | HUD Fair Market Rents, 3 bedrooms | Rent figures in `build/build_presets.py` |
| Every year | Property tax rates and caps | Census ACS effective rates; county and state sources in each note | `build/build_presets.py` |
| Every year, around November | Standard deduction and SALT cap | IRS inflation adjustments | `src/engine.js` and `tests/model.py` (keep them identical; the engine check will fail if they differ) |
| Every year, January to February | Income tax brackets, capital gains thresholds, state and city rates | IRS revenue procedure; Tax Foundation's annual state table; city revenue departments | `data/tax2026.json` (copy to a new year's file and update `build/build_site.py`); run `tests/test_tax.py` |
| Quarterly or twice a year | Price and rent histories | FHFA House Price Index and BLS CPI rent of primary residence, via FRED | Add the new year to the files in `data/series/`, then run `build/metro_stats.py` |

After changing anything under `build/` or `data/series/`, regenerate the presets and rebuild:

```
python build/metro_stats.py
python build/build_presets.py
python build/build_site.py
python tests/make_cases.py && node tests/check_engine.js && python tests/check_data.py
```

## Checks that run before every deploy

- **Engine vs. reference model:** 600 random scenarios (including price reversion, assessment caps, and PMI) must match the Python reference model in `tests/model.py` to within one cent.
- **Data sanity:** every metro's price, rent, tax rate, cap, gap, and growth rate must fall in a plausible range and carry a source note; rates must be plausible and dated.
- **Built page:** no unreplaced placeholders, and every market appears in the page.
- **Rate refresh logic:** offline tests of the rules above.
- **Tax calculator:** hand-computed checks (for example, the IRS's own $11,600 figure and a published New York example), plus over 1,000 income, filing, market, and city combinations where `src/tax.js` must match an independent Python implementation exactly.

## Known limitations

- HUD's FY2027 Fair Market Rents took effect October 1, 2026. The presets still use FY2026 and are due for an update.
- Transfer taxes are not modeled. Several metros (Philadelphia, New York, San Francisco, Washington) and Hawaii charge them; raise the selling cost input to account for them.
- HUD rents are 40th-percentile gross rents (including utilities) for mostly apartment and townhome units, so a single-family house usually rents for more.
- Metros without a fully sourced price, rent, and 30-year history are excluded: Anchorage, Baltimore, Phoenix, Riverside, and Seattle.
- The Excel file in `spreadsheet/` is a snapshot and is not rebuilt by the workflows. It covers 50 years but has no income preset.
- The income preset uses one tax rate per household for the whole period: it doesn't model income changes, large gains pushing you into a higher bracket in the year of sale, the SALT cap phase-down above $505,000, New York's high-income recapture, or the 37% bracket's itemized-deduction limit. City taxes other than New York City's apply to wages only.
