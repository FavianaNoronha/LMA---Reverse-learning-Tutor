const { chromium } = require('playwright'); const fs = require('fs');
(async () => { const b = await chromium.launch(); const p = await b.newPage();
  await p.setContent('<!doctype html><html><head><meta charset="utf-8"></head><body>' + fs.readFileSync('app/hosted/setu_app.html','utf8') + '</body></html>');
  const exp = JSON.parse(require('child_process').execSync('python3 scripts/py_expected_for_parity.py').toString());
  const bad = await p.evaluate(exp => { const E = window.__setu; const RULESX = {}; const out = [];
    for (const c of exp) {
      if (c.t === 'check') { const [rule, item] = window.__items(c.item); const v = E.check(rule, item, c.a).verdict; if (v !== c.v) out.push([c, v]); }
      else { const [rule, item] = window.__items(c.item); const d = E.checkDraft(c.d, rule, item, new Set(c.seen), c.st, c.ne); if (d.ok !== c.ok || JSON.stringify(d.reasons) !== JSON.stringify(c.r)) out.push([c, d]); } }
    return out; }, exp);
  console.log('cases', exp.length, 'mismatches', bad.length, JSON.stringify(bad.slice(0,3))); await b.close(); })();
