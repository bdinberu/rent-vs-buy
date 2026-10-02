"""Independent Python implementation of the income-to-tax rules (written from the rule descriptions, not translated from tax.js)."""
import json, math
from pathlib import Path
T = json.loads((Path(__file__).resolve().parent.parent / "data/tax2026.json").read_text())

def tax_on(brackets, x):
    total = 0.0
    edges = [b[0] for b in brackets] + [float("inf")]
    for (start, rate), end in zip(brackets, edges[1:]):
        if x <= start: break
        total += (min(x, end) - start) * rate
    return total

def rate_at(brackets, x):
    rate = brackets[0][1]
    for start, r in brackets:
        if x > start: rate = r
    return rate

def household(income, filing, market, in_city=False):
    f = "mfj" if filing == "mfj" else "single"
    fed = T["federal"]; fed_taxable = max(0.0, income - fed["std"][f])
    out = {"marg": rate_at(fed["brackets"][f], fed_taxable)}
    cg = rate_at(fed["ltcg"][f], fed_taxable) + (fed["niit"]["rate"] if income > fed["niit"]["threshold"][f] else 0.0)
    if market not in T["markets"]:
        out.update(slt=None, cg=cg); return out
    scode, ccode = T["markets"][market]; S = T["states"][scode]
    if S.get("none"):
        s_tax, s_taxable, s_gain = 0.0, 0.0, 0.0
    else:
        std = S.get("std", {}).get(f, 0.0)
        ph = S.get("stdPhase")
        if ph and income > ph["start"]:
            reduction = ph["rate1"] * (min(income, ph["second"]) - ph["start"]) + ph["rate2"] * max(0.0, income - ph["second"])
            std = std - min(reduction, ph["maxCut"] * std)
        ex = S.get("exemption", {}).get(f, 0.0)
        lim = S.get("exemptionIncomeLimit")
        if lim and income > lim[f]: ex = 0.0
        s_taxable = max(0.0, income - std - ex)
        s_tax = tax_on(S["brackets"][f], s_taxable)
        cr = S.get("credit")
        if cr:
            credit = cr[f]
            if income > cr["phaseStart"][f]:
                credit -= cr["phasePer2500"][f] * math.ceil((income - cr["phaseStart"][f]) / 2500)
            s_tax = max(0.0, s_tax - max(0.0, credit))
        m = rate_at(S["brackets"][f], s_taxable)
        s_gain = 0.0 if S.get("gainsExempt") else min(m, S["gainsCap"]) if "gainsCap" in S else m
    c_tax = c_gain = 0.0
    if ccode and in_city:
        C = T["cities"][ccode]
        if C["base"] == "wages":
            c_tax = income * C["rate"]
        else:
            c_tax = tax_on(C["brackets"][f], s_taxable)
            if C.get("taxesGains"): c_gain = rate_at(C["brackets"][f], s_taxable)
    out.update(slt=s_tax + c_tax, cg=cg + s_gain + c_gain); return out
