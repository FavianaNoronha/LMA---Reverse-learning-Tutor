from .schemas import Rule
from .leakfilter import errors_in


def copy_rate(productions: list[str], planted_rule_ids: set[str], rules: list[Rule]) -> float:
    """Share of the learner's own later sentences that contain an error the classmate planted for them."""
    if not productions:
        return 0.0
    hits = sum(1 for p in productions if set(errors_in(p, rules)) & planted_rule_ids)
    return hits / len(productions)
