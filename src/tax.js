// Income -> tax inputs for the rent vs buy model, from the 2026 rules in tax2026.json.
// Returns the federal marginal rate, state and local income tax paid, and the all-in capital gains rate.
function makeTax(T) {
  const fs = f => (f === "mfj" ? "mfj" : "single");
  function bracketTax(br, x) {
    let t = 0;
    for (let i = 0; i < br.length; i++) {
      const lo = br[i][0], hi = i + 1 < br.length ? br[i + 1][0] : Infinity;
      if (x > lo) t += (Math.min(x, hi) - lo) * br[i][1];
    }
    return t;
  }
  function marginal(br, x) { let r = br[0][1]; for (const [lo, rate] of br) if (x > lo) r = rate; return r; }
  function federal(income, filing) {
    const f = fs(filing), F = T.federal, taxable = Math.max(0, income - F.std[f]);
    return { taxable, tax: bracketTax(F.brackets[f], taxable), marg: marginal(F.brackets[f], taxable),
             ltcg: marginal(F.ltcg[f], taxable), niit: income > F.niit.threshold[f] ? F.niit.rate : 0 };
  }
  function state(code, income, filing) {
    const S = T.states[code], f = fs(filing);
    if (!S || S.none) return { name: S ? S.name : "", taxable: 0, tax: 0, marg: 0, gains: 0, none: true };
    let std = S.std ? S.std[f] : 0;
    if (S.stdPhase && income > S.stdPhase.start) {
      const P = S.stdPhase;
      const cut = P.rate1 * (Math.min(income, P.second) - P.start) + P.rate2 * Math.max(0, income - P.second);
      std -= Math.min(cut, P.maxCut * std);
    }
    let ex = S.exemption ? S.exemption[f] : 0;
    if (S.exemptionIncomeLimit && income > S.exemptionIncomeLimit[f]) ex = 0;
    const taxable = Math.max(0, income - std - ex);
    let tax = bracketTax(S.brackets[f], taxable);
    if (S.credit) {
      let c = S.credit[f];
      if (income > S.credit.phaseStart[f]) c -= S.credit.phasePer2500[f] * Math.ceil((income - S.credit.phaseStart[f]) / 2500);
      tax = Math.max(0, tax - Math.max(0, c));
    }
    const marg = marginal(S.brackets[f], taxable);
    const gains = S.gainsExempt ? 0 : (S.gainsCap ? Math.min(marg, S.gainsCap) : marg);
    return { name: S.name, taxable, tax, marg, gains };
  }
  function city(code, income, filing, stateTaxable) {
    const C = T.cities[code]; if (!C) return null;
    if (C.base === "wages") return { name: C.name, tax: income * C.rate, marg: C.rate, gains: 0 };
    const f = fs(filing), m = marginal(C.brackets[f], stateTaxable);
    return { name: C.name, tax: bracketTax(C.brackets[f], stateTaxable), marg: m, gains: C.taxesGains ? m : 0 };
  }
  function forHousehold(income, filing, marketKey, inCity) {
    const fed = federal(income, filing);
    const mk = T.markets[marketKey] || null;
    const st = mk ? state(mk[0], income, filing) : null;
    const ct = mk && mk[1] && inCity ? city(mk[1], income, filing, st.taxable) : null;
    const cgRate = fed.ltcg + fed.niit + (st ? st.gains : 0) + (ct ? ct.gains : 0);
    return { margRate: fed.marg, stateLocalTax: mk ? st.tax + (ct ? ct.tax : 0) : null, cgRate, fed, st, ct,
             cityName: mk && mk[1] ? T.cities[mk[1]].name : null };
  }
  return { federal, state, city, forHousehold, bracketTax, marginal };
}
if (typeof module !== "undefined") module.exports = { makeTax };
