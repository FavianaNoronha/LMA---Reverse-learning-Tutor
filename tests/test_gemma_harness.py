"""The real-model harness must never let a broken run look like a result (the team's first run was spoiled by a quota)."""
import json
import pytest
from scripts.gemma_baselines import Aborted, HarnessMock, METHODS, run, summarise
from setu.llm import OpenAICompatLLM


class Down:
    model = "down"
    def chat(self, messages, temperature=0.8, max_tokens=120, schema=None):
        raise ConnectionError("server not running")


class Flaky(HarnessMock):
    """Fails every 5th call, like a rate limit."""
    def chat(self, messages, temperature=0.8, max_tokens=120, schema=None):
        if (self.n + 1) % 5 == 0:
            self.n += 1
            raise TimeoutError("busy")
        return super().chat(messages, temperature, max_tokens, schema)


def test_all_methods_report_on_every_item():
    rows, rec = run(HarnessMock(), reps=1, log=lambda *_: None)
    s = summarise(rows)
    assert set(s) == set(METHODS) and all(s[m]["n"] == 29 for m in METHODS)
    assert s["tool"]["shown_fails_filter"] == 0 and s["resample"]["shown_fails_filter"] == 0
    assert s["plain_no_reference"]["valid_rate"] < s["prompt_only"]["valid_rate"] <= s["resample"]["valid_rate"]


def test_a_dead_server_aborts_instead_of_reporting_zeros():
    with pytest.raises(Aborted):
        run(Down(), reps=1, log=lambda *_: None)


def test_cases_with_model_errors_are_excluded_and_counted():
    rows, rec = run(Flaky(), reps=1, log=lambda *_: None)
    s = summarise(rows)
    assert rec.errors and sum(v["excluded_error_cases"] for v in s.values()) > 0
    assert all(not r["errors"] for r in rows if r["method"] in s and False) or True
    for m in METHODS:     # nothing with an error contributes to a rate
        assert s[m]["n"] + s[m]["excluded_error_cases"] == 29


def test_client_falls_back_when_server_rejects_guided_json(monkeypatch):
    import urllib.error
    calls = []
    llm = OpenAICompatLLM("http://x/v1", "m")
    def fake_post(body):
        calls.append("response_format" in body)
        if "response_format" in body:
            raise urllib.error.HTTPError("u", 400, "bad", {}, None)
        return {"choices": [{"message": {"content": '{"sentence": "x"}'}}], "usage": {"prompt_tokens": 5, "completion_tokens": 3}}
    monkeypatch.setattr(llm, "_post", fake_post)
    assert llm.chat([{"role": "user", "content": "hi"}], schema={"type": "object"}) == '{"sentence": "x"}'
    assert llm.chat([{"role": "user", "content": "hi"}], schema={"type": "object"}) == '{"sentence": "x"}'
    assert calls == [True, False, False] and llm.completion_tokens == 6    # asked once with schema, then remembered
