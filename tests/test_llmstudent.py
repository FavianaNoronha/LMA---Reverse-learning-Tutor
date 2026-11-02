"""AI student simulator: the LLM writes typing, the parametric learner decides the outcome, the real checker marks it."""
import random, tempfile
from scripts.simulate_students import controlled, free
from setu.llm import AgentMockLLM
from setu.llmstudent import LLMStudent, StudentMock, pick_style
from setu.memory import Store
from setu.session import Tutor
from setu.simlearner import Params, run_learner


class Broken:
    model = "broken"
    def chat(self, *a, **k):
        raise ConnectionError("down")


def test_without_a_writer_the_parametric_learner_is_unchanged():
    def go():
        with tempfile.TemporaryDirectory() as d:
            t = Tutor(Store(d), AgentMockLLM(), seed=3, p_no_error=0.2, agent=True)
            return run_learner(t, "x", Params(), 3, [r.rule_id for r in t.rules][:4])["results"]
    assert go() == go()


def test_styles_are_chosen_by_the_harness_and_cover_every_style():
    rng = random.Random(0)
    seen = {pick_style(rng, "correct")[0] for _ in range(200)} | {pick_style(rng, "wrong")[0] for _ in range(200)}
    assert seen == {"exact", "slip", "devanagari", "extra_word", "same_words", "reworded"}


def test_outcome_is_decided_by_the_harness_not_the_model():
    res = controlled(2, lambda: AgentMockLLM(), lambda: StudentMock(), seed=5, n_rules=5)
    assert res["intended_wrong_marked_wrong"] == 1.0           # a wrong attempt never becomes a correct verdict
    st = res["checker_on_llm_written_answers"]
    assert st["correct / exact"]["correct"] == 1.0 and st["correct / devanagari"]["correct"] == 1.0   # script bridge works on written answers
    assert st["correct / extra_word"]["correct"] == 0.0       # tag particle is never accepted


def test_a_failing_model_falls_back_and_is_counted():
    s = LLMStudent(Broken(), random.Random(1))
    from setu.bank import load_rules
    r = load_rules()[0]; text, style = s.write(r.items[0], r, "correct", r.items[0].accepted[0])
    assert text == r.items[0].accepted[0] and style.endswith("(fallback)") and s.failures == 1


def test_free_probe_runs_and_reports_rates():
    out = free(StudentMock(), 1)
    assert out["n"] == 29 and 0 <= out["rate_correct_on_unmet_rule"] <= 1
