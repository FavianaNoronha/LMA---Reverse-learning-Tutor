"""Simulated learner v0 (Section 8.2). Parametric, no language model: each rule has a memory half-life and
p_recall = 2^(-days / half-life), as in the tutor's own tracker. It answers through the real Tutor, so the run
also tests the machinery (planner, Raju, checker, ledger, forgetting) end to end.

The learning rules ARE assumptions, stated here so nobody mistakes the output for evidence about people:
  * successful retrieval multiplies the half-life by RETRIEVAL_BASE + RETRIEVAL_GAIN * (1 - p)   (harder recall,
    bigger gain: the spacing/testing idea behind FSRS-style schedulers);
  * restudy (reading a corrected example) multiplies it by RESTUDY_BASE + RESTUDY_GAIN * (1 - p);
  * a failed retrieval followed by the correct form counts as a restudy; a failure with only a hint gives a
    second try with a better chance (HINT_HELP);
  * answering Raju's "why?" multiplies the half-life by EXPLAIN_GAIN (1.0 = no self-explanation effect);
  * when recall fails in a test, the learner reproduces the classmate's planted error with probability COPY_P.
Run scripts/simulate_learners.py to see how results move when these assumptions change (sensitivity grid).
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from .checker import NO_ERROR


@dataclass
class Params:
    retrieval_base: float = 1.2
    retrieval_gain: float = 3.0
    restudy_base: float = 1.1
    restudy_gain: float = 1.5
    explain_gain: float = 1.0
    hint_help: float = 0.4
    copy_p: float = 0.1
    h0: float = 1.0          # half-life (days) right after first meeting a rule


@dataclass
class SimLearner:
    params: Params
    rng: random.Random
    h: dict[str, float] = field(default_factory=dict)
    last: dict[str, float] = field(default_factory=dict)
    writer: object | None = None                    # optional LLM student: writes the answer text; the outcome is still decided here
    log: list = field(default_factory=list)

    def say(self, item, rule, ok: bool, mode: str = "fix", copied: bool = False):
        """(text, meta). mode 'fix': a miss is the planted mistake; 'intro'/'test': a miss is 'I don't know' unless copied."""
        intended = "correct" if ok else ("wrong" if (mode == "fix" or copied) else "dontknow")
        canned = item.accepted[0] if intended == "correct" else (item.planted_error if intended == "wrong" else "నాకు తెలియదు")
        if self.writer is None or intended == "dontknow":
            return canned, None
        text, style = self.writer.write(item, rule, intended, canned)
        return text, {"intended": intended, "style": style, "item": item.item_id}

    def submit(self, t, lid, item, rule, ok: bool, mode: str = "fix", copied: bool = False):
        text, meta = self.say(item, rule, ok, mode, copied)
        r = t.answer(lid, text)
        if meta:
            v = r["verdict"]
            if v == "recorded":                          # tests give no feedback; the checker's verdict is in the stored test record
                v = t.store.load(lid).tests[-1]["verdict"]
            self.log.append({**meta, "verdict": v, "text": text, "mode": mode})
        return r

    def p(self, rid: str, day: float) -> float:
        if rid not in self.h:
            return 0.0
        return 2 ** (-(day - self.last[rid]) / self.h[rid])

    def meet(self, rid: str, day: float) -> None:
        self.h[rid] = self.params.h0; self.last[rid] = day

    def _gain(self, rid: str, day: float, base: float, g: float) -> None:
        p = self.p(rid, day); self.h[rid] *= base + g * (1 - p); self.last[rid] = day

    def retrieve(self, rid: str, day: float, bonus: float = 0.0) -> bool:
        p = self.p(rid, day); ok = self.rng.random() < p + (1 - p) * bonus
        if ok:
            self._gain(rid, day, self.params.retrieval_base, self.params.retrieval_gain)
        return ok

    def restudy(self, rid: str, day: float) -> None:
        if rid not in self.h:
            self.meet(rid, day)
        self._gain(rid, day, self.params.restudy_base, self.params.restudy_gain)

    def explain(self, rid: str, day: float) -> None:
        if rid in self.h:
            self.h[rid] *= self.params.explain_gain


def answer_raju(sim: SimLearner, t, lid: str, out: dict) -> None:
    """Answer one Raju turn (and a follow-up 'why?') through the tutor."""
    l = t.store.load(lid); p = l.pending; day = l.clock_offset_days
    rule, item = t.items[p["item_id"]]; rid = rule.rule_id
    if p["turn_type"] == "no_error":
        knows = sim.retrieve(rid, day)
        r = t.answer(lid, NO_ERROR if knows or sim.rng.random() < 0.5 else item.planted_error)
    else:
        ok = sim.retrieve(rid, day)
        r = sim.submit(t, lid, item, rule, ok)
        if r["verdict"] == "wrong" and t.store.load(lid).pending:          # hint, second try
            ok = sim.retrieve(rid, day, bonus=sim.params.hint_help)
            r = sim.submit(t, lid, item, rule, ok)
    if r.get("why_question"):
        sim.explain(rid, day); t.answer(lid, "క్యోంకి తెలుగులో ఇక్కడ ఇలాగే చెబుతారు")
    out["raju_changed_without_correct"] += 0                                # counted from the ledger below


def run_learner(t, lid: str, params: Params, seed: int, rule_ids: list[str], sessions=(0, 1, 2),
                exposures_per_session: int = 6, delay_days: int = 7, writer=None) -> dict:
    rng = random.Random(seed); sim = SimLearner(params, rng, writer=writer); out = {"raju_changed_without_correct": 0}
    t.assign_conditions(lid, rule_ids)
    l = t.store.load(lid); cond = dict(l.conditions)

    def test(phase: str, transfer: bool = False):
        for rid in rule_ids:
            rule = t.by_id[rid]
            item = rule.items[-1] if transfer and len(rule.items) > 1 else rule.items[0]
            day = t.store.load(lid).clock_offset_days
            ok = sim.rng.random() < sim.p(rid, day)                         # tests: recall without changing memory
            copied = (not ok) and phase != "pre" and cond[rid] in "AB" and sim.rng.random() < params.copy_p
            t.test_item(lid, phase, rid, item.item_id)
            sim.submit(t, lid, item, rule, ok, "test", copied)

    test("pre")
    for c in "ABC":                                                          # meet every rule (same explanation in all conditions)
        while (r := t.intro(lid, c)) is not None:
            rid = r["rule_id"]; day = t.store.load(lid).clock_offset_days; sim.meet(rid, day)
            rule = t.by_id[rid]
            for _ in range(3):
                if t.store.load(lid).pending is None:
                    break
                ok = sim.retrieve(rid, day, bonus=0.5)
                sim.submit(t, lid, rule.items[-1], rule, ok, "intro")
                if not ok:
                    sim.restudy(rid, day)
            l = t.store.load(lid); l.pending = None; t.store.save(l)
            if c == "A" and not t.store.load(lid).rules[rid].ready_for_raju:   # learner must get it right once
                l = t.store.load(lid); l.rules[rid].ready_for_raju = True; l.raju.setdefault(rid, "unknown"); t.store.save(l)
    prev = 0
    for s in sessions:
        if s > prev:
            t.skip_days(lid, s - prev); prev = s
        for _ in range(exposures_per_session):                              # matched practice count per condition
            r = t.turn(lid)
            if r["kind"] == "raju":
                answer_raju(sim, t, lid, out)
            ex = t.example(lid)
            if ex:
                sim.restudy(ex["rule_id"], t.store.load(lid).clock_offset_days)
            pr = t.prompt(lid)
            if pr:
                rid = pr["rule_id"]; day = t.store.load(lid).clock_offset_days
                item = t.items[t.store.load(lid).pending["item_id"]][1]
                ok = sim.retrieve(rid, day); prule = t.by_id[rid]
                res = sim.submit(t, lid, item, prule, ok)
                if res["verdict"] == "wrong" and t.store.load(lid).pending:     # hint, second try (as in A)
                    ok = sim.retrieve(rid, day, bonus=sim.params.hint_help)
                    res = sim.submit(t, lid, item, prule, ok)
                if res["verdict"] != "correct":
                    sim.restudy(rid, day)                                    # the tutor shows the correct form
    test("post"); t.skip_days(lid, delay_days); test("delayed"); test("transfer", transfer=True)
    l = t.store.load(lid)
    out["raju_changed_without_correct"] = sum(1 for e in l.events if e.classmate_state_changed and e.verdict != "correct")
    out["results"] = t.results(lid)
    out["copies"] = sum(1 for x in l.tests if x["phase"] in ("delayed", "transfer") and x["answer"] == t.items[x["item"]][1].planted_error)
    if writer is not None:
        out["student_log"] = sim.log        # every LLM-written answer: intended outcome, style, the checker's verdict
    return out
