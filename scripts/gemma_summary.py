"""Reads everything a Gemma run produced and writes one readable summary (docs/results_gemma/SUMMARY.md).
  python scripts/gemma_summary.py
Numbers are copied from the result files, never recomputed by hand."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "docs/results_gemma"


def load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main():
    info, pre = load(R / "run_info.json") or {}, load(R / "preflight.json") or {}
    leak, base = load(R / "leak_plain.json"), load(R / "baselines.json")
    sim, ev = load(R / "sim_learners.json"), load(R / "simulated_eval.json")
    L = ["# Gemma run summary", ""]
    L += [f"- Model: **{info.get('model', pre.get('model', '?'))}**  ·  profile: {info.get('profile', '?')}  ·  machine: {info.get('machine', '?')}",
          f"- Started {info.get('started', '?')}, took {info.get('minutes', '?')} min  ·  code commit {info.get('commit', '?')}",
          f"- Steps: " + (", ".join(f"{k}={'ok' if v == 0 else 'FAILED(' + str(v) + ')'}" for k, v in info.get('steps', {}).items()) or "?"), ""]
    if base:
        L += [f"## Raju generation, four ways ({base['status']}, {base['reps']} rep(s), {base['seconds']} s)", "",
              "| Method | Cases | Valid sentence | First draft passes | Bank fallback | Leak | Calls/case | Median s/case | Excluded (errors) |", "|---|---|---|---|---|---|---|---|---|"]
        for m, v in base["methods"].items():
            L.append(f"| {m} | {v['n']} | {v.get('valid_rate')} | {v.get('first_draft_pass_rate')} | {v.get('fallback_rate')} | {v.get('leak_rate')} | {v.get('calls_per_case')} | {v.get('median_latency_s')} | {v['excluded_error_cases']} |")
        bad = {m: v["shown_fails_filter"] for m, v in base["methods"].items() if v.get("shown_fails_filter")}
        L += ["", "Safety invariant (a shown sentence must pass the filter again): " + ("**VIOLATED** " + str(bad) if bad else "held on every case."),
              ("Model errors seen: " + "; ".join(base["all_errors"])) if base.get("all_errors") else "No model errors."]
        L += ["", "Reading it: 'valid' = the sentence shown has exactly the planned mistake, only seen words, no answer leak. For prompt_only and plain_no_reference nothing stops a bad sentence from being shown, so 1 − valid is how often it would be.", ""]
    if leak:
        r = leak["reasons"]
        L += [f"## Plain prompt, no reference sentence ({leak['model']}{', MOCK' if leak.get('mock') else ''})", "",
              f"{leak['pass']} of {leak['total']} drafts passed the filter ({100*leak['pass']/max(1,leak['total']):.1f}%). Reasons for failure: " + ", ".join(f"{k} {v}" for k, v in sorted(r.items(), key=lambda x: -x[1])), ""]
    if ev:
        L += [f"## Controllability with this model ({ev.get('model')})", "", "```", json.dumps({k: v for k, v in ev.items() if k != 'rows'}, indent=1)[:1200], "```", ""]
    if sim:
        d = sim.get("settings", {}).get("default (testing + spacing effects)")
        L += [f"## Simulated learners, default assumptions ({sim.get('model')})", "", "```", json.dumps(d, indent=1)[:1500] if d else "missing", "```",
              "These follow from the assumptions in setu/simlearner.py; they are not evidence about people.", ""]
    stu = load(R / "students_llm.json")
    if stu:
        c = stu["controlled"]
        L += [f"## AI student simulator ({stu['model']}{', MOCK' if stu.get('mock') else ''})", "",
              f"The model writes what the learner types; the parametric learner decides right or wrong. Of {c['n_intended_correct']} answers meant to be correct, the checker marked **{c['intended_correct_marked_correct']}** correct (unsure {c['intended_correct_marked_unsure']}); of {c['n_intended_wrong']} meant to be wrong, **{c['intended_wrong_marked_wrong']}** were marked wrong.", "",
              "| Intended / style | n | correct | wrong | unsure |", "|---|---|---|---|---|"]
        L += [f"| {k} | {v['n']} | {v['correct']} | {v['wrong']} | {v['unsure']} |" for k, v in c["checker_on_llm_written_answers"].items()]
        d = c["by_phase"]["delayed"]
        L += ["", f"Delayed recall with LLM-written answers: A {d['A']['mean']}, B {d['B']['mean']}, C {d['C']['mean']}.", ""]
        if "free" in stu:
            f = stu["free"]
            L += [f"Uncontrolled student (told which rules it has not met): marked correct on the unmet rule **{f['rate_correct_on_unmet_rule']}** of {f['n']} attempts, wrong {f['rate_planted_mistake_or_wrong']}, unsure {f['rate_unsure']}. A high first number means prompting alone cannot make an LLM play a weak learner.", ""]
    (R / "SUMMARY.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    main()
