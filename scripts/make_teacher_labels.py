"""Writes data/l1-hi_l2-te/teacher_labels_v0.csv: learner-style answers for a native Telugu teacher to mark.
Fill the teacher_verdict column with correct / wrong / unsure (and a note if useful); then run scripts/evaluate.py.
The checker's own verdict is included so the teacher can see disagreements, but should be hidden while marking
(sort by id, cover the column) to keep the marking blind."""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setu.bank import load_rules
from setu.checker import check

rules = load_rules(); rows = []; n = 0
for k, rule in enumerate(rules):
    for item in rule.items:
        other = rules[(k + 1) % len(rules)].items[0].accepted[0]
        acc = item.accepted[0]
        variants = [("accepted form", acc), ("planted error left in", item.planted_error),
                    ("another item's correct sentence", other), ("one letter dropped", acc[:-1]),
                    ("extra word added", acc + " కదా")]
        for kind, ans in variants:
            n += 1
            rows.append({"id": f"TL-{n:03d}", "item_id": item.item_id, "english": item.english, "answer": ans,
                         "variant": kind, "checker_verdict": check(rule, item, ans).verdict,
                         "teacher_verdict": "", "teacher_note": ""})
out = Path(__file__).resolve().parent.parent / "data/l1-hi_l2-te/teacher_labels_v0.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "rows ->", out)
