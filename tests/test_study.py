"""Study conditions: A teach Raju, B matched error examples, C normal tutor; cue-free tests without feedback."""
from setu.llm import MockLLM
from setu.memory import Store
from setu.session import Tutor


def T(tmp_path):
    return Tutor(Store(tmp_path), MockLLM(), seed=1, p_no_error=0.0)


def test_latin_square_rotates_by_learner(tmp_path):
    t = T(tmp_path)
    a = t.assign_conditions("aa"); b = t.assign_conditions("ab")
    assert set(a.values()) == {"A", "B", "C"} and a != b
    assert sorted(a.values()).count("A") >= 4


def test_only_condition_A_rules_reach_raju(tmp_path):
    t = T(tmp_path); t.assign_conditions("x")
    for cond in "ABC":
        r = t.intro("x", cond); rule = t.by_id[r["rule_id"]]
        assert t.store.load("x").conditions[rule.rule_id] == cond
        t.answer("x", rule.items[-1].accepted[0])
    l = t.store.load("x")
    ready = [rid for rid, m in l.rules.items() if m.ready_for_raju]
    assert len(ready) == 1 and l.conditions[ready[0]] == "A"
    assert t.turn("x")["kind"] == "raju" and t.store.load("x").pending["rule_id"] == ready[0]


def test_condition_B_example_and_C_tutor(tmp_path):
    t = T(tmp_path); t.assign_conditions("x")
    for cond in "BC":
        r = t.intro("x", cond); t.answer("x", t.by_id[r["rule_id"]].items[-1].accepted[0])
    ex = t.example("x")
    assert ex["wrong"] != ex["right"] and ex["why"]
    pr = t.prompt("x"); p = t.store.load("x").pending
    item = t.items[p["item_id"]][1]
    assert t.answer("x", item.planted_error)["verdict"] == "wrong"           # normal tutor corrects the learner
    t.prompt("x"); p = t.store.load("x").pending
    assert t.answer("x", t.items[p["item_id"]][1].accepted[0])["verdict"] == "correct"
    assert all(v == "unknown" for v in t.store.load("x").raju.values())     # B and C never touch Raju


def test_tests_give_no_feedback_and_change_no_memory(tmp_path):
    t = T(tmp_path); t.assign_conditions("x")
    r = t.intro("x", "A"); rule = t.by_id[r["rule_id"]]; t.answer("x", rule.items[-1].accepted[0])
    before = t.store.load("x").rules[rule.rule_id].model_dump()
    t.test_item("x", "delayed", rule.rule_id)
    out = t.answer("x", rule.items[0].accepted[0])
    assert out["verdict"] == "recorded" and "correct" not in out["message"].lower()
    assert t.store.load("x").rules[rule.rule_id].model_dump() == before
    res = t.results("x")
    assert res["delayed"]["A"] == {"correct": 1, "n": 1, "unsure": 0}


def test_simulated_learners_run_end_to_end_and_never_teach_raju_unchecked():
    import importlib.util
    from pathlib import Path
    from setu.llm import AgentMockLLM
    spec = importlib.util.spec_from_file_location("sl", Path(__file__).resolve().parent.parent / "scripts" / "simulate_learners.py")
    sl = importlib.util.module_from_spec(spec); spec.loader.exec_module(sl)
    from setu.simlearner import Params
    r = sl.run(Params(), 3, lambda: AgentMockLLM(leaky_every=3), seed=5)
    assert r["raju_learned_from_unchecked_answers"] == 0
    assert set(r["by_phase"]["delayed"]) == {"A", "B", "C"}
    assert all(r["by_phase"]["pre"][c]["mean"] == 0.0 for c in "ABC")
