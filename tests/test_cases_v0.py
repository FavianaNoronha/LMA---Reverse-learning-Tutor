import json, pathlib, pytest
from setu.bank import load_rules, index_items, vocab_for
from setu.checker import check, check_no_error_turn
from setu.schemas import CheckResult
from setu.ledger import apply_check
from setu.metrics import copy_rate
from setu.planner import choose_turn
import random
from setu.leakfilter import check_draft, select_classmate_sentence, errors_in
from setu.state import RajuState

RULES = load_rules(); IDX = index_items(RULES)
CASES = [json.loads(l) for l in (pathlib.Path(__file__).parent.parent / "data/l1-hi_l2-te/tests_v0.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.mark.parametrize("c", CASES, ids=[c["case_id"] for c in CASES])
def test_case(c):
    g = c["group"]
    if g == "checker":
        rule, item = IDX[c["item_id"]]
        assert check(rule, item, c["answer"]).verdict == c["expect"]
    elif g == "leak" and "draft" in c:
        rule, item = IDX[c["item_id"]]
        state = {r.rule_id: "unknown" for r in RULES}; state.update(c["rule_state"])
        d = check_draft(c["draft"], rule, item, RULES, vocab_for(RULES, c["seen_rules"]), state)
        assert d.ok == c["expect_ok"]
        assert set(c["expect_reasons"]) <= set(d.reasons)
    elif g == "leak":
        rule, item = IDX[c["item_id"]]
        state = {r.rule_id: "unknown" for r in RULES}
        t = select_classmate_sentence(c["drafts"], rule, item, RULES, vocab_for(RULES, c["seen_rules"]), state)
        assert t.source == c["expect_source"]
        if c["expect_index"] is not None:
            assert t.draft == c["drafts"][c["expect_index"]]
        else:
            assert t.draft == item.planted_error
    elif g == "planting":
        _, item = IDX[c["item_id"]]
        assert errors_in(item.planted_error, RULES) == c["expect_rules"]
    elif g == "no_error" and "draft" in c:
        rule, item = IDX[c["item_id"]]
        state = {r.rule_id: "unknown" for r in RULES}; state.update(c["rule_state"])
        d = check_draft(c["draft"], rule, item, RULES, vocab_for(RULES, c["seen_rules"]), state, no_error=True)
        assert d.ok == c["expect_ok"]
        assert set(c["expect_reasons"]) <= set(d.reasons)
    elif g == "no_error":
        rule, item = IDX[c["item_id"]]
        assert check_no_error_turn(rule, item, c["answer"]).verdict == c["expect"]
    elif g == "ledger":
        rule, item = IDX[c["item_id"]]
        s = RajuState([r.rule_id for r in RULES])
        ev = apply_check(s, "L1", rule, item, CheckResult(item_id=item.item_id, answer="x", verdict=c["verdict"], reason="test"), c["turn_type"])
        assert ev.counts_toward_mastery == c["expect_counts"]
        assert ev.classmate_state_changed == c["expect_changed"]
    elif g == "copy":
        assert copy_rate(c["productions"], set(c["planted"]), RULES) == c["expect"]
    elif g == "forgetting":
        s = RajuState([r.rule_id for r in RULES])
        for step in c["steps"]:
            if step[0] == "correct": s.learner_corrected(step[1], step[2])
            else: s.apply_forgetting(step[1])
        for k, v in c["expect"].items():
            assert s.rules[k] == v


def test_bank_consistency():
    for rid, (r, i) in IDX.items():
        assert errors_in(i.planted_error, RULES) == [r.rule_id], rid          # exactly one error, of this rule
        assert all(not any(__import__("re").search(p, a) for p in i.wrong_regex) for a in i.accepted), rid


def test_planner_no_error_only_from_taught_rules():
    s = RajuState([r.rule_id for r in RULES])
    rng = random.Random(0)
    assert all(choose_turn(s, rng)[0] == "planted" for _ in range(50))   # nothing taught yet
    s.learner_corrected("HI-TE-002", True)
    turns = [choose_turn(s, rng, p_no_error=0.2) for _ in range(1000)]
    ne = [t for t in turns if t[0] == "no_error"]
    assert all(r == "HI-TE-002" for _, r in ne)
    assert 0.12 < len(ne) / len(turns) < 0.28
