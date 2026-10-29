"""Leak filter v0. A classmate draft is shown to the learner only if it passes all checks.
Reasons: OOV (word the learner has not seen), NOT_ONE_ERROR, UNKNOWN_RULE_CORRECT,
ANSWER_LEAK, EXPLANATION, and for no-error turns NOT_CORRECT."""
from __future__ import annotations
from dataclasses import dataclass, field
from .schemas import Rule, Item, ClassmateTurn
from .text import tokens, normalize
from .bank import matches

EXPLAIN_MARKERS = ["ఎందుకంటే", "నియమం", "వ్యాకరణం", "क्योंकि", "नियम", "because", "rule", "grammar", "should be"]


@dataclass
class LeakDecision:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def errors_in(draft: str, rules: list[Rule]) -> list[str]:
    """Rule ids whose error pattern the draft matches."""
    return [r.rule_id for r in rules if any(matches(i.wrong_regex, draft) for i in r.items)]


def check_draft(draft: str, rule: Rule, item: Item, rules: list[Rule],
                seen_words: set[str], rule_state: dict[str, str], no_error: bool = False) -> LeakDecision:
    """no_error=False: draft must contain exactly one error, of `rule`.
    no_error=True : draft must be a correct sentence for `item`, and the classmate may only
                    produce it if it has already been taught `rule` (it cannot use rules it doesn't know)."""
    reasons: list[str] = []
    allowed = set(seen_words) | set(item.allowed_new) | set(tokens(item.planted_error))
    for s in item.accepted:
        allowed.update(tokens(s))
    if any(t not in allowed for t in tokens(draft)):
        reasons.append("OOV")
    errs = errors_in(draft, rules)
    if no_error:
        is_correct = normalize(draft) in {normalize(a) for a in item.accepted} or matches(item.fix_regex, draft)
        if errs or not is_correct:
            reasons.append("NOT_CORRECT")
        if rule_state.get(rule.rule_id, "unknown") != "taught":
            reasons.append("UNKNOWN_RULE_CORRECT")
    else:
        if errs != [rule.rule_id] or not matches(item.wrong_regex, draft):
            reasons.append("NOT_ONE_ERROR")
        if matches(item.fix_regex, draft):
            reasons.append("ANSWER_LEAK")
    for r in rules:
        if r.rule_id == rule.rule_id:
            continue
        if rule_state.get(r.rule_id, "unknown") != "taught":
            if any(matches(i.fix_regex, draft) for i in r.items):
                reasons.append("UNKNOWN_RULE_CORRECT")
                break
    low = draft.lower()
    if any(m.lower() in low for m in EXPLAIN_MARKERS):
        reasons.append("EXPLANATION")
    return LeakDecision(ok=not reasons, reasons=sorted(set(reasons)))


def select_classmate_sentence(drafts, rule: Rule, item: Item, rules: list[Rule],
                              seen_words: set[str], rule_state: dict[str, str],
                              learner_id: str = "anon", max_tries: int = 3, no_error: bool = False,
                              model: str | None = None, prompt_version: str | None = None) -> ClassmateTurn:
    rejected = []
    meta = dict(learner_id=learner_id, item_id=item.item_id, turn_type="no_error" if no_error else "planted",
                rule_version=rule.version, model=model, prompt_version=prompt_version)
    from itertools import islice
    for d in islice(drafts, max_tries):   # lazy: stops calling the model at the first draft that passes
        dec = check_draft(d, rule, item, rules, seen_words, rule_state, no_error=no_error)
        if dec.ok:
            return ClassmateTurn(draft=d, source="llm", rejected=rejected, **meta)
        rejected.append({"draft": d, "reasons": dec.reasons})
    fallback = item.accepted[0] if no_error else item.planted_error
    return ClassmateTurn(draft=fallback, source="bank", rejected=rejected, **meta)
