"""Merge the native reviewer's returned sheets into the repo (idempotent).
  sheet 3 (blind marking)  -> data/l1-hi_l2-te/teacher_labels_v0.csv  (teacher_verdict, teacher_verdict_raw, teacher_note)
  sheet 1 / 2 (rule review) -> level, frequency, review_notes on each item; rule status/reviewer/date
The reviewer's raw wording is kept in teacher_verdict_raw; spelling slips ('corrcet') are normalised for scoring only.
Sheet 1 came back with its Telugu replaced by '?' (saved as ASCII), so only its ratings are used, joined on item_id."""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from setu.bank import load_rules
from setu.checker import check

R = ROOT / "docs/reviewer_pack/returned"
REVIEWER, DATE = "R1 (bilingual team member; initials pending)", "2026-11-02"
NORM = {"correct": "correct", "corrcet": "correct", "corect": "correct", "wrong": "wrong", "unsure": "unsure", "partially correct": "unsure"}
K = lambda row, start: next(v for k, v in row.items() if k.startswith(start))

# --- sheet 3 -> labels
lp = ROOT / "data/l1-hi_l2-te/teacher_labels_v0.csv"
rows = list(csv.DictReader(open(lp, encoding="utf-8")))
her = {r["id"]: r for r in csv.DictReader(open(R / "3_mark_learner_answers_BLIND_RETURNED.csv", encoding="utf-8-sig"))}
rules = load_rules(); items = {i.item_id: (r, i) for r in rules for i in r.items}
for m in rows:
    h = her[m["id"]]; assert h["item_id"] == m["item_id"] and h["learner_answer"].strip() == m["answer"].strip()
    m.setdefault("checker_verdict_at_return", m["checker_verdict"])      # frozen: what the checker said when the labels came back
    raw = K(h, "your_verdict").strip(); m["teacher_verdict_raw"] = raw; m["teacher_verdict"] = NORM[raw.lower()]
    m["teacher_note"] = h["why (optional)"].strip()
    r, i = items[m["item_id"]]; m["checker_verdict"] = check(r, i, m["answer"]).verdict   # refreshed with the current checker
cols = ["id", "item_id", "english", "answer", "variant", "checker_verdict_at_return", "checker_verdict", "teacher_verdict", "teacher_verdict_raw", "teacher_note"]
with open(lp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows([{c: m.get(c, "") for c in cols} for m in rows])

# --- sheets 1 and 2 -> item metadata
def sheet(name, enc):
    return list(csv.DictReader(open(R / name, encoding=enc)))
meta = {}
for name, enc in [("1_review_hindi_to_telugu_rules_RETURNED_telugu_lost.csv", "latin-1"), ("2_review_telugu_to_hindi_rules_RETURNED.csv", "utf-8-sig")]:
    for r in sheet(name, enc):
        meta[r["item_id"]] = {"level": K(r, "Q6").strip(), "frequency": K(r, "Q1").strip().lower(),
                              "q5": K(r, "Q5").strip(), "q4": K(r, "Q4").strip(), "q2": K(r, "Q2").strip().lower(), "q3": K(r, "Q3").strip().lower()}
for path in ["data/l1-hi_l2-te/rules.json", "data/l1-te_l2-hi/rules.json"]:
    p = ROOT / path; data = json.loads(p.read_text(encoding="utf-8"))
    for rule in data:
        ok = True
        for it in rule["items"]:
            m = meta.get(it["item_id"])
            if not m: ok = False; continue
            it["level"], it["frequency"] = m["level"], m["frequency"]
            notes = []
            if m["q5"].lower() not in ("yes", "yes ", ""): notes.append(f"explanation: {m['q5']}")
            if m["q4"] and "?" not in m["q4"]: notes.append(f"reviewer's other forms (not used by checker): {m['q4']}")
            it["review_notes"] = notes
            ok &= m["q2"].startswith("y") and m["q3"].startswith("y") and m["q5"].lower().startswith("y")
        if ok:
            rule["status"], rule["reviewer"], rule["reviewed_at"] = "native_checked", REVIEWER, DATE
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("labels:", len(rows), "| rules native_checked:",
      sum(r.get("status") == "native_checked" for f in ["data/l1-hi_l2-te/rules.json", "data/l1-te_l2-hi/rules.json"] for r in json.load(open(ROOT / f, encoding="utf-8"))))
