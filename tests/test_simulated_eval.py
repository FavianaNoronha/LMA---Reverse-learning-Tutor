import importlib.util, json
from pathlib import Path
from setu.llm import MockLLM

spec = importlib.util.spec_from_file_location("simulated_eval", Path(__file__).resolve().parent.parent / "scripts" / "simulated_eval.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)


def test_simulated_eval_with_well_behaved_model():
    r = ev.run(6, MockLLM, seed=3, turns=12)
    assert r["selective_flip_score"] == 1.0 and r["controllability_mean"] == 1.0 and r["rmse_mean"] == 0.0
    assert r["guidance_responsiveness"] == 1.0


def test_simulated_eval_with_a_model_that_knows_too_much_is_still_controlled():
    # the "competence paradox" case: the model always writes the correct sentence, never the planted mistake
    knows_all = lambda: MockLLM(lambda m: json.dumps({"sentence": "ఇది పుస్తకం"}, ensure_ascii=False))
    r = ev.run(6, knows_all, seed=3, turns=12)
    assert r["bank_fallback_rate"] > 0.5                       # the filter rejects it, the bank steps in
    assert r["controllability_mean"] == 1.0 and r["rmse_mean"] == 0.0
