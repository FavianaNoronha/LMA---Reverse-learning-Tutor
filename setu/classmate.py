"""Raju. The model only rewrites a bank sentence; the leak filter decides what is shown."""
from __future__ import annotations
from .schemas import Rule, Item, ClassmateTurn
from .leakfilter import select_classmate_sentence
from .llm import LLM, parse_sentence

PROMPT_VERSION = "classmate-v0.1"
SCHEMA = {"type": "object", "properties": {"sentence": {"type": "string"}}, "required": ["sentence"]}
SYSTEM = ("You write ONE short Telugu sentence for a language-learning game. Use only words from the allowed "
          "list. Do not explain anything, do not translate, do not add words. Reply as JSON: {\"sentence\": \"...\"}")

# What Raju says around the sentence. Fixed text, in the learner's L1 (Hindi for l1-hi_l2-te), never generated.
RAJU_ASK = ["मैंने ये लिखा, क्या ये सही है?", "ये ठीक है न?", "मुझे लगता है ये सही है… आप बताइए?"]
RAJU_THANKS = "अच्छा! समझ गया, धन्यवाद।"


def build_messages(item: Item, seen_words: set[str], no_error: bool) -> list[dict]:
    allowed = sorted(seen_words)
    ref = item.accepted[0] if no_error else item.planted_error
    kind = "correct; keep it correct" if no_error else "contains one mistake; keep exactly that mistake"
    user = (f"Allowed words: {' '.join(allowed)}\n"
            f"Meaning: {item.english}\n"
            f"Reference sentence ({kind}): {ref}\n"
            "Write a natural version using only allowed words. It may be identical to the reference.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def raju_turn(llm: LLM | None, rule: Rule, item: Item, rules: list[Rule], seen_words: set[str],
              rule_state: dict[str, str], learner_id: str, no_error: bool = False, n_drafts: int = 3) -> ClassmateTurn:
    drafts: list[str] = []
    if llm is not None:
        msgs = build_messages(item, seen_words, no_error)
        for _ in range(n_drafts):
            try:
                drafts.append(parse_sentence(llm.chat(msgs, schema=SCHEMA)))
            except Exception:
                drafts.append("")
    return select_classmate_sentence(drafts, rule, item, rules, seen_words, rule_state, learner_id=learner_id,
                                     max_tries=n_drafts, no_error=no_error,
                                     model=getattr(llm, "model", None), prompt_version=PROMPT_VERSION)
