"""Applies a checker result. This is the only place mastery and classmate state change.
- unsure  -> logged, counts for nothing, changes nothing (teacher settles it later)
- correct on a planted turn -> classmate is taught the rule
- anything else -> classmate unchanged (the model is never told 'you were wrong' and left to update itself)"""
from .schemas import Rule, Item, CheckResult, MasteryEvent
from .state import RajuState


def apply_check(raju: RajuState, learner_id: str, rule: Rule, item: Item,
                result: CheckResult, turn_type: str = "planted") -> MasteryEvent:
    before = raju.rules[rule.rule_id]
    if result.verdict == "correct" and turn_type == "planted":
        raju.learner_corrected(rule.rule_id, True)
    return MasteryEvent(learner_id=learner_id, rule_id=rule.rule_id, item_id=item.item_id,
                        rule_version=rule.version, turn_type=turn_type, verdict=result.verdict,
                        counts_toward_mastery=result.verdict != "unsure",
                        classmate_state_changed=raju.rules[rule.rule_id] != before)
