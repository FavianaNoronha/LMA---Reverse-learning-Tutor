"""Telugu speakers learning Hindi (Group 2): the draft bank must be consistent, like the Hindi->Telugu bank."""
import re
from setu.bank import load_rules
from setu.checker import check
from setu.leakfilter import errors_in

RULES = load_rules("l1-te_l2-hi")


def test_ten_draft_rules_all_unverified():
    assert len(RULES) == 10 and all(r.status == "draft_unverified" and r.reviewer is None for r in RULES)


def test_each_planted_error_is_exactly_one_error_of_its_rule():
    for r in RULES:
        for i in r.items:
            assert errors_in(i.planted_error, RULES) == [r.rule_id], i.item_id
            for a in i.accepted:
                assert errors_in(a, RULES) == [], (i.item_id, a)
                assert any(re.search(p, a) for p in i.fix_regex), (i.item_id, a)


def test_checker_works_unchanged_for_hindi_answers():
    r = RULES[0]; i = r.items[0]
    assert check(r, i, i.accepted[0]).verdict == "correct"
    assert check(r, i, i.planted_error).verdict == "wrong"
