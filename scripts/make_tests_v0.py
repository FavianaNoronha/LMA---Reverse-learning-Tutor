"""Generate data/l1-hi_l2-te/tests_v0.jsonl (50 cases). Re-run after editing rules. Hand-edit leak cases here."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setu.bank import load_rules

rules = load_rules(); cases = []
def add(group, **kw): cases.append({"case_id": f"{group[:3].upper()}-{sum(c['group']==group for c in cases)+1:02d}", "group": group, **kw})

firsts = [r.items[0] for r in rules]
seconds = [r.items[1] for r in rules if len(r.items) > 1]
for i in firsts:                                   # 15 correct
    add("checker", item_id=i.item_id, answer=i.accepted[0], expect="correct")
for i in seconds[::3][:5] if False else [seconds[k] for k in (0, 4, 8, 12, 13)][:4]:   # 4 wrong (error left unchanged)
    add("checker", item_id=i.item_id, answer=i.planted_error, expect="wrong")
add("checker", item_id=firsts[0].item_id, answer="క్యా నువ్వు వస్తున్నావు", expect="wrong")
add("checker", item_id="HI-TE-005-b", answer="వాడు రాడు", expect="correct")  # variant from Krishnamurti & Gwynn
add("checker", item_id="HI-TE-008-b", answer="వాడు వస్తుంది", expect="wrong")  # wrong via pattern, not exact bank sentence
for i in (firsts[1], firsts[4], firsts[8], firsts[12]):  # 4 unsure
    add("checker", item_id=i.item_id, answer="నాకు తెలియదు", expect="unsure")

L = [  # item, seen rules, draft, rule_state overrides, expect_ok, expect reasons (subset)
 ("HI-TE-002-a", ["HI-TE-002"], "ఇది పుస్తకం ఉంది", {}, True, []),
 ("HI-TE-002-a", ["HI-TE-002"], "ఇది పుస్తకం", {}, False, ["ANSWER_LEAK", "NOT_ONE_ERROR"]),
 ("HI-TE-002-a", ["HI-TE-002"], "ఇది కలం ఉంది", {}, False, ["OOV"]),
 ("HI-TE-002-a", ["HI-TE-002"], "ఇది పుస్తకం ఉంది ఎందుకంటే నియమం", {}, False, ["OOV", "EXPLANATION"]),
 ("HI-TE-003-a", ["HI-TE-003"], "నేను ఒక పుస్తకం ఉంది", {}, True, []),
 ("HI-TE-003-a", ["HI-TE-003"], "నాకు ఒక పుస్తకం ఉంది", {}, False, ["ANSWER_LEAK"]),
 ("HI-TE-002-a", ["HI-TE-002", "HI-TE-003"], "నాకు ఒక పుస్తకం ఉంది", {}, False, ["UNKNOWN_RULE_CORRECT", "NOT_ONE_ERROR"]),
 ("HI-TE-005-a", ["HI-TE-005"], "నేను వస్తాను కాదు", {}, True, []),
 ("HI-TE-005-a", ["HI-TE-005"], "నేను రాను", {}, False, ["ANSWER_LEAK"]),
 ("HI-TE-008-a", ["HI-TE-008"], "ఆమె వస్తాడు", {}, True, []),
 ("HI-TE-008-a", ["HI-TE-008"], "ఆమె వస్తుంది", {}, False, ["ANSWER_LEAK"]),
]
for it, seen, d, st, ok, rs in L:
    add("leak", item_id=it, seen_rules=seen, draft=d, rule_state=st, expect_ok=ok, expect_reasons=rs)

S = [  # selection: drafts -> expected source / index
 ("HI-TE-002-a", ["ఇది పుస్తకం", "ఇది కలం ఉంది", "ఇది పుస్తకం ఉంది"], "llm", 2),
 ("HI-TE-002-a", ["ఇది పుస్తకం", "ఇది కలం ఉంది", "ఇది పుస్తకం, నియమం"], "bank", None),
 ("HI-TE-002-a", ["ఇది పుస్తకం ఉంది"], "llm", 0),
 ("HI-TE-002-a", [], "bank", None),
 ("HI-TE-002-a", ["ఇది పుస్తకం", "ఇది కలం ఉంది", "అది పెన్ను", "ఇది పుస్తకం ఉంది"], "bank", None),
]
for it, drafts, src, idx in S:
    add("leak", item_id=it, seen_rules=["HI-TE-002"], drafts=drafts, expect_source=src, expect_index=idx)

for it in ("HI-TE-002-a", "HI-TE-005-b", "HI-TE-008-a", "HI-TE-011-b", "HI-TE-015-a"):   # planting: exactly one error, of the right rule
    rid = it.rsplit("-", 1)[0]
    add("planting", item_id=it, expect_rules=[rid])

add("forgetting", steps=[["correct", "HI-TE-002", True]], expect={"HI-TE-002": "taught"})
add("forgetting", steps=[["correct", "HI-TE-002", True], ["forget", {"HI-TE-002": 0.3}]], expect={"HI-TE-002": "forgotten"})
add("forgetting", steps=[["correct", "HI-TE-002", True], ["forget", {"HI-TE-002": 0.8}]], expect={"HI-TE-002": "taught"})
add("forgetting", steps=[["correct", "HI-TE-002", True], ["forget", {"HI-TE-002": 0.3}], ["correct", "HI-TE-002", True]], expect={"HI-TE-002": "taught"})
add("forgetting", steps=[["correct", "HI-TE-002", False]], expect={"HI-TE-002": "unknown"})

# no-error turns (classmate sentence is correct)
add("no_error", item_id="HI-TE-002-a", seen_rules=["HI-TE-002"], draft="ఇది పుస్తకం", rule_state={"HI-TE-002": "taught"}, expect_ok=True, expect_reasons=[])
add("no_error", item_id="HI-TE-002-a", seen_rules=["HI-TE-002"], draft="ఇది పుస్తకం ఉంది", rule_state={"HI-TE-002": "taught"}, expect_ok=False, expect_reasons=["NOT_CORRECT"])
add("no_error", item_id="HI-TE-002-a", seen_rules=["HI-TE-002"], draft="ఇది పుస్తకం", rule_state={}, expect_ok=False, expect_reasons=["UNKNOWN_RULE_CORRECT"])
add("no_error", item_id="HI-TE-002-a", answer="<NO_ERROR>", expect="correct")
add("no_error", item_id="HI-TE-002-a", answer="ఇది పుస్తకం ఉంది", expect="wrong")

# ledger: only checked correct fixes change the classmate; unsure never counts
add("ledger", item_id="HI-TE-002-a", verdict="correct", turn_type="planted", expect_counts=True, expect_changed=True)
add("ledger", item_id="HI-TE-002-a", verdict="wrong", turn_type="planted", expect_counts=True, expect_changed=False)
add("ledger", item_id="HI-TE-002-a", verdict="unsure", turn_type="planted", expect_counts=False, expect_changed=False)
add("ledger", item_id="HI-TE-002-a", verdict="correct", turn_type="no_error", expect_counts=True, expect_changed=False)

# copy rate
add("copy", productions=["ఇది పుస్తకం ఉంది", "నేను రాను"], planted=["HI-TE-002"], expect=0.5)
add("copy", productions=[], planted=["HI-TE-002"], expect=0.0)

out = Path(__file__).resolve().parent.parent / "data/l1-hi_l2-te/tests_v0.jsonl"
out.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cases) + "\n", encoding="utf-8")
from collections import Counter
print(len(cases), dict(Counter(c["group"] for c in cases)))
