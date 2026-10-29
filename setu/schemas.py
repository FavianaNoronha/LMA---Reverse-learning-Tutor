"""The four contracts every other module talks through.

Rule/Item     - what the error bank stores
ClassmateTurn - what the classmate (Raju) is asked to produce / what comes back
CheckResult   - what the deterministic checker returns
LearnerRecord - what is stored per learner (state of each rule for the classmate)
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

Verdict = Literal["correct", "wrong", "unsure"]  # "partial" is planned for v1
RuleStatus = Literal["draft_unverified", "native_checked", "teacher_verified"]
Evidence = Literal["model_predicted", "predicted", "proxy", "observed", "replicated"]
Transfer = Literal["negative", "positive_control", "unclear"]
ClassmateRuleState = Literal["unknown", "taught", "forgotten"]


class Item(BaseModel):
    item_id: str
    english: str
    hindi: str = ""                 # Hindi gloss (L1 for Hindi speakers learning Telugu)
    telugu: str = ""                # Telugu gloss (L1 for Telugu speakers learning Hindi)
    accepted: list[str]            # full correct sentences (Telugu)
    planted_error: str             # bank sentence with exactly one error of the rule
    wrong_regex: list[str]         # patterns that identify this rule's error
    fix_regex: list[str]           # patterns that identify the correct form
    allowed_new: list[str] = Field(default_factory=list)  # extra words the classmate may use


class Rule(BaseModel):
    rule_id: str
    name: str
    category: str
    l1_habit: str
    transfer: Transfer
    status: RuleStatus = "draft_unverified"
    evidence: Evidence = "model_predicted"
    version: int = 1                   # bump on any change; never overwrite a published rule
    reviewer: str | None = None
    reviewed_at: str | None = None     # ISO date
    source: str = "unknown"            # grammar section, pilot sentence id, ...
    items: list[Item]


class ClassmateTurn(BaseModel):
    learner_id: str
    item_id: str
    draft: str
    source: Literal["llm", "bank"]
    turn_type: Literal["planted", "no_error"] = "planted"
    rule_version: int = 1
    model: str | None = None           # e.g. google/gemma-3-12b-it
    prompt_version: str | None = None
    rejected: list[dict] = Field(default_factory=list)  # [{"draft":..., "reasons":[...]}]
    model_calls: int | None = None     # set by the agent loop (else the caller counts)
    tool_log: list[dict] = Field(default_factory=list)  # [{"args":..., "result":...}] tool calls the model made


class CheckResult(BaseModel):
    item_id: str
    answer: str
    verdict: Verdict
    reason: str


class LearnerRecord(BaseModel):
    learner_id: str
    seen_words: set[str] = Field(default_factory=set)
    rule_state: dict[str, ClassmateRuleState] = Field(default_factory=dict)


class MasteryEvent(BaseModel):
    """One logged, checked attempt. Unsure verdicts are logged but never count."""
    learner_id: str
    rule_id: str
    item_id: str
    rule_version: int
    turn_type: Literal["planted", "no_error"]
    verdict: Verdict
    counts_toward_mastery: bool
    classmate_state_changed: bool
