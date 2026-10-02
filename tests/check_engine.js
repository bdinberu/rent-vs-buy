// Compare the web app's engine (src/engine.js) with the Python reference model on every case.
const path = require("path");
const { run } = require(path.join(__dirname, "../src/engine.js"));
const cases = require(path.join(__dirname, "cases.json"));
let maxErr = 0, bad = 0;
for (const c of cases) {
  const r = run(c.p);
  for (const [a, b] of [[r.ownerNW, c.py.owner], [r.renterNW, c.py.renter], [r.fullInt, c.py.fullInt], [r.pmt, c.py.pmt], [r.fullPmi, c.py.pmi]]) {
    if (!Number.isFinite(a) || !Number.isFinite(b)) bad++;
    else maxErr = Math.max(maxErr, Math.abs(a - b));
  }
}
console.log(`cases ${cases.length}, max difference $${maxErr.toExponential(2)}, non-finite ${bad}`);
if (bad > 0 || maxErr > 0.01) { console.error("FAIL: engine disagrees with the reference model"); process.exit(1); }
console.log("PASS: engine matches the reference model");
