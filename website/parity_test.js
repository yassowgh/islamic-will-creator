const E = require("./engine.js");
const fixtures = require("./fixtures.json");
let pass = 0, fail = 0;
const failures = [];
for (const fx of fixtures) {
  const heirs = Object.entries(fx.heirs).map(([r, c]) => ({ relationship: r, count: c }));
  let r;
  try { r = E.calculate(fx.madhhab, heirs); }
  catch (e) { fail++; failures.push([fx, "threw " + e.message]); continue; }
  const got = {};
  for (const s of r.shares) if (!s.total.isZero()) got[s.relationship] = s.total.toString();
  const want = {};
  for (const [rel, [n, d]] of Object.entries(fx.expected)) want[rel] = d === 1 ? `${n}` : `${n}/${d}`;
  const ok = JSON.stringify(Object.entries(got).sort()) === JSON.stringify(Object.entries(want).sort())
    && r.awl === fx.awl && r.radd === fx.radd;
  if (ok) pass++;
  else { fail++; failures.push([fx, JSON.stringify(got), JSON.stringify(want), "awl:" + r.awl + "/" + fx.awl, "radd:" + r.radd + "/" + fx.radd]); }
}
console.log(`parity: ${pass} passed, ${fail} failed of ${fixtures.length}`);
for (const f of failures.slice(0, 5)) console.log(JSON.stringify(f, null, 1));
process.exit(fail ? 1 : 0);
