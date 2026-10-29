"""Turn choice v0: about 1 turn in 5 is a no-error turn, drawn only from rules the classmate
has been taught (it cannot use a rule correctly before that).
Optional `weights` (rule_id -> weight) makes Raju plant mistakes the learner makes more often, borrowing the
error-profile idea of 'Imitating Mistakes in a Learning Companion AI Agent' (arXiv 2507.12801). Raju's
knowledge state is unaffected; weights only steer which unknown rule he is wrong about."""
import random
from .state import RajuState


def choose_turn(raju: RajuState, rng: random.Random, p_no_error: float = 0.2,
                weights: dict[str, float] | None = None) -> tuple[str, str] | None:
    taught = [r for r, s in raju.rules.items() if s == "taught"]
    plantable = raju.eligible_to_plant()
    if taught and (not plantable or rng.random() < p_no_error):
        return "no_error", rng.choice(taught)
    if plantable:
        if weights:
            return "planted", rng.choices(plantable, weights=[max(weights.get(r, 1.0), 0.0) + 1e-9 for r in plantable])[0]
        return "planted", rng.choice(plantable)
    return None
