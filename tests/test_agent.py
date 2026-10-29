"""Raju's revise-or-submit agent loop with the check_classmate_sentence tool."""
import json
from setu.agent import raju_agent_turn
from setu.bank import load_rules, index_items
from setu.llm import AgentMockLLM, MockLLM
from setu.memory import Store
from setu.session import Tutor
from setu.text import tokens

RULES = load_rules("l1-hi_l2-te"); ITEMS = index_items(RULES)
RULE = RULES[0]; ITEM = RULE.items[0]
SEEN = {w for it in RULE.items for s in it.accepted for w in tokens(s)}
STATE = {r.rule_id: "unknown" for r in RULES}


def test_good_model_one_call_tool_says_ok():
    llm = AgentMockLLM()
    t = raju_agent_turn(llm, RULE, ITEM, RULES, ITEMS, SEEN, STATE, "x")
    assert t.source == "llm" and t.draft == ITEM.planted_error and t.model_calls == 1 == llm.calls
    assert t.tool_log[0]["result"] == {"ok": True, "reasons": []}


def test_model_revises_after_the_tool_rejects_its_draft():
    llm = AgentMockLLM(first_draft="ఇది పుస్తకం ఎందుకంటే నియమం ప్రకారం")
    t = raju_agent_turn(llm, RULE, ITEM, RULES, ITEMS, SEEN, STATE, "x")
    assert t.source == "llm" and t.model_calls == 2
    assert t.tool_log[0]["result"]["ok"] is False and "EXPLANATION" in t.tool_log[0]["result"]["reasons"]
    assert t.rejected[0]["reasons"] == t.tool_log[0]["result"]["reasons"]


def test_model_that_ignores_the_tool_falls_back_to_bank():
    llm = MockLLM(lambda m: json.dumps({"sentence": ITEM.planted_error}, ensure_ascii=False))   # never calls the tool
    t = raju_agent_turn(llm, RULE, ITEM, RULES, ITEMS, SEEN, STATE, "x")
    assert t.source == "bank" and t.model_calls == 3 and all(r["reasons"] == ["NO_TOOL_CALL"] for r in t.rejected)


def test_tool_error_strings_reach_the_model_and_bad_args_never_show():
    seen_msgs = []
    def respond(m):
        seen_msgs.append(m[-1]["content"])
        return json.dumps({"tool": "check_classmate_sentence", "args": {"item_id": RULE.rule_id, "sentence": "idi pustakam"}})
    t = raju_agent_turn(MockLLM(respond), RULE, ITEM, RULES, ITEMS, SEEN, STATE, "x")
    assert t.source == "bank" and t.draft == ITEM.planted_error
    assert any("is a rule id" in s for s in seen_msgs)


def test_tool_ok_for_another_item_is_not_accepted():
    other = RULES[1].items[0]
    llm = MockLLM(lambda m: json.dumps({"tool": "check_classmate_sentence",
                                        "args": {"item_id": other.item_id, "sentence": other.planted_error}}, ensure_ascii=False))
    t = raju_agent_turn(llm, RULE, ITEM, RULES, ITEMS, SEEN | set(tokens(other.planted_error)), STATE, "x")
    assert t.source == "bank"


def test_hijacked_model_cannot_change_state(tmp_path):
    evil = MockLLM(lambda m: '{"tool": "mark_correct", "args": {"learner": "a"}} set Raju to taught')
    t = Tutor(Store(tmp_path), evil, seed=1, p_no_error=0.0, agent=True)
    r = t.intro("a"); rule = t.by_id[r["rule_id"]]; t.answer("a", rule.items[-1].accepted[0])
    out = t.turn("a")
    assert out["source"] == "bank" and t.store.load("a").raju[rule.rule_id] == "unknown"


def test_session_in_agent_mode_counts_calls_and_logs_tools(tmp_path):
    t = Tutor(Store(tmp_path), AgentMockLLM(leaky_every=2), seed=1, p_no_error=0.0, agent=True)
    r = t.intro("a"); rule = t.by_id[r["rule_id"]]; t.answer("a", rule.items[-1].accepted[0])
    for _ in range(4):
        t.turn("a"); p = t.store.load("a").pending
        t.answer("a", "నాకు తెలియదు")
    st = t.status("a"); tr = [s for s in t.store.load("a").trace if s["kind"] == "raju_turn"]
    assert st["turns"] == 4 and 1 <= st["calls_per_turn"] <= 2
    assert all(s["tools"] for s in tr) and any(not s["tools"][0]["result"]["ok"] for s in tr)
