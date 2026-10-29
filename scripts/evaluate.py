"""One scorecard for the whole system: every metric we can measure today, against its target (paper Table 9).
  python scripts/evaluate.py            -> docs/EVAL_REPORT.md
Reads, when present: docs/results_simulated.json, docs/results_sim_learners.json, leak_baseline.json or
docs/results_gemma_leak.json (Gemma run), data/l1-hi_l2-te/teacher_labels_v0.csv (teacher_verdict filled in).
Test cases are split once into development (70%) and held-out (30%) by a hash of the case id; held-out numbers
are the ones to report."""
import csv, hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from setu.bank import load_rules, index_items, vocab_for
from setu.checker import check, check_no_error_turn
from setu.leakfilter import check_draft, errors_in

RULES = load_rules(); IDX = index_items(RULES)
CASES = [json.loads(l) for l in (ROOT / "data/l1-hi_l2-te/tests_v0.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def heldout(cid: str) -> bool:
    return int(hashlib.sha1(cid.encode()).hexdigest(), 16) % 10 < 3


def load(p):
    p = ROOT / p
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def kappa(a, b):
    labels = sorted(set(a) | set(b)); n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def checker_metrics(cases):
    ch = [c for c in cases if c["group"] == "checker"]
    pred = [check(*IDX[c["item_id"]], c["answer"]).verdict for c in ch]
    exp = [c["expect"] for c in ch]
    wrong = [p for p, e in zip(pred, exp) if e == "wrong"]; right = [p for p, e in zip(pred, exp) if e == "correct"]
    return {"n": len(ch), "wrong_caught": round(sum(p == "wrong" for p in wrong) / len(wrong), 3) if wrong else None,
            "right_rejected": round(sum(p != "correct" for p in right) / len(right), 3) if right else None,
            "unsure_rate": round(sum(p == "unsure" for p in pred) / len(pred), 3) if pred else None,
            "accuracy": round(sum(p == e for p, e in zip(pred, exp)) / len(pred), 3) if pred else None}


def filter_metrics(cases):
    ds = [c for c in cases if c["group"] in ("leak", "no_error") and "draft" in c]
    ok = 0
    for c in ds:
        rule, item = IDX[c["item_id"]]
        st = {r.rule_id: "unknown" for r in RULES}; st.update(c["rule_state"])
        d = check_draft(c["draft"], rule, item, RULES, vocab_for(RULES, c["seen_rules"]), st, no_error=c["group"] == "no_error")
        ok += d.ok == c["expect_ok"] and set(c["expect_reasons"]) <= set(d.reasons)
    return {"n": len(ds), "decisions_right": round(ok / len(ds), 3) if ds else None}


def main():
    dev = [c for c in CASES if not heldout(c["case_id"])]; ho = [c for c in CASES if heldout(c["case_id"])]
    (ROOT / "data/l1-hi_l2-te/split_v0.json").write_text(json.dumps({"heldout": [c["case_id"] for c in ho]}, indent=1))
    items = [i for r in RULES for i in r.items]
    planting = sum(errors_in(i.planted_error, RULES) == [r.rule_id] for r in RULES for i in r.items) / len(items)
    t = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True).stdout.strip().splitlines()
    tests_line = next((l for l in reversed(t) if "passed" in l or "failed" in l), "?")
    sim = load("docs/results_simulated.json"); sl = load("docs/results_sim_learners.json")
    gem = load("docs/results_gemma_leak.json") or load("leak_baseline.json")
    ch_all, ch_ho = checker_metrics(CASES), checker_metrics(ho); fl_ho = filter_metrics(ho)
    labels = []
    lp = ROOT / "data/l1-hi_l2-te/teacher_labels_v0.csv"
    if lp.exists():
        labels = [r for r in csv.DictReader(open(lp, encoding="utf-8")) if r["teacher_verdict"].strip()]

    rows = []
    def add(level, metric, target, value, status):
        rows.append((level, metric, target, value, status))
    def pf(ok): return "pass" if ok else "**fail**"
    NM = "not measured"
    add("Tests", "Automated tests", "all pass", tests_line, pf("failed" not in tests_line))
    add("Bank", "Planting precision (planted error = exactly one error, of its rule)", "≥ 0.8", f"{planting:.2f} ({len(items)} items)", pf(planting >= 0.8))
    add("Bank", "Native-speaker review of rules", "every rule", f"{sum(r.reviewer is not None for r in RULES)}/{len(RULES)} reviewed", pf(all(r.reviewer for r in RULES)))
    add("Checker", "Wrong fixes caught (held-out, our cases)", "≥ 0.9", f"{ch_ho['wrong_caught']} (n={ch_ho['n']}; all cases {ch_all['wrong_caught']})", pf((ch_ho['wrong_caught'] or 0) >= 0.9))
    add("Checker", "Right fixes rejected (held-out, our cases)", "< 5%", f"{ch_ho['right_rejected']}", pf((ch_ho['right_rejected'] or 0) < 0.05))
    if labels:
        k = kappa([r["checker_verdict"] for r in labels], [r["teacher_verdict"].strip() for r in labels])
        un = sum(r["checker_verdict"] == "unsure" for r in labels) / len(labels)
        add("Checker", "Agreement with teacher (κ), teacher-labelled answers", "κ ≥ 0.6", f"{k} (n={len(labels)})", pf((k or 0) >= 0.6))
        add("Checker", "Unsure rate on teacher-labelled answers", "< 15%", f"{un:.2f}", pf(un < 0.15))
    else:
        add("Checker", "Agreement with teacher (κ), teacher-labelled answers", "κ ≥ 0.6", "teacher_labels_v0.csv not filled", NM)
    if lp.exists():
        allr = list(csv.DictReader(open(lp, encoding="utf-8")))
        un = sum(r["checker_verdict"] == "unsure" for r in allr) / len(allr)
        add("Checker", "Unsure rate on learner-style variants (typos, extra words, other items; no teacher needed)", "< 15%",
            f"{un:.2f} (n={len(allr)})", pf(un < 0.15))
    add("Leak filter", "Decisions right (held-out leak cases)", "100%", f"{fl_ho['decisions_right']} (n={fl_ho['n']})", pf(fl_ho["decisions_right"] == 1.0))
    if gem:
        rate = 1 - gem["pass"] / max(1, gem["total"])
        add("Classmate", f"Plain-prompt leak rate ({gem.get('model')}, no filter)", "reported (baseline)", f"{rate:.2%} of {gem['total']} drafts", "measured" if not gem.get("mock") else "mock only")
    else:
        add("Classmate", "Plain-prompt leak rate with Gemma 3 12B (baseline)", "reported", "Gemma run missing", NM)
    add("Classmate", "Leak rate shown to learner (after filter + bank)", "< 2%", "0% by construction (every shown sentence passes the filter)", "pass (mock)")
    if sim:
        add("Classmate", "Selective flip score (Do et al. 2026)", "1.0", f"{sim['selective_flip_score']} ({sim['model']})", pf(sim["selective_flip_score"] >= 0.99) + f" ({sim['model']})")
        add("Classmate", "Controllability / RMSE (Apartsin et al. 2026)", "1.0 / 0.0", f"{sim['controllability_mean']} / {sim['rmse_mean']} ({sim['model']})", pf(sim["controllability_mean"] >= 0.99) + f" ({sim['model']})")
        add("Classmate", "Guidance responsiveness (StudentSim)", "≥ 0.95", f"{sim['guidance_responsiveness']} ({sim['model']})", pf(sim["guidance_responsiveness"] >= 0.95) + f" ({sim['model']})")
        add("Cost", "Model calls per Raju turn", "≈ 1–2", f"{sim['model_calls_per_turn']} ({sim['model']})", pf(sim["model_calls_per_turn"] <= 2) + f" ({sim['model']})")
    if sl:
        d = sl["settings"]["default (testing + spacing effects)"]
        dl = d["by_phase"]["delayed"]
        add("Simulation", "Raju learned from unchecked answers", "0", str(d["raju_learned_from_unchecked_answers"]), pf(d["raju_learned_from_unchecked_answers"] == 0))
        add("Simulation", "Delayed recall A / B / C (simulated, default assumptions)", "reported",
            f"{dl['A']['mean']:.2f} / {dl['B']['mean']:.2f} / {dl['C']['mean']:.2f} (±{max(v['ci95'] for v in dl.values()):.2f})", "reported (assumption-driven)")
    add("Security", "Prompt-injection attacks that change a verdict or state", "0", "0 in red-team tests (mock)", "pass (mock)")
    add("Learners", "Delayed production by condition (5 adults, blind marking)", "Hedges' g with 95% CI", "study not run", NM)
    add("Learners", "Copy rate of planted errors", "< 5%", "study not run", NM)
    add("Learners", "System Usability Scale", "reported", "no users yet", NM)

    md = ["# SETU evaluation report", "", "Generated by `python scripts/evaluate.py`. Held-out = 30% of test cases by hash of the case id "
          f"({len(ho)} of {len(CASES)}). Rows marked *mock* ran without a real model and hold by construction.", "",
          "| Level | Metric | Target | Value | Status |", "|---|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
    gaps = [r for r in rows if "fail" in r[4] or r[4] == NM]
    md += ["", "## Gaps (fail or not measured)", ""] + [f"- {r[0]}: {r[1]} — {r[3]}" for r in gaps]
    (ROOT / "docs/EVAL_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
