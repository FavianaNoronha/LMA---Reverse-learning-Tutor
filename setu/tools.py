"""Tools exposed to a model (function calling). v0 has one: the leak filter as a self-check for Raju.
Validation errors are returned as exact, fixed strings so the model can correct itself."""
from __future__ import annotations
import re
from .leakfilter import check_draft

CHECK_CLASSMATE_SENTENCE = {
    "name": "check_classmate_sentence",
    "description": (
        "Checks one Telugu sentence that the AI classmate (Raju) wants to show the learner, against the planted "
        "rule of one bank item and the learner's seen words; returns ok=true or the list of leak reasons. "
        "Use it on every draft sentence before it is shown to the learner. "
        "Do not use it to mark the learner's own answer (that is the checker's job) or to translate or explain."),
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {
                "type": "string",
                "description": "Bank item the sentence is for, e.g. HI-TE-002-a. Not the rule id (HI-TE-002) and not the English meaning.",
                "pattern": "^(HI-TE|TE-HI)-[0-9]{3}-[a-z]$"},
            "sentence": {
                "type": "string",
                "description": "Exactly one sentence in Telugu script (Unicode), as the learner would see it. No romanization, translation, quotes or explanation.",
                "minLength": 1, "maxLength": 120},
        },
        "required": ["item_id", "sentence"],
        "additionalProperties": False,
    },
}

_ITEM = re.compile(r"^(HI-TE|TE-HI)-[0-9]{3}-[a-z]$")
_RULE = re.compile(r"^(HI-TE|TE-HI)-[0-9]{3}$")
_TELUGU = re.compile(r"[ఀ-౿]")
_LATIN = re.compile(r"[A-Za-z]")

ERR_ITEM_IS_RULE = 'ERROR invalid_argument item_id: "{v}" is a rule id; pass an item id like "{v}-a".'
ERR_ITEM_FORMAT = 'ERROR invalid_argument item_id: "{v}" does not match HI-TE-NNN-x (example: HI-TE-002-a).'
ERR_ITEM_UNKNOWN = 'ERROR invalid_argument item_id: "{v}" is not in the rule bank.'
ERR_SENT_EMPTY = 'ERROR invalid_argument sentence: empty; pass one Telugu sentence.'
ERR_SENT_LATIN = 'ERROR invalid_argument sentence: contains Latin letters; pass Telugu script only, no romanization or English.'
ERR_SENT_NOT_TELUGU = 'ERROR invalid_argument sentence: no Telugu characters found; pass the sentence in Telugu script.'
ERR_SENT_MULTI = 'ERROR invalid_argument sentence: more than one sentence or line; pass exactly one sentence.'
ERR_SENT_LONG = 'ERROR invalid_argument sentence: longer than 120 characters; pass one short sentence.'


def check_classmate_sentence(args: dict, *, items: dict, rules: list, seen_words: set, rule_state: dict) -> dict | str:
    """Returns {"ok": bool, "reasons": [...]} or one of the ERR_* strings above (first invalid argument only)."""
    iid = str(args.get("item_id", "")).strip()
    sent = str(args.get("sentence", ""))
    if _RULE.match(iid):
        return ERR_ITEM_IS_RULE.format(v=iid)
    if not _ITEM.match(iid):
        return ERR_ITEM_FORMAT.format(v=iid)
    if iid not in items:
        return ERR_ITEM_UNKNOWN.format(v=iid)
    s = sent.strip()
    if not s:
        return ERR_SENT_EMPTY
    if "\n" in s or len(re.findall(r"[.!?।]\s*\S", s)) > 0:
        return ERR_SENT_MULTI
    if len(s) > 120:
        return ERR_SENT_LONG
    if _LATIN.search(s):
        return ERR_SENT_LATIN
    if not _TELUGU.search(s):
        return ERR_SENT_NOT_TELUGU
    rule, item = items[iid]
    dec = check_draft(s, rule, item, rules, seen_words, rule_state)
    return {"ok": dec.ok, "reasons": dec.reasons}
