"""Prints the Python checker / leak-filter decisions for every test case and teacher-label row, for the JS parity check."""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from setu.bank import load_rules, index_items, vocab_for
from setu.checker import check
from setu.leakfilter import check_draft
R = load_rules(); I = index_items(R); out = []
for c in [json.loads(l) for l in open(ROOT / "data/l1-hi_l2-te/tests_v0.jsonl", encoding="utf-8")]:
    if c["group"] == "checker":
        out.append({"t": "check", "item": c["item_id"], "a": c["answer"], "v": check(*I[c["item_id"]], c["answer"]).verdict})
    if c["group"] in ("leak", "no_error") and "draft" in c:
        st = {r.rule_id: "unknown" for r in R}; st.update(c["rule_state"]); seen = sorted(vocab_for(R, c["seen_rules"]))
        d = check_draft(c["draft"], *I[c["item_id"]], R, set(seen), st, no_error=c["group"] == "no_error")
        out.append({"t": "draft", "item": c["item_id"], "d": c["draft"], "seen": seen, "st": st, "ne": c["group"] == "no_error", "ok": d.ok, "r": d.reasons})
for r in csv.DictReader(open(ROOT / "data/l1-hi_l2-te/teacher_labels_v0.csv", encoding="utf-8")):
    out.append({"t": "check", "item": r["item_id"], "a": r["answer"], "v": r["checker_verdict"]})
print(json.dumps(out, ensure_ascii=False))
