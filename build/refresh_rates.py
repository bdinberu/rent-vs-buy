"""Update data/rates.json with the latest Freddie Mac weekly rates from FRED.

Needs a free FRED API key in the FRED_API_KEY environment variable
(https://fred.stlouisfed.org/docs/api/api_key.html).
Series: MORTGAGE30US and MORTGAGE15US (Freddie Mac Primary Mortgage Market Survey, published Thursdays).
Exits with an error, changing nothing, if the response looks wrong.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.stlouisfed.org/fred/series/observations"

def latest(payload):
    """Return (iso_date, value) for the most recent non-missing observation in a FRED response."""
    for ob in payload.get("observations", []):
        if ob.get("value") not in (None, "", "."):
            return ob["date"], round(float(ob["value"]), 2)
    raise ValueError("no usable observations in response")

def fetch(series, key):
    q = urllib.parse.urlencode({"series_id": series, "api_key": key, "file_type": "json", "sort_order": "desc", "limit": 5})
    with urllib.request.urlopen(f"{API}?{q}", timeout=30) as r:
        return json.load(r)

def updated_rates(old, p30, p15, today):
    (d30, r30), (d15, r15) = latest(p30), latest(p15)
    if d30 != d15:
        raise ValueError(f"30-year ({d30}) and 15-year ({d15}) are from different weeks")
    for name, v in (("30-year", r30), ("15-year", r15)):
        if not 2 <= v <= 15:
            raise ValueError(f"{name} rate {v}% is implausible")
    if d30 < old["week"]:
        raise ValueError(f"FRED's latest week {d30} is older than the current {old['week']}")
    if abs(r30 - old["rate30"]) > 1.0:
        raise ValueError(f"30-year rate moved {r30 - old['rate30']:+.2f} points in one update; check by hand")
    return {"rate30": r30, "rate15": r15, "week": d30, "as_of": today}

def main():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        sys.exit("FRED_API_KEY is not set")
    path = ROOT / "data/rates.json"
    old = json.loads(path.read_text())
    new = updated_rates(old, fetch("MORTGAGE30US", key), fetch("MORTGAGE15US", key), date.today().isoformat())
    if new["week"] == old["week"] and new["rate30"] == old["rate30"] and new["rate15"] == old["rate15"]:
        print(f"No new rates (still week of {old['week']})"); return
    path.write_text(json.dumps(new, indent=1) + "\n")
    print(f"Rates updated: {old['rate30']}% -> {new['rate30']}% (30 yr), {old['rate15']}% -> {new['rate15']}% (15 yr), week of {new['week']}")

if __name__ == "__main__":
    main()
