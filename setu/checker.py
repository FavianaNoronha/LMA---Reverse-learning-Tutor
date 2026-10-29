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
    # v0.1 (found by the scorecard: 60% of learner-style variants came back unsure)
    if any(_edits(n, normalize(a)) == 1 for a in item.accepted):
        return CheckResult(item_id=item.item_id, answer=answer, verdict="wrong", reason="near miss: one letter away from the right form (spelling)")
    if n in OTHER_SENTENCES.get(item.item_id, set()):
        return CheckResult(item_id=item.item_id, answer=answer, verdict="wrong", reason="a correct sentence, but not this one (different meaning)")
    return CheckResult(item_id=item.item_id, answer=answer, verdict="unsure", reason="not in accepted set and no known error pattern")


def _edits(a: str, b: str) -> int:
    """Levenshtein distance on Unicode code points (Telugu vowel signs count as one letter each)."""
    if abs(len(a) - len(b)) > 1:
        return 2
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _other_sentences() -> dict[str, set[str]]:
    """For every item: the accepted forms of all OTHER items with a different meaning."""
    from .bank import load_rules
    try:
        rules = load_rules()
    except Exception:
        return {}
    items = [i for r in rules for i in r.items]
    return {i.item_id: {normalize(a) for j in items if j.english != i.english for a in j.accepted} for i in items}


OTHER_SENTENCES = _other_sentences()


NO_ERROR = "<NO_ERROR>"   # sent by the UI button "There is no mistake"


def check_no_error_turn(rule: Rule, item: Item, answer: str) -> CheckResult:
    """The classmate's sentence was correct. Saying so (or leaving it unchanged) is correct;
    'fixing' it into a known error is wrong (a false alarm); any other edit is unsure."""
    n = normalize(answer)
    if answer.strip() == NO_ERROR or n in {normalize(a) for a in item.accepted}:
        return CheckResult(item_id=item.item_id, answer=answer, verdict="correct", reason="recognised a correct sentence")
    if matches(item.wrong_regex, n):
        return CheckResult(item_id=item.item_id, answer=answer, verdict="wrong", reason="false alarm: changed a correct sentence into a known error")
    return CheckResult(item_id=item.item_id, answer=answer, verdict="unsure", reason="changed a correct sentence; may be a valid paraphrase")
