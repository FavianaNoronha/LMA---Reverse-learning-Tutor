"""Simulated learners through all three study conditions (A teach Raju, B matched examples, C normal tutor).
  python scripts/simulate_learners.py                # 20 learners x sensitivity grid, mock model
Writes docs/results_sim_learners.json. These numbers follow from the assumptions in setu/simlearner.py; they test
the machinery and show which assumptions drive the A/B/C differences. They are NOT evidence about people."""
import argparse, json, math, random, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setu.llm import MockLLM, OpenAICompatLLM
from setu.memory import Store
from setu.session import Tutor
from setu.simlearner import Params, run_learner

GRID = {   # name -> (learner assumptions, tutor settings)
    "default (testing + spacing effects)": (Params(), {}),
    "no testing effect (restudy = retrieval)": (Params(restudy_base=1.2, restudy_gain=3.0), {}),
    "self-explanation helps (why? x1.3)": (Params(explain_gain=1.3), {}),
    "weak learners (half-life 0.5 day)": (Params(h0=0.5), {}),
    "Raju needs 2 lessons per rule": (Params(), {"teach_needed": 2}),
}


def mean_ci(xs):
    n = len(xs); m = sum(xs) / n
    sd = (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5 if n > 1 else 0.0
    return round(m, 3), round(1.96 * sd / math.sqrt(n), 3)


def run(params: Params, n: int, llm_factory, seed: int, n_rules: int = 9, tutor_kw: dict | None = None):
    per = {ph: {c: [] for c in "ABC"} for ph in ("pre", "post", "delayed", "transfer")}
    leaks = copies = calls = turns = 0; tt = {}
    for i in range(n):
        with tempfile.TemporaryDirectory() as d:
            t = Tutor(Store(d), llm_factory(), seed=seed + i, p_no_error=0.2, agent=True, **(tutor_kw or {}))
            ids = [r.rule_id for r in t.rules][:n_rules]
            out = run_learner(t, f"sim{i:02d}", params, seed + i, ids)
            leaks += out["raju_changed_without_correct"]; copies += out["copies"]
            for e in t.store.load(f"sim{i:02d}").events:
                tt[e.turn_type] = tt.get(e.turn_type, 0) + 1
            st = t.status(f"sim{i:02d}"); calls += st["model_calls"]; turns += st["turns"]
            for ph, byc in out["results"].items():
                for c, v in byc.items():
                    per[ph][c].append(v["correct"] / v["n"])
    res = {ph: {c: dict(zip(("mean", "ci95"), mean_ci(v))) for c, v in byc.items() if v} for ph, byc in per.items()}
    return {"by_phase": res, "raju_learned_from_unchecked_answers": leaks,
            "copied_planted_errors_in_delayed_and_transfer": copies, "model_calls_per_raju_turn": round(calls / max(1, turns), 2), "raju_turn_types": tt}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20); ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--base-url"); ap.add_argument("--model", default="gemma3:12b")
    ap.add_argument("--out", default="docs/results_sim_learners.json")
    ap.add_argument("--default-only", action="store_true", help="run only the default assumption set (much faster with a real model)")
    a = ap.parse_args()
    from setu.llm import AgentMockLLM
    f = (lambda: OpenAICompatLLM(a.base_url, a.model)) if a.base_url else (lambda: AgentMockLLM(leaky_every=3))
    out = {"model": a.model if a.base_url else "agent-mock", "learners_per_setting": a.n,
           "note": "Follows from the assumptions in setu/simlearner.py; tests the machinery, not people.",
           "settings": {k: run(p, a.n, f, a.seed, tutor_kw=kw) for k, (p, kw) in GRID.items() if not a.default_only or k.startswith("default")}}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for k, v in out["settings"].items():
        d = v["by_phase"]["delayed"]
        print(f"{k:45s} delayed A {d['A']['mean']:.2f}±{d['A']['ci95']:.2f}  B {d['B']['mean']:.2f}±{d['B']['ci95']:.2f}  C {d['C']['mean']:.2f}±{d['C']['ci95']:.2f}"
              f" | unchecked->Raju {v['raju_learned_from_unchecked_answers']} | calls/turn {v['model_calls_per_raju_turn']}")
