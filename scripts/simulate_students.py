"""AI student simulator runs (setu/llmstudent.py).

 1. controlled (default): the parametric learner decides right / wrong / don't know, the LLM writes what the learner
    types, the real checker marks it. Reports (a) the A/B/C study result with LLM-written answers, and (b) for every
    style of answer, what the checker said - a check of the checker on learner variation we did not write.
 2. --free: the uncontrolled student. The LLM is told which rules the learner has NOT met and translates the item.
    Reports how often it is right anyway (the competence problem: an unconstrained LLM student knows too much).

  python scripts/simulate_students.py --base-url http://localhost:11434/v1 --model gemma3:12b --n 3
  python scripts/simulate_students.py --mock         # dry run of the harness (NOT a result)
"""
from __future__ import annotations
import argparse, json, random, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.simulate_learners import mean_ci
from setu.bank import index_items, load_rules
from setu.checker import check
from setu.llm import AgentMockLLM, OpenAICompatLLM
from setu.llmstudent import LLMStudent, StudentMock
from setu.memory import Store
from setu.session import Tutor
from setu.simlearner import Params, run_learner


def controlled(n, raju_llm_factory, student_llm_factory, seed, n_rules=9):
    per = {ph: {c: [] for c in "ABC"} for ph in ("pre", "post", "delayed", "transfer")}
    log, fails, calls = [], 0, 0
    for i in range(n):
        with tempfile.TemporaryDirectory() as d:
            t = Tutor(Store(d), raju_llm_factory(), seed=seed + i, p_no_error=0.2, agent=True)
            student = LLMStudent(student_llm_factory(), random.Random(seed + i))
            out = run_learner(t, f"stu{i:02d}", Params(), seed + i, [r.rule_id for r in t.rules][:n_rules], writer=student)
            log += out["student_log"]; fails += student.failures; calls += student.calls
            for ph, byc in out["results"].items():
                for c, v in byc.items():
                    per[ph][c].append(v["correct"] / v["n"])
    table = defaultdict(Counter)
    for e in log:
        table[f"{e['intended']} / {e['style']}"][e["verdict"]] += 1
    by_style = {k: {"n": sum(v.values()), **{x: round(v[x] / sum(v.values()), 3) for x in ("correct", "wrong", "unsure")}} for k, v in sorted(table.items())}
    ic = [e for e in log if e["intended"] == "correct" and "fallback" not in e["style"]]
    iw = [e for e in log if e["intended"] == "wrong" and "fallback" not in e["style"]]
    return {"learners": n, "student_calls": calls, "student_failures": fails,
            "by_phase": {ph: {c: dict(zip(("mean", "ci95"), mean_ci(v))) for c, v in byc.items() if v} for ph, byc in per.items()},
            "checker_on_llm_written_answers": by_style,
            "intended_correct_marked_correct": round(sum(e["verdict"] == "correct" for e in ic) / max(1, len(ic)), 3),
            "intended_correct_marked_unsure": round(sum(e["verdict"] == "unsure" for e in ic) / max(1, len(ic)), 3),
            "intended_wrong_marked_wrong": round(sum(e["verdict"] == "wrong" for e in iw) / max(1, len(iw)), 3),
            "n_intended_correct": len(ic), "n_intended_wrong": len(iw)}


FREE = ("You are Ankit, an adult Hindi speaker learning Telugu. You have met only these Telugu grammar points so far: {known}. "
        "You have NOT met this one: {rule}. Translate into Telugu the way Ankit would, using only what he has learned. "
        "Meaning: \"{english}\". Output only the Telugu sentence.")


def free(llm, reps):
    rules = load_rules(); idx = index_items(rules); rows = []; errors = []
    for iid, (rule, item) in idx.items():
        known = ", ".join(r.name for r in rules if r.rule_id != rule.rule_id and r.category != rule.category) or "none"
        for _ in range(reps):
            try:
                out = llm.chat([{"role": "user", "content": FREE.format(known=known, rule=rule.name, english=item.english)}], max_tokens=60)
                text = next((l.strip() for l in out.strip().splitlines() if l.strip()), "")
            except Exception as e:
                errors.append(str(e)[:100]); continue
            rows.append({"item": iid, "text": text, "verdict": check(rule, item, text).verdict})
    c = Counter(r["verdict"] for r in rows); n = max(1, len(rows))
    return {"n": len(rows), "errors": errors[:5], "rate_correct_on_unmet_rule": round(c["correct"] / n, 3),
            "rate_planted_mistake_or_wrong": round(c["wrong"] / n, 3), "rate_unsure": round(c["unsure"] / n, 3),
            "reading": "A learner who has NOT met the rule should usually be wrong on it. A high 'correct' rate means the LLM student is too competent to be controlled by prompting alone."}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url"); ap.add_argument("--model", default="gemma3:12b"); ap.add_argument("--mock", action="store_true")
    ap.add_argument("--n", type=int, default=3); ap.add_argument("--seed", type=int, default=21); ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--free", action="store_true"); ap.add_argument("--out", default="docs/results_students_llm.json")
    a = ap.parse_args()
    if a.mock or not a.base_url:
        raju, stu, name = (lambda: AgentMockLLM(leaky_every=3)), (lambda: StudentMock()), "mock"
    else:
        raju, stu, name = (lambda: OpenAICompatLLM(a.base_url, a.model)), (lambda: OpenAICompatLLM(a.base_url, a.model)), a.model
    res = {"model": name, "mock": name == "mock",
           "note": "Outcomes are decided by the parametric learner (assumptions in setu/simlearner.py); the model only writes the typing. Not evidence about people."}
    res["controlled"] = controlled(a.n, raju, stu, a.seed)
    if a.free:
        res["free"] = free(StudentMock() if name == "mock" else OpenAICompatLLM(a.base_url, a.model), a.reps)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    c = res["controlled"]
    print(f"{name}: intended-correct marked correct {c['intended_correct_marked_correct']} (unsure {c['intended_correct_marked_unsure']}, n={c['n_intended_correct']}); "
          f"intended-wrong marked wrong {c['intended_wrong_marked_wrong']} (n={c['n_intended_wrong']})")
    for k, v in c["checker_on_llm_written_answers"].items():
        print(f"  {k:28s} n={v['n']:3d}  correct {v['correct']}  wrong {v['wrong']}  unsure {v['unsure']}")
    d = c["by_phase"]["delayed"]; print("  delayed recall  A %.2f  B %.2f  C %.2f" % tuple(d[x]["mean"] for x in "ABC"))
    if a.free:
        print("  free student:", {k: v for k, v in res["free"].items() if k.startswith("rate")})
