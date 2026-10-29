"""Learner record, stored as one JSON file per learner (Postgres later).
Recall model v0: each rule has a half-life that doubles after a correct answer and halves after a wrong one;
p_recall = 2^(-days since last practice / half-life). Placeholder for the Kalman tracker / FSRS in the paper."""
from __future__ import annotations
import json, time
from pathlib import Path
from pydantic import BaseModel, Field
from .schemas import MasteryEvent


class RuleMemory(BaseModel):
    introduced: bool = False
    ready_for_raju: bool = False      # learner was taught it AND got it right once
    correct: int = 0
    wrong: int = 0
    last_practised: float | None = None
    half_life_days: float = 1.0

    def p_recall(self, now: float) -> float:
        if self.last_practised is None:
            return 0.0
        days = (now - self.last_practised) / 86400
        return 2 ** (-days / self.half_life_days)

    def update(self, verdict: str, now: float, recognition: bool = False) -> None:
        """recognition=True: the learner only judged a correct sentence ("no mistake"). That is weaker evidence than
        producing the fix, so it grows the half-life by 1.2x instead of 2x (found with the simulated learners: with
        2x, no-mistake turns kept recall high, Raju almost never forgot, and 83% of teach-Raju turns had no error)."""
        if verdict == "unsure":          # never counts
            return
        if verdict == "correct":
            self.correct += 1; self.half_life_days *= 1.2 if recognition else 2
        else:
            self.wrong += 1; self.half_life_days = max(0.5, self.half_life_days / 2)
        self.last_practised = now


class Learner(BaseModel):
    learner_id: str
    pair: str = "l1-hi_l2-te"
    seen_words: set[str] = Field(default_factory=set)
    rules: dict[str, RuleMemory] = Field(default_factory=dict)
    raju: dict[str, str] = Field(default_factory=dict)       # rule_id -> unknown / taught / forgotten
    raju_progress: dict[str, int] = Field(default_factory=dict)  # correct fixes so far towards 'taught'
    pending: dict | None = None                               # the open question, if any
    events: list[MasteryEvent] = Field(default_factory=list)
    model_calls: int = 0                                      # total LLM calls for this learner (intake Q2)
    turns: int = 0
    fixes: int = 0                                            # checked-correct fixes on planted turns (drives the 'why?' question)
    conditions: dict[str, str] = Field(default_factory=dict)    # study: rule_id -> A (teach Raju) / B (matched examples) / C (normal tutor)
    tests: list[dict] = Field(default_factory=list)            # study: pre / post / delayed / transfer test answers (no feedback)
    exposures: dict[str, int] = Field(default_factory=dict)    # study: practice exposures per rule (for matching conditions)
    trace: list[dict] = Field(default_factory=list)           # last internal steps, for the demo's 'inside' view
    clock_offset_days: float = 0.0                            # demo/testing: "skip days"


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root); (self.root / "learners").mkdir(parents=True, exist_ok=True)

    def _p(self, lid: str) -> Path:
        safe = "".join(c for c in lid if c.isalnum() or c in "-_")[:64] or "anon"
        return self.root / "learners" / f"{safe}.json"

    def load(self, lid: str) -> Learner:
        p = self._p(lid)
        return Learner.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else Learner(learner_id=lid)

    def save(self, l: Learner) -> None:
        self._p(l.learner_id).write_text(l.model_dump_json(indent=1), encoding="utf-8")

    def teacher_queue(self, lid: str, n: int = 8) -> list[dict]:
        p = self.root / "teacher_queue.jsonl"
        if not p.exists():
            return []
        rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        return [r for r in rows if r.get("learner") == lid][-n:]

    def queue_for_teacher(self, entry: dict) -> None:
        with open(self.root / "teacher_queue.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({**entry, "t": time.time()}, ensure_ascii=False) + "\n")
