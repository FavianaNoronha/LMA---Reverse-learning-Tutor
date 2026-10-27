"""Leak filter v0. A classmate draft is shown to the learner only if it passes all checks.
Reasons: OOV (word the learner has not seen), NOT_ONE_ERROR, UNKNOWN_RULE_CORRECT,
ANSWER_LEAK, EXPLANATION."""
from dataclasses import dataclass, field
from .schemas import Rule, Item, ClassmateTurn
from .text import tokens
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
                seen_words: set[str], rule_state: dict[str, str]) -> LeakDecision:
    reasons: list[str] = []
    allowed = set(seen_words) | set(item.allowed_new)
    for s in item.accepted + [item.planted_error]:
        allowed.update(tokens(s))  # target words of this item are allowed
    allowed_for_oov = set(seen_words) | set(item.allowed_new) | set(tokens(item.planted_error))
    for s in item.accepted:
        allowed_for_oov.update(tokens(s))
    if any(t not in allowed_for_oov for t in tokens(draft)):
        reasons.append("OOV")
    errs = errors_in(draft, rules)
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
    return LeakDecision(ok=not reasons, reasons=reasons)


def select_classmate_sentence(drafts: list[str], rule: Rule, item: Item, rules: list[Rule],
                              seen_words: set[str], rule_state: dict[str, str],
                              learner_id: str = "anon", max_tries: int = 3) -> ClassmateTurn:
    rejected = []
    for d in drafts[:max_tries]:
        dec = check_draft(d, rule, item, rules, seen_words, rule_state)
        if dec.ok:
            return ClassmateTurn(learner_id=learner_id, item_id=item.item_id, draft=d, source="llm", rejected=rejected)
        rejected.append({"draft": d, "reasons": dec.reasons})
    return ClassmateTurn(learner_id=learner_id, item_id=item.item_id, draft=item.planted_error, source="bank", rejected=rejected)
