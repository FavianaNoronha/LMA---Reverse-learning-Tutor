"""Minimal web app over the same Tutor. Run:
  pip install fastapi uvicorn
  SETU_LLM=demo SETU_DEMO=1 uvicorn app.server:app --reload       # guided demo (shows leaky drafts being rejected)
  SETU_LLM=mock uvicorn app.server:app --reload            # or SETU_LLM=http://localhost:11434/v1 SETU_MODEL=gemma3:12b
then open http://127.0.0.1:8000
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from setu.llm import AgentMockLLM, DemoLLM, MockLLM, OpenAICompatLLM
from setu.memory import Store
from setu.session import Tutor, NO_ERROR

_llm_env = os.environ.get("SETU_LLM", "mock")
llm = None if _llm_env == "none" else MockLLM() if _llm_env == "mock" else AgentMockLLM(leaky_every=3) if _llm_env == "demo" else OpenAICompatLLM(_llm_env, os.environ.get("SETU_MODEL", "gemma3:12b"))
tutor = Tutor(Store(os.environ.get("SETU_STORE", "runs")), llm, demo=os.environ.get("SETU_DEMO", "0") == "1",
              agent=os.environ.get("SETU_AGENT", "1") == "1")      # Raju as a tool-using agent by default
app = FastAPI(title="SETU tutor")


class L(BaseModel):
    learner_id: str


class A(L):
    text: str = ""
    no_error: bool = False


class S(L):
    days: float = 3


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.post("/api/intro")
def intro(b: L):
    return tutor.intro(b.learner_id) or {"done": True}


@app.post("/api/turn")
def turn(b: L):
    return tutor.turn(b.learner_id)


@app.post("/api/answer")
def answer(b: A):
    return tutor.answer(b.learner_id, NO_ERROR if b.no_error else b.text)


@app.post("/api/skip")
def skip(b: S):
    tutor.skip_days(b.learner_id, b.days); return tutor.status(b.learner_id)


@app.post("/api/status")
def status(b: L):
    return tutor.status(b.learner_id)


@app.post("/api/inside")
def inside(b: L):
    return tutor.inside(b.learner_id)


@app.post("/api/reset")
def reset(b: L):
    from setu.memory import Learner
    tutor.store.save(Learner(learner_id=b.learner_id)); return {"ok": True}


# ---- study mode (conditions A/B/C and tests) ----
class P(L):
    phase: str = "pre"
    rule_id: str
    item_id: str | None = None


class C(L):
    condition: str | None = None


@app.post("/api/study/assign")
def study_assign(b: L):
    return tutor.assign_conditions(b.learner_id)


@app.post("/api/study/intro")
def study_intro(b: C):
    return tutor.intro(b.learner_id, b.condition) or {"done": True}


@app.post("/api/study/example")
def study_example(b: L):
    return tutor.example(b.learner_id) or {"done": True}


@app.post("/api/study/prompt")
def study_prompt(b: L):
    return tutor.prompt(b.learner_id) or {"done": True}


@app.post("/api/study/test")
def study_test(b: P):
    return tutor.test_item(b.learner_id, b.phase, b.rule_id, b.item_id)


@app.post("/api/study/results")
def study_results(b: L):
    return {"conditions": tutor.store.load(b.learner_id).conditions, "results": tutor.results(b.learner_id)}
