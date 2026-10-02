"""Offline tests for build/refresh_rates.py using responses shaped like FRED's documented JSON."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
from refresh_rates import latest, updated_rates

def resp(*obs): return {"observations": [{"date": d, "value": v} for d, v in obs]}
old = {"rate30": 7.28, "rate15": 6.60, "week": "2026-10-01", "as_of": "2026-10-02"}
passed = 0
def expect_error(fn, why):
    global passed
    try: fn()
    except ValueError: passed += 1; return
    raise AssertionError(f"should have rejected: {why}")

assert latest(resp(("2026-10-08", "."), ("2026-10-01", "7.28"))) == ("2026-10-01", 7.28); passed += 1
new = updated_rates(old, resp(("2026-10-08", "7.31")), resp(("2026-10-08", "6.64")), "2026-10-09")
assert new == {"rate30": 7.31, "rate15": 6.64, "week": "2026-10-08", "as_of": "2026-10-09"}; passed += 1
expect_error(lambda: updated_rates(old, resp(("2026-10-08", "7.31")), resp(("2026-10-01", "6.60")), "x"), "mismatched weeks")
expect_error(lambda: updated_rates(old, resp(("2026-10-08", "73.1")), resp(("2026-10-08", "6.6")), "x"), "implausible value")
expect_error(lambda: updated_rates(old, resp(("2026-09-24", "7.03")), resp(("2026-09-24", "6.42")), "x"), "older week")
expect_error(lambda: updated_rates(old, resp(("2026-10-08", "8.60")), resp(("2026-10-08", "7.9")), "x"), "jump over 1 point")
expect_error(lambda: latest(resp(("2026-10-08", "."))), "no usable data")
print(f"PASS: {passed} refresh tests")
