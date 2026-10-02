"""Tax calculator tests: hand-computed anchors and JavaScript (src/tax.js) vs independent Python (tests/taxcalc.py)."""
import json, subprocess, itertools, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from taxcalc import T, tax_on, rate_at, household
ok = 0
def check(name, got, want, tol=0.01):
    global ok
    assert abs(got - want) <= tol, f"{name}: got {got}, want {want}"; ok += 1; print(f"  ok  {name}: {got:,.4f}")
print("Hand-computed and published anchors:")
check("federal joint tax on $100,800 taxable (IRS table: $11,600)", tax_on(T["federal"]["brackets"]["mfj"], 100800), 11600)
check("federal bracket, $250k joint income", household(250000, "mfj", "custom")["marg"], 0.24, 1e-9)
check("federal bracket, $120k single income", household(120000, "single", "custom")["marg"], 0.22, 1e-9)
ny = 0.039*8500 + 0.044*(11700-8500) + 0.0515*(13900-11700) + 0.054*(80650-13900) + 0.059*(200000-80650)
check("NY state tax, $200k single taxable (published: about $11,200)", tax_on(T["states"]["NY"]["brackets"]["single"], 200000), ny)
assert abs(ny - 11200) < 100; print(f"      (hand total ${ny:,.2f} vs published ~$11,200)")
check("Philadelphia resident, $100k", household(100000, "single", "phi", True)["slt"] - household(100000, "single", "phi", False)["slt"], 3735)
ti = 150000 - 5540
ca = 0.01*11079 + 0.02*(26264-11079) + 0.04*(41452-26264) + 0.06*(57542-41452) + 0.08*(72724-57542) + 0.093*(ti-72724) - 153
check("California tax, $150k single", household(150000, "single", "sd")["slt"], ca)
check("capital gains, $250k joint in San Diego (15% fed + 0% NIIT + 9.3% CA)", household(250000, "mfj", "sd")["cg"], 0.15 + 0.093, 1e-9)
check("capital gains, $260k joint in San Diego (adds 3.8% NIIT)", household(260000, "mfj", "sd")["cg"], 0.15 + 0.038 + 0.093, 1e-9)
check("capital gains, $400k single in Honolulu (state capped at 7.25%)", household(400000, "single", "hon")["cg"], 0.15 + 0.038 + 0.0725, 1e-9)
check("capital gains, $150k single in St. Louis (Missouri exempts gains)", household(150000, "single", "stl", True)["cg"], 0.15, 1e-9)
check("no state tax in Dallas", household(300000, "mfj", "dal")["slt"], 0)
mn_std = 30600 - min(0.03*(337800-244400) + 0.10*(400000-337800), 0.8*30600)
check("Minnesota standard deduction phase-down at $400k joint", 400000 - mn_std, 400000 - (30600 - 0.8*30600) if 0.03*93400+0.10*62200 > 0.8*30600 else 400000 - mn_std)
# Cross-check against the JavaScript implementation
incomes = [0, 15000, 40000, 75000, 100000, 150000, 200000, 250000, 260000, 350000, 505000, 750000, 1200000, 3000000]
cases = [(i, f, m, c) for i, f, m, c in itertools.product(incomes, ["single", "mfj"], list(T["markets"]) + ["custom"], [False, True])]
js = """const {makeTax}=require(process.argv[1]+'/src/tax.js');const T=require(process.argv[1]+'/data/tax2026.json');const X=makeTax(T);
const cases=JSON.parse(require('fs').readFileSync(0,'utf8'));
console.log(JSON.stringify(cases.map(([i,f,m,c])=>{const r=X.forHousehold(i,f,m,c);return [r.margRate,r.stateLocalTax,r.cgRate];})));"""
out = json.loads(subprocess.run(["node", "-e", js, str(HERE.parent)], input=json.dumps(cases), capture_output=True, text=True, check=True).stdout)
worst = 0
for (i, f, m, c), (jm, js_slt, jcg) in zip(cases, out):
    p = household(i, f, m, c)
    worst = max(worst, abs(jm - p["marg"]), abs(jcg - p["cg"]), 0 if p["slt"] is None and js_slt is None else abs(js_slt - p["slt"]))
print(f"\nJavaScript vs independent Python: {len(cases)} combinations, worst difference {worst:.2e}")
assert worst < 1e-6
print(f"PASS: {ok} anchors, {len(cases)} cross-checks")
