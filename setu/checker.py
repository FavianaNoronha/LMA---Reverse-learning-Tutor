"""Checker v0: deterministic, conservative. Only this module may decide correct/wrong.
It never guesses: anything it cannot match is 'unsure' (goes to the teacher queue)."""
from .schemas import Item, Rule, CheckResult
from .text import normalize
from .bank import matches


def check(rule: Rule, item: Item, answer: str) -> CheckResult:
    n = normalize(answer)
    if not n:
        return CheckResult(item_id=item.item_id, answer=answer, verdict="unsure", reason="empty answer")
    if n in {normalize(a) for a in item.accepted}:
        return CheckResult(item_id=item.item_id, answer=answer, verdict="correct", reason="exact accepted form")
    if n == normalize(item.planted_error):
        return CheckResult(item_id=item.item_id, answer=answer, verdict="wrong", reason="classmate error left unchanged")
    if matches(item.wrong_regex, n):
        return CheckResult(item_id=item.item_id, answer=answer, verdict="wrong", reason="matches known error pattern")
    return CheckResult(item_id=item.item_id, answer=answer, verdict="unsure", reason="not in accepted set and no known error pattern")
