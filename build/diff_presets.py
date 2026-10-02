"""Compare two versions of data/presets.json and print every changed value, flagging implausible moves.

Usage: python3 build/diff_presets.py OLD.json [NEW.json]   (NEW defaults to data/presets.json)
Exit code 2 if any change is flagged, so a routine can stop and report instead of proceeding.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
# field: (label, kind, flag threshold as a relative change for money, absolute for rates)
FIELDS = {"price": ("Home price", "money", 0.20), "rent0": ("Rent (3BR)", "money", 0.15),
          "propTax": ("Property tax", "pct", 0.003), "assessCap": ("Assessment cap", "pct", 0.0),
          "overval": ("Price-to-rent gap", "pct", 0.10), "apprHist": ("Price growth", "pct", 0.01),
          "rentHist": ("Rent growth", "pct", 0.01)}
def fmt(v, kind):
    if v is None: return "none"
    return f"${v:,.0f}" if kind == "money" else f"{v * 100:.2f}%"
def main():
    old = json.loads(Path(sys.argv[1]).read_text())
    new = json.loads(Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "data/presets.json").read_text())
    rows, flags = [], 0
    for k in sorted(set(old) | set(new)):
        if k not in old or k not in new:
            rows.append(f"| {k} | market {'added' if k in new else 'removed'} | | | FLAG |"); flags += 1; continue
        for f, (label, kind, lim) in FIELDS.items():
            a, b = old[k].get(f), new[k].get(f)
            if a == b: continue
            if a is None or b is None: flag = True
            elif kind == "money": flag = abs(b / a - 1) > lim
            else: flag = abs(b - a) > lim
            flags += flag
            rows.append(f"| {new[k]['label']} | {label} | {fmt(a, kind)} | {fmt(b, kind)} | {'FLAG' if flag else ''} |")
    if not rows:
        print("No changes to market data."); return 0
    print("| Market | Field | Old | New | Check |\n|---|---|---|---|---|"); print("\n".join(rows))
    print(f"\n{len(rows)} changes, {flags} flagged for review.")
    return 2 if flags else 0
if __name__ == "__main__":
    sys.exit(main())
