"""Per-learner classmate knowledge. The classmate is weaker than the learner by construction:
a rule moves unknown -> taught only after the learner corrects it correctly; taught -> forgotten when
the learner's own tracker predicts the learner is about to forget it (so the classmate 'forgets' too)."""
from .schemas import ClassmateRuleState


class RajuState:
    def __init__(self, rule_ids: list[str]):
        self.rules: dict[str, ClassmateRuleState] = {r: "unknown" for r in rule_ids}

    def learner_corrected(self, rule_id: str, correct: bool) -> None:
        if correct and self.rules[rule_id] in ("unknown", "forgotten"):
            self.rules[rule_id] = "taught"

    def apply_forgetting(self, p_recall: dict[str, float], threshold: float = 0.5) -> None:
        for rid, p in p_recall.items():
            if self.rules.get(rid) == "taught" and p < threshold:
                self.rules[rid] = "forgotten"

    def eligible_to_plant(self) -> list[str]:
        return [r for r, s in self.rules.items() if s in ("unknown", "forgotten")]
