"""Simulated-learner evaluation of the weak classmate (no real learners, no real model needed).
  python scripts/simulated_eval.py                       # mock model
  python scripts/simulated_eval.py --base-url http://localhost:11434/v1 --model gemma3:12b --learners 20
Reports: selective flip score, controllability / RMSE, guidance responsiveness, bank-fallback rate,
rejected-draft rate and model calls per turn. Writes docs/results_simulated.json."""
import argparse, json, random, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setu.leakfilter import errors_in
from setu.llm import MockLLM, OpenAICompatLLM
from setu.memory import Store
from setu.metrics import selective_flip_score, rmse, controllability
from setu.session import Tutor


def run(learners: int, llm_factory, seed: int, turns: int = 24):
    rng = random.Random(seed)
    flips = {"targeted": 0, "misaligned": 0, "generic": 0}; ntr = {"targeted": 0, "misaligned": 0, "generic": 0}
    acc_ok = acc_n = resp_ok = resp_n = bank = rej = tot_turns = calls = 0
    rm, ctl = [], []
    for i in range(learners):
        with tempfile.TemporaryDirectory() as d:
            llm = llm_factory(); t = Tutor(Store(d), llm, seed=seed + i, p_no_error=0.2)
            lid = f"s{i}"; ids = []
            for _ in range(rng.randint(2, 5)):
                r = t.intro(lid)
                if r is None: break
                rule = t.by_id[r["rule_id"]]; t.answer(lid, rule.items[-1].accepted[0]); ids.append(rule.rule_id)
            tgt: dict[str, float] = {}; obs: dict[str, float] = {}      # one entry per shown sentence
            for _ in range(turns):
                out = t.turn(lid)
                if out["kind"] != "raju": break
                tot_turns += 1; bank += out["source"] == "bank"; rej += out["rejected_drafts"]
                p = t.store.load(lid).pending; rule, item = t.items[p["item_id"]]
                state_before = t.store.load(lid).raju.get(rule.rule_id)
                is_err = rule.rule_id in errors_in(p["sentence"], t.rules)
                key = f"{rule.rule_id}:{tot_turns}"
                tgt[key] = 1.0 if state_before == "taught" else 0.0       # target: may he know this rule right now?
                obs[key] = 0.0 if is_err else 1.0
                if p["turn_type"] == "planted":
                    kind = rng.choice(list(flips)); ntr[kind] += 1
                    other = next((r for r in t.rules if r.rule_id != rule.rule_id), rule)
                    text = {"targeted": item.accepted[0], "misaligned": other.items[0].accepted[0], "generic": "this is wrong"}[kind]
                    t.answer(lid, text)
                    flips[kind] += t.store.load(lid).raju.get(rule.rule_id) == "taught"
                    if kind == "targeted":                          # guidance responsiveness: right on this rule next time
                        resp_n += 1
                        t.turn(lid); q = t.store.load(lid).pending
                        resp_ok += q["rule_id"] != rule.rule_id or rule.rule_id not in errors_in(q["sentence"], t.rules)
                        t.answer(lid, "<NO_ERROR>" if q["turn_type"] == "no_error" else "unsure")
                else:
                    t.answer(lid, "<NO_ERROR>")
            st = t.store.load(lid)
            rm.append(rmse(tgt, obs)); ctl.append(controllability(tgt, obs))
            calls += st.model_calls
    fr = {k: flips[k] / max(1, ntr[k]) for k in flips}
    return {"learners": learners, "turns": tot_turns,
            "selective_flip_score": round(selective_flip_score(fr["targeted"], fr["misaligned"], fr["generic"]), 3),
            "flip_counts": flips, "feedback_trials": ntr, "rmse_mean": round(sum(rm) / len(rm), 3), "controllability_mean": round(sum(ctl) / len(ctl), 3),
            "guidance_responsiveness": round(resp_ok / max(1, resp_n), 3),
            "bank_fallback_rate": round(bank / max(1, tot_turns), 3), "rejected_drafts_per_turn": round(rej / max(1, tot_turns), 3),
            "model_calls_per_turn": round(calls / max(1, tot_turns), 2)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url"); ap.add_argument("--model", default="gemma3:12b")
    ap.add_argument("--learners", type=int, default=30); ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="docs/results_simulated.json")
    a = ap.parse_args()
    f = (lambda: OpenAICompatLLM(a.base_url, a.model)) if a.base_url else MockLLM
    res = {"model": a.model if a.base_url else "mock", **run(a.learners, f, a.seed)}
    Path(a.out).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
