"""Build site/index.html from src/template.html + data files.

Inputs:  src/template.html, src/engine.js, src/tax.js, data/presets.json, data/rates.json, data/tax2026.json
Output:  site/index.html (a single self-contained page)
"""
import json, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def fmt_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"

def build():
    t = (ROOT / "src/template.html").read_text()
    presets = json.loads((ROOT / "data/presets.json").read_text())
    rates = json.loads((ROOT / "data/rates.json").read_text())
    subs = {
        "{{AS_OF}}": fmt_date(rates["as_of"]),
        "{{RATE_WEEK}}": fmt_date(rates["week"]),
        "{{RATE30}}": f'{rates["rate30"]:.2f}',
        "{{RATE15}}": f'{rates["rate15"]:.2f}',
    }
    for k, v in subs.items():
        t = t.replace(k, v)
    t = t.replace("/*MARKETS*/", json.dumps(presets))
    t = t.replace("/*ENGINE*/", (ROOT / "src/engine.js").read_text())
    t = t.replace("/*TAXJS*/", (ROOT / "src/tax.js").read_text())
    t = t.replace("/*TAXDATA*/", json.dumps(json.loads((ROOT / "data/tax2026.json").read_text())))
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}|/\*(MARKETS|ENGINE|TAXJS|TAXDATA)\*/", t)
    if left:
        sys.exit(f"Unreplaced placeholders: {left}")
    out = ROOT / "site/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t)
    print(f"Built {out.relative_to(ROOT)} ({len(t):,} bytes, {len(presets)} markets, 30-yr rate {subs['{{RATE30}}']}%)")

if __name__ == "__main__":
    build()
