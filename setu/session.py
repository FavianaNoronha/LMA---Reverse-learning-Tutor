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
from .classmate import raju_turn, RAJU_ASK, RAJU_THANKS
from .coach import hint
from .ledger import apply_check
from .llm import LLM
from .memory import Learner, RuleMemory, Store
from .planner import choose_turn
from .schemas import Rule
from .state import RajuState
from .text import tokens

FORGET_THRESHOLD = 0.5


class Tutor:
    def __init__(self, store: Store, llm: LLM | None = None, pair: str = "l1-hi_l2-te",
                 seed: int | None = None, p_no_error: float = 0.2):
        self.rules: list[Rule] = load_rules(pair)
        self.by_id = {r.rule_id: r for r in self.rules}
        self.items = index_items(self.rules)
        self.store, self.llm, self.pair, self.p_no_error = store, llm, pair, p_no_error
        self.rng = random.Random(seed)

    # ---------- helpers ----------
    def now(self, l: Learner) -> float:
        return time.time() + l.clock_offset_days * 86400

    def _mem(self, l: Learner, rid: str) -> RuleMemory:
        return l.rules.setdefault(rid, RuleMemory())

    def _raju(self, l: Learner) -> RajuState:
        ready = [rid for rid, m in l.rules.items() if m.ready_for_raju]
        s = RajuState(ready)
        for rid in ready:
            s.rules[rid] = l.raju.get(rid, "unknown")
        return s

    def _save_raju(self, l: Learner, s: RajuState) -> None:
        l.raju.update(s.rules)

    # ---------- 1. learn a new rule ----------
    def intro(self, lid: str) -> dict | None:
        l = self.store.load(lid)
        nxt = next((r for r in self.rules if not self._mem(l, r.rule_id).introduced), None)
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
        return {"rule_id": nxt.rule_id, "title": nxt.name, "why": nxt.l1_habit,
                "example_wrong": ex.planted_error, "example_right": ex.accepted[0],
                "task": f"Say in Telugu: {check_item.english}", "hindi": check_item.hindi}

    # ---------- 3. Raju's turn ----------
    def turn(self, lid: str) -> dict:
        l = self.store.load(lid)
        raju = self._raju(l)
        now = self.now(l)
        raju.apply_forgetting({rid: self._mem(l, rid).p_recall(now) for rid in raju.rules}, FORGET_THRESHOLD)
        choice = choose_turn(raju, self.rng, self.p_no_error)
        if choice is None:
            self._save_raju(l, raju); self.store.save(l)
            return {"kind": "need_intro", "message": "Learn a new rule first."}
        turn_type, rid = choice
        rule = self.by_id[rid]
        item = self.rng.choice(rule.items)
        t = raju_turn(self.llm, rule, item, self.rules, l.seen_words, raju.rules, lid, no_error=(turn_type == "no_error"))
        calls = (len(t.rejected) + (1 if t.source == "llm" else 0)) if self.llm is not None else 0
        l.model_calls += calls; l.turns += 1
        l.pending = {"kind": "raju", "rule_id": rid, "item_id": item.item_id, "turn_type": turn_type,
                     "sentence": t.draft, "attempt": 0, "source": t.source}
        self._save_raju(l, raju); self.store.save(l)
        return {"kind": "raju", "sentence": t.draft, "ask": self.rng.choice(RAJU_ASK), "meaning": item.english,
                "source": t.source, "rejected_drafts": len(t.rejected)}

    # ---------- 2 + 4. learner answers ----------
    def answer(self, lid: str, text: str) -> dict:
        l = self.store.load(lid)
        p = l.pending
        if not p:
            return {"error": "Nothing to answer. Ask for a turn or a new rule."}
        rule, item = self.items[p["item_id"]]
        now = self.now(l)
        p["attempt"] += 1

        if p["kind"] == "intro_check":
            res = check(rule, item, text)
            m = self._mem(l, rule.rule_id)
            m.update(res.verdict, now)
            if res.verdict == "correct":
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
        l.events.append(ev)
        if ev.counts_toward_mastery:
            self._mem(l, rule.rule_id).update(res.verdict, now)
        self._save_raju(l, raju)

        if res.verdict == "unsure":
            self.store.queue_for_teacher({"learner": lid, "item": item.item_id, "answer": text,
                                          "turn_type": p["turn_type"], "raju_sentence": p["sentence"]})
            l.pending = None
            msg = "I'm not sure about that answer, so it doesn't count either way. A teacher will look at it."
        elif res.verdict == "correct":
            l.pending = None
            msg = ("Yes, there was no mistake." if p["turn_type"] == "no_error" else RAJU_THANKS)
        else:
            if p["turn_type"] == "no_error":
                msg = "Raju's sentence was already correct."
                l.pending = None
            else:
                msg = hint(rule, item, p["attempt"])
                if p["attempt"] >= 2:
                    l.pending = None
        self.store.save(l)
        return {"verdict": res.verdict, "message": msg, "raju_state": l.raju.get(rule.rule_id),
                "turn_type": p["turn_type"]}

    def skip_days(self, lid: str, days: float) -> None:
        l = self.store.load(lid); l.clock_offset_days += days; self.store.save(l)

    def status(self, lid: str) -> dict:
        l = self.store.load(lid); now = self.now(l)
        return {"rules": {rid: {"ready": m.ready_for_raju, "recall": round(m.p_recall(now), 2),
                                "raju": l.raju.get(rid, "-"), "correct": m.correct, "wrong": m.wrong}
                          for rid, m in l.rules.items() if m.introduced},
                "seen_words": len(l.seen_words), "day": round(l.clock_offset_days, 1),
                "turns": l.turns, "model_calls": l.model_calls,
                "calls_per_turn": round(l.model_calls / l.turns, 2) if l.turns else 0}


__all__ = ["Tutor", "NO_ERROR"]
