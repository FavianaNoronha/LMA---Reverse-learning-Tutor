from .schemas import Rule
from .leakfilter import errors_in


def copy_rate(productions: list[str], planted_rule_ids: set[str], rules: list[Rule]) -> float:
    """Share of the learner's own later sentences that contain an error the classmate planted for them."""
    if not productions:
        return 0.0
    hits = sum(1 for p in productions if set(errors_in(p, rules)) & planted_rule_ids)
    return hits / len(productions)


# ---- evaluation metrics for the weak classmate (borrowed ideas, see docs/prior_art.md) ----
def selective_flip_score(flip_targeted: float, flip_misaligned: float, flip_generic: float) -> float:
    """SFS = F_T - 0.5 (F_M + F_G)  (Do, Sonkar & Sachan 2026, arXiv 2605.12748).
    F_* = share of trials where the simulated student flips to the right answer after targeted / misaligned /
    generic feedback. 1.0 = flips only when taught the right thing; ~0 = flips whatever you say (sycophantic)."""
    return flip_targeted - 0.5 * (flip_misaligned + flip_generic)


def rmse(target: dict[str, float], observed: dict[str, float]) -> float:
    """RMSE between the target skill vector (1 = classmate may know it, 0 = must not) and the classmate's
    observed per-rule accuracy (Apartsin et al. 2026, arXiv 2605.25601)."""
    keys = list(target)
    if not keys:
        return 0.0
    return (sum((target[k] - observed.get(k, 0.0)) ** 2 for k in keys) / len(keys)) ** 0.5


def controllability(target: dict[str, float], observed: dict[str, float]) -> float:
    """Mean of accuracy on rules he may know and (1 - accuracy) on rules he must not know. 1.0 = perfect control."""
    keys = list(target)
    if not keys:
        return 1.0
    return sum(observed.get(k, 0.0) if target[k] == 1 else 1.0 - observed.get(k, 0.0) for k in keys) / len(keys)
