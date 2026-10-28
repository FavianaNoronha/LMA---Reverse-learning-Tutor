import json, re
from pathlib import Path
from .schemas import Rule, Item
from .text import normalize, tokens

DATA = Path(__file__).resolve().parent.parent / "data"


def load_rules(pair: str = "l1-hi_l2-te") -> list[Rule]:
    raw = json.loads((DATA / pair / "rules.json").read_text(encoding="utf-8"))
    return [Rule(**r) for r in raw]


def index_items(rules: list[Rule]) -> dict[str, tuple[Rule, Item]]:
    return {i.item_id: (r, i) for r in rules for i in r.items}


def matches(patterns: list[str], text: str) -> bool:
    n = normalize(text)
    return any(re.search(p, n) for p in patterns)


def vocab_for(rules: list[Rule], rule_ids: list[str]) -> set[str]:
    """Words a learner has seen if they have studied these rules (v0 stand-in for the real seen-word list)."""
    out: set[str] = set()
    for r in rules:
        if r.rule_id in rule_ids:
            for i in r.items:
                for s in i.accepted + [i.planted_error]:
                    out.update(tokens(s))
    return out
