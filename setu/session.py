"""The tutor loop. One place that ties planner -> Raju -> learner -> checker -> ledger -> memory together.

Flow for a learner:
  1. intro(): learn a new rule (explanation + example), then answer one check item yourself.
  2. Once you got that check item right, the rule is "ready": Raju may now make that mistake.
  3. turn(): Raju shows a sentence (one planted mistake, or ~20% of the time none).
  4. answer(): the checker marks the fix; only a checked correct fix teaches Raju; unsure goes to the teacher.
  5. When your recall of a rule drops below 0.5, Raju forgets it too and makes the mistake again.
"""
from __future__ import annotations
import random, time
from .bank import load_rules, index_items
from .checker import check, check_no_error_turn, NO_ERROR
from .agent import raju_agent_turn
from .classmate import raju_turn, RAJU_ASK, RAJU_THANKS, RAJU_WHY
from .coach import hint
from .ledger import apply_check
from .llm import LLM
from .memory import Learner, RuleMemory, Store
from .planner import choose_turn
from .schemas import Rule
from .state import RajuState
from .text import tokens

FORGET_THRESHOLD = 0.5
WHY_EVERY = 3        # Raju asks 'why?' after every 3rd checked fix (mode-shifting idea from AlgoBo, arXiv 2309.14534)


class Tutor:
    def __init__(self, store: Store, llm: LLM | None = None, pair: str = "l1-hi_l2-te",
                 seed: int | None = None, p_no_error: float = 0.2, demo: bool = False, agent: bool = False,
                 forget_threshold: float = FORGET_THRESHOLD, teach_needed: int = 1):
        self.rules: list[Rule] = load_rules(pair)
        self.by_id = {r.rule_id: r for r in self.rules}
        self.items = index_items(self.rules)
        self.store, self.llm, self.pair, self.p_no_error = store, llm, pair, p_no_error
        self.rng = random.Random(seed)
        self.teach_needed = teach_needed            # Raju must be taught a rule on this many sentences before he knows it
        self.forget_threshold = forget_threshold   # Raju forgets a rule when the learner's recall drops below this
        self.agent = agent        # True: Raju runs as a tool-using agent (setu/agent.py)
        self.demo = demo          # demo only: also return the accepted answer so a scripted walk-through can play itself

    # ---------- helpers ----------
    def _log(self, l: Learner, kind: str, **data) -> None:
        l.trace.append({"kind": kind, "day": round(l.clock_offset_days, 1), **data}); del l.trace[:-14]

    def now(self, l: Learner) -> float:
        return time.time() + l.clock_offset_days * 86400

    def _mem(self, l: Learner, rid: str) -> RuleMemory:
        return l.rules.setdefault(rid, RuleMemory())

    def _raju(self, l: Learner) -> RajuState:
        ready = [rid for rid, m in l.rules.items() if m.ready_for_raju]
        s = RajuState(ready, self.teach_needed, l.raju_progress)
        for rid in ready:
            s.rules[rid] = l.raju.get(rid, "unknown")
        return s

    def _save_raju(self, l: Learner, s: RajuState) -> None:
        l.raju.update(s.rules); l.raju_progress.update(s.progress)

    # ---------- 1. learn a new rule ----------
    def intro(self, lid: str, condition: str | None = None) -> dict | None:
        """Learn the next rule. In a study, `condition` picks the next rule assigned to that condition."""
        l = self.store.load(lid)
        pool = [r for r in self.rules if condition is None or l.conditions.get(r.rule_id) == condition]
        nxt = next((r for r in pool if not self._mem(l, r.rule_id).introduced), None)
        if nxt is None:
            return None
        m = self._mem(l, nxt.rule_id); m.introduced = True
        for it in nxt.items:                                   # the learner now "has seen" these words
            for s in it.accepted:
                l.seen_words.update(tokens(s))
        check_item = nxt.items[-1]
        l.pending = {"kind": "intro_check", "rule_id": nxt.rule_id, "item_id": check_item.item_id, "attempt": 0}
        self.store.save(l)
        ex = nxt.items[0]
        self._log(l, "intro", rule=nxt.rule_id, title=nxt.name)
        self.store.save(l)
        out = {"rule_id": nxt.rule_id, "title": nxt.name, "why": nxt.l1_habit,
                "example_wrong": ex.planted_error, "example_right": ex.accepted[0],
                "task": f"Say in Telugu: {check_item.english}", "hindi": check_item.hindi}
        if self.demo:
            out["demo_answer"] = check_item.accepted[0]
        return out

    # ---------- 3. Raju's turn ----------
    def turn(self, lid: str) -> dict:
        l = self.store.load(lid)
        raju = self._raju(l)
        now = self.now(l)
        before_states = dict(raju.rules)
        raju.apply_forgetting({rid: self._mem(l, rid).p_recall(now) for rid in raju.rules}, self.forget_threshold)
        for rid, st in raju.rules.items():
            if st == "forgotten" and before_states[rid] == "taught":
                self._log(l, "forgot", rule=rid, recall=round(self._mem(l, rid).p_recall(now), 2))
        weights = {rid: 1 + self._mem(l, rid).wrong for rid in raju.eligible_to_plant()}   # steer towards the learner's weak rules
        choice = choose_turn(raju, self.rng, self.p_no_error, weights)
        if choice is None:
            self._save_raju(l, raju); self.store.save(l)
            return {"kind": "need_intro", "message": "Learn a new rule first."}
        turn_type, rid = choice
        rule = self.by_id[rid]
        item = self.rng.choice(rule.items)
        if self.agent and self.llm is not None:
            t = raju_agent_turn(self.llm, rule, item, self.rules, self.items, l.seen_words, raju.rules, lid,
                                no_error=(turn_type == "no_error"))
        else:
            t = raju_turn(self.llm, rule, item, self.rules, l.seen_words, raju.rules, lid, no_error=(turn_type == "no_error"))
        calls = t.model_calls if t.model_calls is not None else (
            (len(t.rejected) + (1 if t.source == "llm" else 0)) if self.llm is not None else 0)
        l.model_calls += calls; l.turns += 1
        l.pending = {"kind": "raju", "rule_id": rid, "item_id": item.item_id, "turn_type": turn_type,
                     "sentence": t.draft, "attempt": 0, "source": t.source}
        self._log(l, "raju_turn", rule=rid, turn_type=turn_type, source=t.source, shown=t.draft,
                  rejected=[{"draft": r.get("draft"), "reasons": r.get("reasons")} for r in t.rejected],
                  state=dict(raju.rules).get(rid), calls=calls,
                  tools=[{"sentence": c["args"].get("sentence"), "result": c["result"]} for c in t.tool_log])
        self._save_raju(l, raju); self.store.save(l)
        out = {"kind": "raju", "sentence": t.draft, "ask": self.rng.choice(RAJU_ASK), "meaning": item.english,
               "source": t.source, "rejected_drafts": len(t.rejected), "turn_type": turn_type}
        if self.demo:
            out["demo_answer"] = NO_ERROR if turn_type == "no_error" else item.accepted[0]
        return out

    # ---------- 2 + 4. learner answers ----------
    def answer(self, lid: str, text: str) -> dict:
        l = self.store.load(lid)
        p = l.pending
        if not p:
            return {"error": "Nothing to answer. Ask for a turn or a new rule."}
        rule, item = self.items[p["item_id"]]
        now = self.now(l)
        if p["kind"] in ("tutor", "test"):
            return self._study_answer(l, p, rule, item, text, now)
        if p["kind"] == "why":                                  # an explanation, not an answer: teacher reads it, nothing changes
            self.store.queue_for_teacher({"learner": lid, "item": item.item_id, "kind": "explanation", "text": text})
            l.pending = None; self.store.save(l)
            return {"verdict": "explanation", "message": RAJU_THANKS, "raju_state": l.raju.get(rule.rule_id)}
        p["attempt"] += 1

        if p["kind"] == "intro_check":
            res = check(rule, item, text)
            m = self._mem(l, rule.rule_id)
            m.update(res.verdict, now)
            if res.verdict == "correct":
                if l.conditions.get(rule.rule_id, "A") == "A":     # only teach-Raju rules go to Raju
                    m.ready_for_raju = True
                    l.raju.setdefault(rule.rule_id, "unknown")
                l.pending = None
                out = {"verdict": "correct", "message": "Right! Now Raju will try this rule, and you'll check him."}
            elif res.verdict == "unsure":
                self.store.queue_for_teacher({"learner": lid, "item": item.item_id, "answer": text, "kind": "intro_check"})
                l.pending = None if p["attempt"] >= 2 else p
                out = {"verdict": "unsure", "message": "I can't judge that one; a teacher will check it. Try the form from the example."}
            else:
                out = {"verdict": "wrong", "message": hint(rule, item, p["attempt"])}
                if p["attempt"] >= 2:
                    l.pending = None
            self.store.save(l)
            return out

        # Raju turn
        raju = self._raju(l)
        if p["turn_type"] == "no_error":
            res = check_no_error_turn(rule, item, text)
        else:
            res = check(rule, item, text)
        ev = apply_check(raju, lid, rule, item, res, p["turn_type"])
        self._log(l, "checked", rule=rule.rule_id, verdict=res.verdict, turn_type=p["turn_type"],
                  raju_changed=ev.classmate_state_changed, counts=ev.counts_toward_mastery)
        l.events.append(ev)
        if ev.counts_toward_mastery:
            self._mem(l, rule.rule_id).update(res.verdict, now, recognition=p["turn_type"] == "no_error")
        self._save_raju(l, raju)

        if res.verdict == "unsure":
            self.store.queue_for_teacher({"learner": lid, "item": item.item_id, "answer": text,
                                          "turn_type": p["turn_type"], "raju_sentence": p["sentence"]})
            l.pending = None
            msg = "I'm not sure about that answer, so it doesn't count either way. A teacher will look at it."
        elif res.verdict == "correct":
            l.pending = None
            msg = ("Yes, there was no mistake." if p["turn_type"] == "no_error" else RAJU_THANKS)
            if p["turn_type"] == "planted":
                l.fixes += 1
                if l.fixes % WHY_EVERY == 0:
                    why = self.rng.choice(RAJU_WHY)
                    l.pending = {"kind": "why", "rule_id": rule.rule_id, "item_id": item.item_id, "attempt": 0}
                    self.store.save(l)
                    return {"verdict": res.verdict, "message": msg, "raju_state": l.raju.get(rule.rule_id),
                            "turn_type": p["turn_type"], "why_question": why}
        else:
            if p["turn_type"] == "no_error":
                msg = "Raju's sentence was already correct."
                l.pending = None
            else:
                msg = hint(rule, item, p["attempt"])
                if p["attempt"] >= 2:                          # same feedback as the normal tutor: show the correct form
                    msg += f" Correct form: {item.accepted[0]}"
                    l.pending = None
        self.store.save(l)
        return {"verdict": res.verdict, "message": msg, "raju_state": l.raju.get(rule.rule_id),
                "turn_type": p["turn_type"]}

    # ---------- study conditions (Section 8.3): B matched error examples, C normal tutor, and tests ----------
    def assign_conditions(self, lid: str, rule_ids: list[str] | None = None) -> dict[str, str]:
        """Within-learner Latin square: rules are split into A/B/C, rotated by learner so every rule meets every condition."""
        l = self.store.load(lid)
        ids = rule_ids or [r.rule_id for r in self.rules]
        shift = sum(map(ord, lid)) % 3
        l.conditions = {rid: "ABC"[(k + shift) % 3] for k, rid in enumerate(ids)}
        self.store.save(l); return l.conditions

    def example(self, lid: str) -> dict | None:
        """Condition B: study one matched error example (wrong sentence, correction, L1 explanation). No teaching."""
        l = self.store.load(lid)
        rules = [r for r in self.rules if l.conditions.get(r.rule_id) == "B" and self._mem(l, r.rule_id).introduced]
        if not rules:
            return None
        rule = min(rules, key=lambda r: l.exposures.get(r.rule_id, 0))
        item = self.rng.choice(rule.items)
        l.exposures[rule.rule_id] = l.exposures.get(rule.rule_id, 0) + 1
        self._log(l, "example", rule=rule.rule_id); self.store.save(l)
        return {"rule_id": rule.rule_id, "wrong": item.planted_error, "right": item.accepted[0], "why": rule.l1_habit,
                "meaning": item.english}

    def prompt(self, lid: str) -> dict | None:
        """Condition C: normal tutor. The learner writes the sentence; the same checker and hints correct the learner."""
        l = self.store.load(lid)
        rules = [r for r in self.rules if l.conditions.get(r.rule_id) == "C" and self._mem(l, r.rule_id).introduced]
        if not rules:
            return None
        rule = min(rules, key=lambda r: l.exposures.get(r.rule_id, 0))
        item = self.rng.choice(rule.items)
        l.exposures[rule.rule_id] = l.exposures.get(rule.rule_id, 0) + 1
        l.pending = {"kind": "tutor", "rule_id": rule.rule_id, "item_id": item.item_id, "attempt": 0}
        self.store.save(l)
        out = {"rule_id": rule.rule_id, "task": f"Say in Telugu: {item.english}", "hindi": item.hindi}
        if self.demo:
            out["demo_answer"] = item.accepted[0]
        return out

    def test_item(self, lid: str, phase: str, rule_id: str, item_id: str | None = None) -> dict:
        """Cue-free production test: English (and Hindi) meaning -> Telugu sentence. No feedback, no mastery change."""
        l = self.store.load(lid)
        rule = self.by_id[rule_id]
        item = self.items[item_id][1] if item_id else rule.items[0]
        l.pending = {"kind": "test", "phase": phase, "rule_id": rule_id, "item_id": item.item_id, "attempt": 0}
        self.store.save(l)
        return {"phase": phase, "task": f"Say in Telugu: {item.english}", "hindi": item.hindi}

    def _study_answer(self, l, p, rule, item, text, now) -> dict:
        if p["kind"] == "test":
            res = check(rule, item, text)
            l.tests.append({"phase": p["phase"], "rule": rule.rule_id, "item": item.item_id, "condition": l.conditions.get(rule.rule_id),
                            "verdict": res.verdict, "answer": text, "day": round(l.clock_offset_days, 2)})
            if res.verdict == "unsure":
                self.store.queue_for_teacher({"learner": l.learner_id, "item": item.item_id, "answer": text, "kind": "test", "phase": p["phase"]})
            l.pending = None; self.store.save(l)
            return {"verdict": "recorded", "message": "Saved. (No feedback during tests.)"}
        res = check(rule, item, text)                       # condition C
        p["attempt"] += 1
        m = self._mem(l, rule.rule_id); m.update(res.verdict, now)
        self._log(l, "checked", rule=rule.rule_id, verdict=res.verdict, turn_type="tutor", raju_changed=False, counts=res.verdict != "unsure")
        if res.verdict == "correct":
            l.pending = None; msg = "Correct!"
        elif res.verdict == "wrong":
            msg = hint(rule, item, p["attempt"])                 # matched with condition A: hint first, then the correct form
            if p["attempt"] >= 2:
                msg += f" Correct form: {item.accepted[0]}"
                l.pending = None
        else:
            l.pending = None; msg = "I'm not sure; a teacher will check it."
            self.store.queue_for_teacher({"learner": l.learner_id, "item": item.item_id, "answer": text, "kind": "tutor"})
        self.store.save(l)
        return {"verdict": res.verdict, "message": msg}

    def results(self, lid: str) -> dict:
        """Test scores by phase and condition (share correct; unsure counted separately)."""
        l = self.store.load(lid); out: dict = {}
        for t in l.tests:
            d = out.setdefault(t["phase"], {}).setdefault(t["condition"] or "-", {"correct": 0, "n": 0, "unsure": 0})
            d["n"] += 1; d["correct"] += t["verdict"] == "correct"; d["unsure"] += t["verdict"] == "unsure"
        return out

    def skip_days(self, lid: str, days: float) -> None:
        l = self.store.load(lid); l.clock_offset_days += days
        self._log(l, "skip", days=days); self.store.save(l)

    def inside(self, lid: str) -> dict:
        """Everything the 'inside' panel shows: classmate state, learner recall, seen words, recent internal steps, teacher queue."""
        l = self.store.load(lid); now = self.now(l)
        rules = {rid: {"name": self.by_id[rid].name, "ready": m.ready_for_raju, "raju": l.raju.get(rid, "-"),
                       "recall": round(m.p_recall(now), 2), "correct": m.correct, "wrong": m.wrong}
                 for rid, m in l.rules.items() if m.introduced}
        return {"status": self.status(lid), "rules": rules, "seen_words": sorted(l.seen_words),
                "trace": l.trace, "teacher_queue": self.store.teacher_queue(lid), "pending": bool(l.pending)}

    def status(self, lid: str) -> dict:
        l = self.store.load(lid); now = self.now(l)
        return {"rules": {rid: {"ready": m.ready_for_raju, "recall": round(m.p_recall(now), 2),
                                "raju": l.raju.get(rid, "-"), "correct": m.correct, "wrong": m.wrong}
                          for rid, m in l.rules.items() if m.introduced},
                "seen_words": len(l.seen_words), "day": round(l.clock_offset_days, 1),
                "turns": l.turns, "model_calls": l.model_calls,
                "calls_per_turn": round(l.model_calls / l.turns, 2) if l.turns else 0}


__all__ = ["Tutor", "NO_ERROR"]
