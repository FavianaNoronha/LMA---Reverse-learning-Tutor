"""Per-learner classmate knowledge. The classmate is weaker than the learner by construction:
a rule moves unknown -> taught only after the learner corrects it correctly; taught -> forgotten when
the learner's own tracker predicts the learner is about to forget it (so the classmate 'forgets' too)."""
from __future__ import annotations
from .schemas import ClassmateRuleState


class RajuState:
    def __init__(self, rule_ids: list[str], teach_needed: int = 1, progress: dict[str, int] | None = None):
        self.rules: dict[str, ClassmateRuleState] = {r: "unknown" for r in rule_ids}
        self.teach_needed = teach_needed                 # checked correct fixes needed before Raju knows a rule
        self.progress: dict[str, int] = dict(progress or {})

    def learner_corrected(self, rule_id: str, correct: bool) -> None:
        if correct and self.rules[rule_id] in ("unknown", "forgotten"):
            self.progress[rule_id] = self.progress.get(rule_id, 0) + 1
            if self.progress[rule_id] >= self.teach_needed:
                self.rules[rule_id] = "taught"; self.progress[rule_id] = 0

    def apply_forgetting(self, p_recall: dict[str, float], threshold: float = 0.5) -> None:
        for rid, p in p_recall.items():
            if self.rules.get(rid) == "taught" and p < threshold:
                self.rules[rid] = "forgotten"

    def eligible_to_plant(self) -> list[str]:
        return [r for r, s in self.rules.items() if s in ("unknown", "forgotten")]
