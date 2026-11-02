"""AI student simulator: a language model plays the learner's TYPING, the harness decides the OUTCOME.

Same principle as Raju ("AI writes, rules decide"), applied to the student. An LLM that is simply told "you are a
Hindi speaker who does not know this rule" knows too much Telugu: it often writes the right sentence anyway
(measured with `scripts/simulate_students.py --free`). So the parametric learner (setu/simlearner.py) decides
whether this attempt is right, wrong in the planted way, or "I don't know"; the model only writes what that
learner would type. The style is also drawn by the harness, not the model, so every style can be scored separately:

  correct : exact | one small spelling slip | typed in Hindi (Devanagari) letters | one extra word
  wrong   : the planted mistake in the same words | the same mistake in slightly different words

The real checker then marks the answer. Disagreements between the intended outcome and the verdict are the
useful output: they measure how the checker copes with realistic learner variation that we did not write ourselves.
"""
from __future__ import annotations
import json, random, re
from .llm import LLM

STYLES = {
    "correct": [("exact", 0.40, "exactly as written"),
                ("slip", 0.20, "with one small spelling slip, such as a missing or wrong vowel sign, as a tired learner might type"),
                ("devanagari", 0.25, "typed in Hindi (Devanagari) letters instead of Telugu letters, because the learner has no Telugu keyboard"),
                ("extra_word", 0.15, "with one short extra word added at the end")],
    "wrong": [("same_words", 0.60, "in exactly the same words"),
              ("reworded", 0.40, "in slightly different words, keeping the same mistake and the same meaning")],
}
SYSTEM = ("You play Ankit, an adult Hindi speaker who is learning Telugu and is typing on a phone. "
          "Output only the sentence Ankit types, on one line, with no explanation and no quotes.")


def pick_style(rng: random.Random, intended: str):
    opts = STYLES[intended]
    return rng.choices(opts, weights=[o[1] for o in opts])[0]


def build_messages(item, rule, intended: str, canned: str, style_text: str) -> list[dict]:
    if intended == "correct":
        user = (f"Meaning: {item.english}\nThe correct Telugu sentence is: {canned}\n"
                f"Type this sentence the way Ankit would: {style_text}. Keep the meaning.")
    else:
        user = (f"Meaning: {item.english}\nHindi speakers learning Telugu often make this mistake: {rule.l1_habit}\n"
                f"A sentence with that mistake: {canned}\n"
                f"Type Ankit's version of this sentence with the same mistake, {style_text}.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


class LLMStudent:
    def __init__(self, llm: LLM, rng: random.Random):
        self.llm, self.rng = llm, rng
        self.calls = self.failures = 0

    def write(self, item, rule, intended: str, canned: str) -> tuple[str, str]:
        name, _, text = pick_style(self.rng, intended)
        self.calls += 1
        try:
            out = self.llm.chat(build_messages(item, rule, intended, canned, text), temperature=0.8, max_tokens=60)
            line = next((l.strip().strip('"“”\'`') for l in out.strip().splitlines() if l.strip()), "")
            if not line:
                raise ValueError("empty reply")
            return line, name
        except Exception:
            self.failures += 1
            return canned, name + "(fallback)"       # model failed: use the canned answer and say so


class StudentMock:
    """Offline stand-in that follows the style instructions (NOT a result)."""
    model = "student-mock"

    def __init__(self):
        self.calls = 0

    def chat(self, messages, temperature=0.8, max_tokens=60, schema=None) -> str:
        self.calls += 1
        u = messages[-1]["content"]
        if "Meaning:" in u and "Translate into Telugu" in u:          # the uncontrolled 'free' probe
            return "నేను ఇంటికి వెళ్తాను"
        sent = (re.search(r"correct Telugu sentence is: (.+)\n", u) or re.search(r"A sentence with that mistake: (.+)\n", u)).group(1).strip()
        if "spelling slip" in u:
            return sent[:-1]
        if "Devanagari" in u:
            from .script import telugu_to_deva
            return telugu_to_deva(sent)
        if "extra word" in u:
            return sent + " కదా"
        return sent
