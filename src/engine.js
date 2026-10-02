// Rent vs buy engine. Mirrors model.py exactly; validated against it.
const STD_2026 = { single: 16100, mfj: 32200 };
const EXCL = { single: 250000, mfj: 500000 };
const MID_LIMIT = 750000;

function saltCap(calYear) {
  const caps = { 2026: 40400, 2027: 40804, 2028: 41212, 2029: 41624 };
  if (caps[calYear] !== undefined) return caps[calYear];
  return calYear >= 2030 ? 10000 : 40400;
}

// PMI: charged while the scheduled balance is above 78% of the purchase price, and never past
// the midpoint of the loan term (Homeowners Protection Act automatic and final termination).
function pmiCharged(pmiOn, s, price, term) {
  return pmiOn && s.beg > 0.78 * price && s.m <= term * 6;
}

// Home value path. Fixed mode: grows at p.appr. Revert mode: the price-to-rent ratio falls (or rises)
// from today's level toward its long-run norm, closing half the remaining gap every p.halfLife years;
// prices grow with rents times the change in the ratio. p.overval = how far today's ratio sits above its norm (0.27 = 27% above).
function apprInYear(p, y) {
  if (p.priceMode !== "revert") return p.appr;
  const h = p.halfLife, g0 = Math.log(1 + (p.overval || 0));
  if (!(h > 0)) return p.rentGrowth;
  // Log price-to-rent gap closes by half every h years: gap(t) = g0 * 0.5^(t/h). Prices grow with rents times the ratio change.
  return (1 + p.rentGrowth) * Math.exp(g0 * (Math.pow(0.5, y / h) - Math.pow(0.5, (y - 1) / h))) - 1;
}
// Property tax base: market value, or (with a cap, e.g. California Prop 13 = 2%) the purchase price grown at the
// cap, never above market value (Prop 8 decline-in-value).
function taxBase(p, vals, y) {
  const v = vals[y - 1];
  if (!(p.assessCap >= 0) || p.assessCap === null || p.assessCap === "") return v;
  return Math.min(v, p.price * Math.pow(1 + p.assessCap, y - 1));
}
function valuePath(p) {
  const v = [p.price];
  for (let y = 1; y <= 50; y++) v.push(v[y - 1] * (1 + apprInYear(p, y)));
  return v;
}

function payment(loan, r, years) {
  const i = r / 12, n = years * 12;
  if (i === 0) return loan / n;
  return loan * i / (1 - Math.pow(1 + i, -n));
}

function amortize(loan, r, years, months) {
  const pmt = payment(loan, r, years);
  let bal = loan;
  const rows = [];
  for (let m = 1; m <= months; m++) {
    const beg = bal;
    let interest = 0, principal = 0;
    if (m <= years * 12 && beg > 1e-9) {
      interest = beg * r / 12;
      principal = Math.min(beg, pmt - interest);
    }
    bal = beg - principal;
    rows.push({ m, beg, interest, principal, end: bal });
  }
  return { pmt, rows };
}

function annualBenefits(p, sched, loan, vals) {
  const out = {};
  for (let y = 1; y <= 50; y++) {
    const yr = sched.slice((y - 1) * 12, y * 12);
    let interest = 0, balSum = 0;
    for (const r of yr) { interest += r.interest; balSum += r.beg; }
    const avgBal = balSum / 12;
    const frac = avgBal <= MID_LIMIT ? 1 : MID_LIMIT / avgBal;
    const ptax = p.propTax * taxBase(p, vals, y);
    const cap = saltCap(2026 + y);
    const std = STD_2026[p.filing] * Math.pow(1 + p.infl, y);
    const ownerItem = interest * frac + Math.min(cap, ptax + p.stateLocalTax) + p.otherItem;
    const renterItem = Math.min(cap, p.stateLocalTax) + p.otherItem;
    const b = p.margRate * (Math.max(std, ownerItem) - Math.max(std, renterItem));
    out[y] = { benefit: p.itemize ? b : 0, ownerItem, std, itemizes: ownerItem > std };
  }
  return out;
}

// Simulate to year H and liquidate. Returns detail + per-year net worth path.
function run(p, H) {
  H = H || p.horizon;
  const price = p.price, downAmt = price * p.down, loan = price - downAmt;
  const closeAmt = price * p.closing;
  const months = Math.max(600, Math.max(H, p.term) * 12);
  const { pmt, rows: sched } = amortize(loan, p.rate, p.term, months);
  const pmiOn = p.down < 0.20;
  const vals = valuePath(p);
  const ben = annualBenefits(p, sched, loan, vals);
  const im = Math.pow(1 + p.invRet, 1 / 12) - 1;
  const dm = (p.divYield || 0) / 12;
  let renterPf = downAmt + closeAmt, renterContrib = renterPf;
  let ownerPf = 0, ownerContrib = 0;
  const tot = { interest: 0, principal: 0, pmi: 0, ptax: 0, ins: 0, maint: 0, hoa: 0, rent: 0, benefit: 0, divTaxR: 0, divTaxO: 0 };
  const years = [];
  let yAcc = null;
  for (let m = 1; m <= H * 12; m++) {
    const y = Math.ceil(m / 12);
    const s = sched[m - 1];
    const vStart = vals[y - 1];
    const pmi = pmiCharged(pmiOn, s, price, p.term) ? p.pmiRate * loan / 12 : 0;
    const cStart = price * Math.pow(1 + p.infl, y - 1);   // structure costs track inflation, not land value
    const ptax = p.propTax * taxBase(p, vals, y) / 12, ins = p.ins * cStart / 12, maint = p.maint * cStart / 12;
    const hoa = p.hoa * Math.pow(1 + p.infl, y - 1);
    const b = ben[y].benefit / 12;
    const ownerCost = s.interest + s.principal + pmi + ptax + ins + maint + hoa - b;
    const rent = p.rent0 * Math.pow(1 + p.rentGrowth, y - 1) + p.rentIns * Math.pow(1 + p.infl, y - 1);
    const diff = ownerCost - rent;
    // Dividends (part of the total return) are taxed each month at the capital gains rate;
    // the after-tax dividend is reinvested and added to cost basis.
    const divR = renterPf * dm, divO = ownerPf * dm;
    const taxR = divR * p.cgRate, taxO = divO * p.cgRate;
    renterPf = renterPf * (1 + im) - taxR + Math.max(diff, 0);
    renterContrib += divR - taxR + Math.max(diff, 0);
    ownerPf = ownerPf * (1 + im) - taxO + Math.max(-diff, 0);
    ownerContrib += divO - taxO + Math.max(-diff, 0);
    tot.divTaxR += taxR; tot.divTaxO += taxO;
    tot.interest += s.interest; tot.principal += s.principal; tot.pmi += pmi; tot.ptax += ptax;
    tot.ins += ins; tot.maint += maint; tot.hoa += hoa; tot.rent += rent; tot.benefit += b;
    if (m % 12 === 1) yAcc = { year: y, ownerCost: 0, rent: 0, interest: 0, principal: 0, pmi: 0, other: 0, benefit: 0 };
    yAcc.ownerCost += ownerCost; yAcc.rent += rent; yAcc.interest += s.interest; yAcc.principal += s.principal;
    yAcc.pmi += pmi; yAcc.other += ptax + ins + maint + hoa; yAcc.benefit += b;
    if (m % 12 === 0) {
      const liq = liquidate(p, y, s.end, ownerPf, ownerContrib, renterPf, renterContrib, closeAmt, vals);
      years.push({ ...yAcc, balance: s.end, homeVal: liq.homeVal, ownerNW: liq.ownerNW, renterNW: liq.renterNW,
        itemizes: ben[y].itemizes });
    }
  }
  const last = sched[H * 12 - 1];
  const liq = liquidate(p, H, last.end, ownerPf, ownerContrib, renterPf, renterContrib, closeAmt, vals);
  let fullInt = 0, fullPrin = 0, fullPmi = 0;
  for (let m = 1; m <= p.term * 12; m++) {
    const s = sched[m - 1];
    fullInt += s.interest; fullPrin += s.principal;
    if (pmiCharged(pmiOn, s, price, p.term)) fullPmi += p.pmiRate * loan / 12;
  }
  // PMI end month
  let pmiMonths = 0;
  if (pmiOn) for (const s of sched) { if (s.m > p.term * 12) break; if (pmiCharged(pmiOn, s, price, p.term)) pmiMonths++; }
  return { pmt, loan, downAmt, closeAmt, vals, ...liq, diff: liq.ownerNW - liq.renterNW, tot, years,
    fullInt, fullPrin, fullPmi, pmiMonths, sched, ben };
}

function liquidate(p, H, bal, ownerPf, ownerContrib, renterPf, renterContrib, closeAmt, vals) {
  const homeVal = vals[H];
  const sell = homeVal * p.sellCost;
  const gain = homeVal - sell - (p.price + closeAmt);
  const excl = H >= 2 ? EXCL[p.filing] : 0;
  const homeTax = Math.max(0, gain - excl) * p.cgRate;
  const ownerPfTax = p.cgRate * Math.max(0, ownerPf - ownerContrib);
  const renterPfTax = p.cgRate * Math.max(0, renterPf - renterContrib);
  const ownerNW = homeVal - sell - bal - homeTax + ownerPf - ownerPfTax;
  const renterNW = renterPf - renterPfTax;
  return { homeVal, sell, bal, homeTax, ownerPf, ownerPfTax, renterPf, renterPfTax, ownerNW, renterNW, gain };
}

// Find the value of `key` where buying and renting tie at horizon (bisection).
function breakeven(p, key, lo, hi) {
  const f = x => { const q = { ...p, [key]: x }; const r = run(q); return r.ownerNW - r.renterNW; };
  let flo = f(lo), fhi = f(hi);
  if (Math.sign(flo) === Math.sign(fhi)) return { found: false, sign: Math.sign(flo) };
  for (let k = 0; k < 60; k++) {
    const mid = (lo + hi) / 2, fm = f(mid);
    if (Math.sign(fm) === Math.sign(flo)) { lo = mid; flo = fm; } else { hi = mid; fhi = fm; }
  }
  return { found: true, value: (lo + hi) / 2 };
}

if (typeof module !== "undefined") module.exports = { run, breakeven, payment, saltCap, apprInYear, valuePath, taxBase };
