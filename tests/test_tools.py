from setu.bank import load_rules, index_items, vocab_for
from setu.tools import check_classmate_sentence as tool, ERR_SENT_LATIN, ERR_SENT_NOT_TELUGU, ERR_SENT_MULTI

R = load_rules(); I = index_items(R)
CTX = dict(items=I, rules=R, seen_words=vocab_for(R, ["HI-TE-002"]), rule_state={r.rule_id: "unknown" for r in R})


def call(item_id, sentence):
    return tool({"item_id": item_id, "sentence": sentence}, **CTX)


def test_valid_planted_sentence_passes():
    assert call("HI-TE-002-a", "ఇది పుస్తకం ఉంది") == {"ok": True, "reasons": []}


def test_answer_leak_reported():
    assert "ANSWER_LEAK" in call("HI-TE-002-a", "ఇది పుస్తకం")["reasons"]


def test_likely_wrong_values():
    assert call("HI-TE-002", "ఇది పుస్తకం ఉంది") == 'ERROR invalid_argument item_id: "HI-TE-002" is a rule id; pass an item id like "HI-TE-002-a".'
    assert call("This is a book.", "ఇది పుస్తకం ఉంది").startswith('ERROR invalid_argument item_id: "This is a book." does not match')
    assert call("HI-TE-099-a", "ఇది పుస్తకం ఉంది") == 'ERROR invalid_argument item_id: "HI-TE-099-a" is not in the rule bank.'
    assert call("HI-TE-002-a", "idi pustakam undi") == ERR_SENT_LATIN
    assert call("HI-TE-002-a", "ఇది పుస్తకం ఉంది (This is a book)") == ERR_SENT_LATIN
    assert call("HI-TE-002-a", "यह किताब है") == ERR_SENT_NOT_TELUGU
    assert call("HI-TE-002-a", "ఇది పుస్తకం ఉంది. ఇది సరైనదా?") == ERR_SENT_MULTI
