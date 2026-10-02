"""Reference implementation of the rent-vs-buy model.
Used as ground truth to validate the web (JS) model and the Excel formulas."""
import math

DEFAULTS = dict(
    price=500000, down=0.20, rate=0.0728, term=30, closing=0.025,
    propTax=0.009, ins=0.005, maint=0.010, hoa=0.0, pmiRate=0.005,
    appr=0.040, sellCost=0.060,
    rent0=2500, rentGrowth=0.035, rentIns=15,
    invRet=0.070, infl=0.028, horizon=30,
    filing="single", margRate=0.24, stateLocalTax=0.0, otherItem=0.0,
    cgRate=0.15, itemize=False, divYield=0.011,
    priceMode="fixed", overval=0.0, halfLife=11, assessCap=None,
)

STD_2026 = {"single": 16100, "mfj": 32200}
EXCL = {"single": 250000, "mfj": 500000}
MID_LIMIT = 750000


def salt_cap(cal_year):
    caps = {2026: 40400, 2027: 40804, 2028: 41212, 2029: 41624}
    return caps.get(cal_year, 10000 if cal_year >= 2030 else 40400)


def appr_in_year(p, y):
    if p["priceMode"] != "revert":
        return p["appr"]
    h = p["halfLife"]
    if not h or h <= 0:
        return p["rentGrowth"]
    g0 = math.log(1 + p["overval"])
    return (1 + p["rentGrowth"]) * math.exp(g0 * (0.5 ** (y / h) - 0.5 ** ((y - 1) / h))) - 1


def tax_base(p, vals, y):
    v = vals[y - 1]
    if p["assessCap"] is None:
        return v
    return min(v, p["price"] * (1 + p["assessCap"]) ** (y - 1))


def value_path(p):
    v = [p["price"]]
    for y in range(1, 51):
        v.append(v[-1] * (1 + appr_in_year(p, y)))
    return v


def payment(loan, r, n_years):
    i = r / 12
    n = n_years * 12
    if i == 0:
        return loan / n
    return loan * i / (1 - (1 + i) ** -n)


def amortize(loan, r, n_years, months):
    """Monthly schedule out to `months` (zeros after payoff)."""
    pmt = payment(loan, r, n_years)
    bal = loan
    rows = []
    for m in range(1, months + 1):
        beg = bal
        if m <= n_years * 12 and beg > 1e-9:
            interest = beg * r / 12
            principal = min(beg, pmt - interest)
        else:
            interest = principal = 0.0
        bal = beg - principal
        rows.append((m, beg, interest, principal, bal))
    return pmt, rows


def run(p=None, sell_year=None):
    p = {**DEFAULTS, **(p or {})}
    H = p["horizon"] if sell_year is None else sell_year
    price = p["price"]
    down_amt = price * p["down"]
    loan = price - down_amt
    close_amt = price * p["closing"]
    months = max(H, p["term"]) * 12
    pmt, sched = amortize(loan, p["rate"], p["term"], max(months, 600))
    pmi_on = p["down"] < 0.20
    vals = value_path(p)

    # annual tax benefit
    benefit = {}
    for y in range(1, 51):
        yr = sched[(y - 1) * 12: y * 12]
        interest = sum(r[2] for r in yr)
        avg_bal = sum(r[1] for r in yr) / 12
        frac = 1.0 if avg_bal <= MID_LIMIT else MID_LIMIT / avg_bal
        ded_int = interest * frac
        ptax = p["propTax"] * tax_base(p, vals, y)
        cap = salt_cap(2026 + y)
        std = STD_2026[p["filing"]] * (1 + p["infl"]) ** y
        owner_item = ded_int + min(cap, ptax + p["stateLocalTax"]) + p["otherItem"]
        renter_item = min(cap, p["stateLocalTax"]) + p["otherItem"]
        b = p["margRate"] * (max(std, owner_item) - max(std, renter_item))
        benefit[y] = b if p["itemize"] else 0.0

    im = (1 + p["invRet"]) ** (1 / 12) - 1
    dm = p["divYield"] / 12
    div_tax_r = div_tax_o = 0.0
    renter_pf = down_amt + close_amt
    renter_contrib = renter_pf
    owner_pf = 0.0
    owner_contrib = 0.0
    tot = dict(interest=0, principal=0, pmi=0, ptax=0, ins=0, maint=0, hoa=0, rent=0, benefit=0)
    yearly = []
    for m in range(1, H * 12 + 1):
        y = math.ceil(m / 12)
        _, beg, interest, principal, end = sched[m - 1]
        v_start = vals[y - 1]
        pmi = p["pmiRate"] * loan / 12 if (pmi_on and beg > 0.78 * price and m <= p["term"] * 6) else 0.0
        c_start = price * (1 + p["infl"]) ** (y - 1)
        ptax = p["propTax"] * tax_base(p, vals, y) / 12
        ins = p["ins"] * c_start / 12
        maint = p["maint"] * c_start / 12
        hoa = p["hoa"] * (1 + p["infl"]) ** (y - 1)
        ben = benefit[y] / 12
        owner_cost = interest + principal + pmi + ptax + ins + maint + hoa - ben
        rent = p["rent0"] * (1 + p["rentGrowth"]) ** (y - 1) + p["rentIns"] * (1 + p["infl"]) ** (y - 1)
        diff = owner_cost - rent
        div_r, div_o = renter_pf * dm, owner_pf * dm
        tr, to = div_r * p["cgRate"], div_o * p["cgRate"]
        renter_pf = renter_pf * (1 + im) - tr + max(diff, 0)
        renter_contrib += div_r - tr + max(diff, 0)
        owner_pf = owner_pf * (1 + im) - to + max(-diff, 0)
        owner_contrib += div_o - to + max(-diff, 0)
        div_tax_r += tr; div_tax_o += to
        for k, v in (("interest", interest), ("principal", principal), ("pmi", pmi), ("ptax", ptax),
                     ("ins", ins), ("maint", maint), ("hoa", hoa), ("rent", rent), ("benefit", ben)):
            tot[k] += v
        if m % 12 == 0:
            yearly.append(dict(year=y, owner_cost=None))

    # liquidation at H
    home_val = vals[H]
    bal = sched[H * 12 - 1][4]
    sell = home_val * p["sellCost"]
    gain = home_val - sell - (price + close_amt)
    excl = EXCL[p["filing"]] if H >= 2 else 0
    home_tax = max(0, gain - excl) * p["cgRate"]
    owner_pf_at = owner_pf - p["cgRate"] * max(0, owner_pf - owner_contrib)
    renter_pf_at = renter_pf - p["cgRate"] * max(0, renter_pf - renter_contrib)
    owner_nw = home_val - sell - bal - home_tax + owner_pf_at
    renter_nw = renter_pf_at
    # full-term totals
    full_int = sum(r[2] for r in sched[: p["term"] * 12])
    full_pmi = sum(p["pmiRate"] * loan / 12 for r in sched[: p["term"] * 12] if pmi_on and r[1] > 0.78 * price and r[0] <= p["term"] * 6)
    full_prin = sum(r[3] for r in sched[: p["term"] * 12])
    return dict(pmt=pmt, loan=loan, owner_nw=owner_nw, renter_nw=renter_nw, diff=owner_nw - renter_nw,
                home_val=home_val, bal=bal, sell=sell, home_tax=home_tax, owner_pf=owner_pf_at,
                renter_pf_pre=renter_pf, renter_contrib=renter_contrib, owner_pf_pre=owner_pf,
                owner_contrib=owner_contrib, full_int=full_int, full_pmi=full_pmi, div_tax_r=div_tax_r, div_tax_o=div_tax_o, full_prin=full_prin, tot=tot,
                benefit=benefit)


if __name__ == "__main__":
    r = run()
    for k, v in r.items():
        if k not in ("tot", "benefit"):
            print(f"{k:16s} {v:,.2f}")
    print({k: round(v, 2) for k, v in r["tot"].items()})
    print("benefit y1..5", [round(r["benefit"][y], 2) for y in range(1, 6)])
    # sanity checks
    loan = r["loan"]
    assert abs(r["full_prin"] - loan) < 0.01, "principal must sum to loan"
    i = 0.0728 / 12; n = 360
    closed = loan * i * (1 + i) ** n / ((1 + i) ** n - 1)
    assert abs(closed - r["pmt"]) < 1e-6
    assert abs(r["full_int"] - (r["pmt"] * 360 - loan)) < 0.01
    print("checks OK; payment", round(closed, 2))
    for y in (1, 5, 10, 15, 20, 30):
        rr = run(sell_year=y)
        print(y, round(rr["owner_nw"]), round(rr["renter_nw"]), round(rr["diff"]))
