"""Raju as a small tool-using agent (revise-or-submit loop).

The model is asked to write one sentence for a bank item. It must call the tool `check_classmate_sentence`
on every draft; it reads the tool's result (ok, or the leak reasons, or an exact error string) and either revises
or stops. Bounded: at most `max_calls` model calls, then the bank sentence is used.

Safety rules that do not depend on the model behaving:
  * the harness, not the model, decides what is shown: a sentence is shown only if check_draft passes on it;
  * once the tool says ok, the harness submits that same sentence (no extra model call);
  * the tool is read-only; the model has no tool that writes memory or marks answers;
  * learner text never enters this prompt.
Works with any chat model: tool calls use a JSON reply {"tool": "check_classmate_sentence", "args": {...}}
(the fallback when a model has no native function calling; native calling can be added behind the same loop).
"""
from __future__ import annotations
import json
from .leakfilter import check_draft
from .llm import LLM, parse_json
from .schemas import ClassmateTurn, Item, Rule
from .tools import CHECK_CLASSMATE_SENTENCE, check_classmate_sentence

PROMPT_VERSION = "classmate-agent-v0.1"
SYSTEM = (
    "You write ONE short Telugu sentence for a language-learning game, using only allowed words. "
    "You have one tool, check_classmate_sentence, and you must call it on every draft before it is used. "
    "Reply with JSON only: {\"tool\": \"check_classmate_sentence\", \"args\": {\"item_id\": \"...\", \"sentence\": \"...\"}}. "
    "If the tool says ok, you are done. If it lists reasons, revise the sentence and call the tool again. "
    "Never explain, translate or add words. Tool schema: " + json.dumps(CHECK_CLASSMATE_SENTENCE, ensure_ascii=False))


def build_messages(item: Item, seen_words: set[str], no_error: bool) -> list[dict]:
    ref = item.accepted[0] if no_error else item.planted_error
    kind = "correct; keep it correct" if no_error else "contains one mistake; keep exactly that mistake"
    user = (f"Item id: {item.item_id}\nAllowed words: {' '.join(sorted(seen_words))}\nMeaning: {item.english}\n"
            f"Reference sentence ({kind}): {ref}\n"
            "Write a natural version using only allowed words (it may be identical to the reference), and check it with the tool.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def raju_agent_turn(llm: LLM, rule: Rule, item: Item, rules: list[Rule], items: dict, seen_words: set[str],
                    rule_state: dict[str, str], learner_id: str, no_error: bool = False, max_calls: int = 3) -> ClassmateTurn:
    msgs = build_messages(item, seen_words, no_error)
    rejected: list[dict] = []; tool_log: list[dict] = []; calls = 0
    meta = dict(learner_id=learner_id, item_id=item.item_id, turn_type="no_error" if no_error else "planted",
                rule_version=rule.version, model=getattr(llm, "model", None), prompt_version=PROMPT_VERSION)
    for _ in range(max_calls):
        calls += 1
        try:
            reply = llm.chat(msgs, schema=None)
            call = parse_json(reply)
        except Exception:
            call = None; reply = ""
        if not isinstance(call, dict) or call.get("tool") != "check_classmate_sentence" or not isinstance(call.get("args"), dict):
            rejected.append({"draft": "", "reasons": ["NO_TOOL_CALL"]})        # model ignored the protocol (or tried something else)
            msgs += [{"role": "assistant", "content": str(reply)[:300]},
                     {"role": "user", "content": "ERROR: reply with the JSON tool call only."}]
            continue
        args = call["args"]
        result = check_classmate_sentence(args, items=items, rules=rules, seen_words=seen_words, rule_state=rule_state, no_error=no_error)
        tool_log.append({"args": args, "result": result})
        sentence = str(args.get("sentence", "")).strip()
        if isinstance(result, dict) and result["ok"] and args.get("item_id") == item.item_id:
            dec = check_draft(sentence, rule, item, rules, seen_words, rule_state, no_error=no_error)   # re-validate: never trust the call
            if dec.ok:
                return ClassmateTurn(draft=sentence, source="llm", rejected=rejected, model_calls=calls, tool_log=tool_log, **meta)
        if isinstance(result, dict):
            rejected.append({"draft": sentence, "reasons": result["reasons"] or ["WRONG_ITEM"]})
        else:
            rejected.append({"draft": sentence, "reasons": ["TOOL_ERROR"]})
        msgs += [{"role": "assistant", "content": json.dumps(call, ensure_ascii=False)},
                 {"role": "user", "content": "TOOL RESULT: " + (json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else result)}]
    fallback = item.accepted[0] if no_error else item.planted_error
    return ClassmateTurn(draft=fallback, source="bank", rejected=rejected, model_calls=calls, tool_log=tool_log, **meta)
