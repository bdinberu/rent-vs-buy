"""Sanity checks on data files. Fails the build if any value is missing or implausible."""
import json, sys
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
errors = []
def check(cond, msg):
    if not cond: errors.append(msg)

rates = json.loads((ROOT / "data/rates.json").read_text())
for k in ("rate30", "rate15"):
    check(2 <= rates[k] <= 15, f"{k}={rates[k]} outside 2-15%")
check(rates["rate15"] < rates["rate30"] + 0.5, "15-year rate should not exceed the 30-year by more than 0.5 points")
for k in ("week", "as_of"):
    date.fromisoformat(rates[k])

presets = json.loads((ROOT / "data/presets.json").read_text())
check(len(presets) >= 1, "no markets")
labels = [m["label"] for m in presets.values()]
check(len(labels) == len(set(labels)), "duplicate market labels")
bounds = {"price": (100_000, 5_000_000), "rent0": (800, 12_000), "propTax": (0.001, 0.03),
          "overval": (-0.5, 1.5), "apprHist": (-0.02, 0.10), "rentHist": (-0.02, 0.10)}
for k, m in presets.items():
    for f, (lo, hi) in bounds.items():
        v = m.get(f)
        check(isinstance(v, (int, float)) and lo <= v <= hi, f"{k}.{f}={v} outside {lo}-{hi}")
    cap = m.get("assessCap")
    check(cap is None or 0 < cap <= 0.15, f"{k}.assessCap={cap} implausible")
    check(bool(m.get("note")), f"{k} missing source note")

site = (ROOT / "site/index.html").read_text()
check("{{" not in site and not any(p in site for p in ("/*MARKETS*/", "/*ENGINE*/", "/*TAXJS*/", "/*TAXDATA*/")), "built page has unreplaced placeholders")
tax = json.loads((ROOT / "data/tax2026.json").read_text())
check(set(tax["markets"]) == set(presets), "every market needs a state in data/tax2026.json (and no extras)")
for m in presets.values():
    check(json.dumps(m["label"]) in site, f'built page missing market {m["label"]}')

if errors:
    print("FAIL:\n  " + "\n  ".join(errors)); sys.exit(1)
print(f"PASS: {len(presets)} markets and rates ({rates['rate30']}% / {rates['rate15']}%, week of {rates['week']}) look plausible")
