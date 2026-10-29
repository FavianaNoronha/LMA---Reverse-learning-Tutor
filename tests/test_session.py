import json
from setu.llm import MockLLM, parse_sentence
from setu.memory import Store
from setu.session import Tutor, NO_ERROR


def tutor(tmp_path, llm=None, p_no_error=0.0, seed=1):
    return Tutor(Store(tmp_path), llm if llm is not None else MockLLM(), seed=seed, p_no_error=p_no_error)


def learn_first_rule(t, lid="a"):
    r = t.intro(lid)
    rule = t.by_id[r["rule_id"]]
    out = t.answer(lid, rule.items[-1].accepted[0])
    assert out["verdict"] == "correct"
    return rule


def test_raju_waits_until_learner_has_got_a_rule_right(tmp_path):
    t = tutor(tmp_path)
    assert t.turn("a")["kind"] == "need_intro"
    r = t.intro("a")
    assert t.turn("a")["kind"] == "need_intro"           # introduced but not yet answered correctly
    t.answer("a", "నాకు తెలియదు")                         # unsure -> still not ready
    assert t.turn("a")["kind"] == "need_intro"


def test_full_loop_teach_forget_reteach(tmp_path):
    t = tutor(tmp_path)
    rule = learn_first_rule(t)
    turn = t.turn("a")
    assert turn["kind"] == "raju" and turn["source"] == "llm"
    assert t.llm.calls == 1                               # stops at the first draft that passes
    item = t.items[t.store.load("a").pending["item_id"]][1]
    assert turn["sentence"] == item.planted_error
    out = t.answer("a", item.accepted[0])
    assert out["verdict"] == "correct" and out["raju_state"] == "taught"
    t.skip_days("a", 30)                                  # learner's recall drops below 0.5
    t.turn("a")
    assert t.store.load("a").raju[rule.rule_id] == "forgotten"
    item = t.items[t.store.load("a").pending["item_id"]][1]
    assert t.answer("a", item.accepted[0])["raju_state"] == "taught"


def test_wrong_and_unsure_do_not_teach_raju(tmp_path):
    t = tutor(tmp_path)
    rule = learn_first_rule(t)
    t.turn("a")
    item = t.items[t.store.load("a").pending["item_id"]][1]
    assert t.answer("a", item.planted_error)["verdict"] == "wrong"     # left the mistake in
    assert t.store.load("a").raju[rule.rule_id] == "unknown"
    t.turn("a")
    before = t.store.load("a").rules[rule.rule_id].model_dump()
    assert t.answer("a", "నాకు తెలియదు")["verdict"] == "unsure"
    l = t.store.load("a")
    assert l.raju[rule.rule_id] == "unknown"
    assert l.rules[rule.rule_id].model_dump() == before                # unsure changes no mastery
    assert (tmp_path / "teacher_queue.jsonl").exists()


def test_leaky_model_falls_back_to_bank(tmp_path):
    leaky = MockLLM(lambda m: json.dumps({"sentence": "ఇది పుస్తకం ఎందుకంటే నియమం"}, ensure_ascii=False))
    t = tutor(tmp_path, llm=leaky)
    learn_first_rule(t)
    turn = t.turn("a")
    item = t.items[t.store.load("a").pending["item_id"]][1]
    assert turn["source"] == "bank" and turn["rejected_drafts"] == 3
    assert turn["sentence"] == item.planted_error
    assert leaky.calls == 3


def test_no_error_turns_after_teaching(tmp_path):
    t = tutor(tmp_path, p_no_error=1.0)
    rule = learn_first_rule(t)
    t.turn("a")                                           # nothing taught yet -> planted
    item = t.items[t.store.load("a").pending["item_id"]][1]
    t.answer("a", item.accepted[0])
    turn = t.turn("a")                                    # now Raju knows it -> correct sentence
    p = t.store.load("a").pending
    assert p["turn_type"] == "no_error"
    assert turn["sentence"] in t.items[p["item_id"]][1].accepted
    out = t.answer("a", NO_ERROR)
    assert out["verdict"] == "correct" and out["raju_state"] == "taught"


def test_parse_sentence_handles_messy_output():
    assert parse_sentence('{"sentence": "ఇది పుస్తకం"}') == "ఇది పుస్తకం"
    assert parse_sentence('Sure!\n{"sentence": "ఇది పుస్తకం"}') == "ఇది పుస్తకం"
    assert parse_sentence('ఇది పుస్తకం\nexplanation...') == "ఇది పుస్తకం"


def test_web_api_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("SETU_STORE", str(tmp_path)); monkeypatch.setenv("SETU_LLM", "mock")
    import importlib, app.server as srv
    importlib.reload(srv)
    from fastapi.testclient import TestClient
    c = TestClient(srv.app)
    assert c.get("/").status_code == 200
    r = c.post("/api/intro", json={"learner_id": "w"}).json()
    rule = srv.tutor.by_id[r["rule_id"]]
    assert c.post("/api/answer", json={"learner_id": "w", "text": rule.items[-1].accepted[0]}).json()["verdict"] == "correct"
    assert c.post("/api/turn", json={"learner_id": "w"}).json()["kind"] == "raju"
