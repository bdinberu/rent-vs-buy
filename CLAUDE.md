# Rent or Buy

A static web app comparing buying a home with renting and investing the difference, for 18 US metros, published to GitHub Pages by `.github/workflows/deploy.yml`.

- Page: `src/template.html` (layout, styles, interface code) plus `src/engine.js` (model) and `src/tax.js` (income to tax inputs), assembled by `build/build_site.py` into `site/index.html`.
- Data: `data/presets.json` (built by `build/build_presets.py` from `data/prices_nar_*.json`, the table in that script, and `data/metro_stats.json`), `data/rates.json`, `data/tax2026.json`, `data/series/` (raw histories).
- The Python reference model is `tests/model.py`. `src/engine.js` must match it; `tests/check_engine.js` enforces this to the cent.

Rules for any change:
1. Run the full check before committing: `python3 build/build_site.py && python3 tests/make_cases.py && node tests/check_engine.js && python3 tests/check_data.py && python3 tests/test_refresh.py && python3 tests/test_tax.py`
2. Every data value needs a named source and date, recorded in the metro note or the data file's source field.
3. Never invent or estimate a number to fill a gap. Leave the old value and report it.
4. To update data, follow `.claude/skills/update-data/SKILL.md`.
