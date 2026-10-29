"""Coach v0: fixed hints from the rule bank (no model). Attempt 1: what is different in Telugu.
Attempt 2: the correct form. An LLM coach in the learner's L1 comes later, behind the same checks."""
from .schemas import Rule, Item


def hint(rule: Rule, item: Item, attempt: int) -> str:
    if attempt <= 1:
        return f"Hint: {rule.name}. {rule.l1_habit}."
    return f"Answer: {item.accepted[0]}"
