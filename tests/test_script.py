"""Script bridge: Devanagari <-> Telugu, and Devanagari typing accepted everywhere with the same rules."""
from setu.bank import load_rules
from setu.llm import MockLLM
from setu.memory import Store
from setu.script import deva_to_telugu, telugu_to_deva, fold_vowel_length, final_m_variant, DIFFERENCES
from setu.session import Tutor


def test_round_trip_every_accepted_form_in_the_bank():
    for r in load_rules():
        for i in r.items:
            for a in i.accepted + [i.planted_error]:
                assert deva_to_telugu(telugu_to_deva(a)) == a, a


def test_hindi_typing_habits():
    assert final_m_variant(deva_to_telugu("इदि पुस्तकम")) == "ఇది పుస్తకం"   # final म -> ం
    assert final_m_variant("నేను అమ్మ") == "నేను అమ్మ"                      # not after a virama
    assert deva_to_telugu("इदि पुस्तकं") == "ఇది పుస్తకం"
    assert telugu_to_deva("ఎవరు") == "ऎवरु" and telugu_to_deva("పళ్ళు") == "पळ्ळु"
    assert fold_vowel_length("వెళ్తున్నాం") == fold_vowel_length("వేళ్తున్నాం")
    assert len(DIFFERENCES) == 6


def test_devanagari_answers_work_in_the_tutor_and_count_as_aid_use(tmp_path):
    t = Tutor(Store(tmp_path), MockLLM(), seed=1, p_no_error=0.0)
    r = t.intro("a"); rule = t.by_id[r["rule_id"]]
    assert r["reading_right"] == telugu_to_deva(r["example_right"])
    assert t.answer("a", telugu_to_deva(rule.items[-1].accepted[0]))["verdict"] == "correct"
    out = t.turn("a"); assert out["reading"] == telugu_to_deva(out["sentence"])
    item = t.items[t.store.load("a").pending["item_id"]][1]
    assert t.answer("a", telugu_to_deva(item.accepted[0]))["raju_state"] == "taught"
    assert t.store.load("a").script_inputs == 2


def test_long_e_typed_for_short_e_is_forgiven_only_for_devanagari_input(tmp_path):
    t = Tutor(Store(tmp_path), MockLLM(), seed=1, p_no_error=0.0)
    item = next(i for r in t.rules for i in r.items if any(c in i.accepted[0] for c in "ఎఒెొ"))
    rule = t.items[item.item_id][0]
    long_deva = telugu_to_deva(item.accepted[0]).replace("ॆ", "े").replace("ॊ", "ो").replace("ऎ", "ए").replace("ऒ", "ओ")
    res = t._check(rule, item, deva_to_telugu(long_deva), typed_deva=True)
    assert res.verdict == "correct" and "short" in res.reason
    assert t._check(rule, item, fold_vowel_length(item.accepted[0]), typed_deva=False).verdict != "correct"


def test_why_explanations_in_hindi_are_not_converted(tmp_path):
    t = Tutor(Store(tmp_path), MockLLM(), seed=1, p_no_error=0.0)
    ids = []
    for _ in range(3):
        r = t.intro("a"); t.answer("a", t.by_id[r["rule_id"]].items[-1].accepted[0])
    for _ in range(3):
        t.turn("a"); p = t.store.load("a").pending; out = t.answer("a", t.items[p["item_id"]][1].accepted[0])
    assert "why_question" in out
    t.answer("a", "क्योंकि हिंदी में है आता है")
    q = (tmp_path / "teacher_queue.jsonl").read_text(encoding="utf-8")
    assert "क्योंकि" in q
